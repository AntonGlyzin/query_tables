from typing import List, Dict, TypeVar, Union
from query_tables.cache import BaseCache, AsyncBaseCache
from query_tables.db import BaseDBQuery, BaseAsyncDBQuery
from query_tables.query.functions import Field, Functions
from query_tables.query.condition import Condition
from query_tables.query.base_query import BaseQueryTable, BaseJoin
from query_tables.query import Query
from query_tables.exceptions import (
    ErrorDeleteCacheJoin,
    DesabledCache
)

T = TypeVar('T', bound='BuilderQueryTable')


class BuilderQueryTable(object):
    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: Union[BaseCache, AsyncBaseCache]
    ):
        """
        Args:
            db (BaseDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (BaseCache): Кеш.
        """
        self._query = Query(table_name, fields)
        
    def __str__(self):
        table_alias = self._query._table_alias or self._query._table_name
        cls_name = __class__.__name__
        return f'<{cls_name}({table_alias})>'
    
    def __repr__(self):
        return str(self)
    
    def select(self: T, *args: Union[Field, Functions, List[str]]) -> T:
        """Устанавливает поля для выборки.

        Args:
            args : Поля из БД. `Field('company', 'name'), Max(Field('person', 'age')).as_('person_age')` или `['id', 'name']`

        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.select(*args)
        return self

    def join(self: T, table: Union[BaseJoin, BaseQueryTable]) -> T:
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (Union[BaseJoin, BaseQueryTable]): Таблица которая присоединяется.

        Returns:
            QueryTable: Экземпляр запроса.
        """
        if issubclass(type(table), BaseJoin):
            query: Query = table.join_table._query
        else:
            query: Query = table._query
        self._query.join(query)
        return self

    def filter(self: T, *args: Union[Condition, Functions, Field], **params) -> T:
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.filter(*args, **params)
        return self
    
    def group_by(self: T, *args: Union[Field, List[str]]) -> T:
        """Группировка записей по полю.

        Args:
            args: Поля для группировки. `Field('company', 'name')` или `['name']`

        Returns:
            QueryTable: Экземпляр запроса.
        """        
        self._query.group_by(*args)
        return self
    
    def having(self: T, *args: Union[Condition, Functions, Field], **params) -> T:
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.having(*args, **params)
        return self

    def order_by(self: T, *args: Union[Field], **kwargs) -> T:
        """Сортировка для sql запроса.
        
        Args:
            args: Параметры сортировки. `Field('company', 'name').desc()`
            params: Параметры сортировки. `age=Ordering.DESC`

        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.order_by(*args, **kwargs)
        return self

    def limit(self: T, value: int) -> T:
        """Ограничение записей в sql запросе.

        Args:
            value (int): Количество записей.
        
        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.limit(value)
        return self
    
    def offset(self: T, value: int) -> T:
        """Смещение.

        Args:
            value (int): Смещение по записям.
        
        Returns:
            QueryTable: Экземпляр запроса.
        """
        self._query.offset(value)
        return self


class QueryTable(BuilderQueryTable, BaseQueryTable):
    """
        Объединяет работу с запросами и кешем.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: BaseCache
    ):
        """
        Args:
            db (BaseDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (BaseCache): Кеш.
        """
        self._db: BaseDBQuery = db
        self._cache: BaseCache = cache
        self._query: Query = None
        super().__init__(db, table_name, fields, cache)

    @property
    def cache(self) -> BaseCache:
        """Кеш данных связанный со своим SQL запросом.

        Raises:
            DesabledCache: Кеш отключен.

        Returns:
            BaseCache: Кеш.
        """        
        if not self._cache.is_enabled_cache():
            raise DesabledCache()
        query = self._query.get()
        return self._cache[query]

    def delete_cache_query(self):
        """
            Удаление кеша привязанного к запросу. 
        """
        if not self._cache.is_enabled_cache():
            raise DesabledCache()
        query = self._query.get()
        del self._cache[query]

    def delete_cache_table(self):
        """
            Удаляет данные из кеша связанные с таблицей.
        """
        if not self._cache.is_enabled_cache():
            raise DesabledCache()
        if self._query.is_table_joined:
            raise ErrorDeleteCacheJoin(self._query._table_name)
        self._cache.delete_cache_table(self._query._table_name)

    def get(self) -> List[Dict]:
        """Запрос на получение записей.
            
        Returns:
            List[Dict]: Записи.
        """
        query = self._query.get()
        if self._cache.is_enabled_cache():
            cache_data = self._cache[query].get()
            if cache_data:
                return cache_data
        with self._db as db_query:
            db_query.execute(query, self._query.params)
            data = db_query.fetchall()
        res = [
            dict(zip(self._query.map_fields, row)) for row in data
        ]
        if self._cache.is_enabled_cache() and res:
            self._cache[query] = res
            self._cache[query].use_tables(self._query.tables_query)
        return res

    def insert(self, records: List[Dict]): 
        """Добавляет записи в БД и удаляет 
        кеш (если включен) по данной таблице.

        Args:
            records (List[Dict]): Записи для вставки в БД.
        """        
        query = self._query.insert(records)
        with self._db as db_query:
            db_query.execute(query, self._query.params)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    def update(self, **params):
        """Обнавляет записи в БД и удаляет 
        кеш (если включен) по данной таблице.

        Args:
            params: Параметры обновления.
        """
        query = self._query.update(**params)
        with self._db as db_query:
            db_query.execute(query, self._query.params)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    def delete(self):
        """Удаляет записи из БД и удаляет 
        кеш (если включен) по данной таблице.
        """
        query = self._query.delete()
        with self._db as db_query:
            db_query.execute(query, self._query.params)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()


class AsyncQueryTable(BuilderQueryTable, BaseQueryTable):
    """
        Объединяет работу с запросами и удаленным кешем в асинхронном режиме.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: AsyncBaseCache
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (AsyncBaseCache): Кеш.
        """
        self._db: BaseAsyncDBQuery = db
        self._cache: AsyncBaseCache = cache
        self._query: Query = None
        super().__init__(db, table_name, fields, cache)
        
    @property
    def cache(self) -> AsyncBaseCache:
        """Кеш данных связанный со своим SQL запросом.

        Returns:
            AsyncBaseCache: Кеш.
        """
        query = self._query.get()
        return self._cache[query]

    async def delete_cache_query(self):
        """
            Удаление кеша привязанного к запросу. 
        """
        enabled = await self._cache.is_enabled_cache()
        if not enabled:
            raise DesabledCache()
        await self.cache.delete_query()

    async def delete_cache_table(self):
        """
            Удаляет данные из кеша связанные с таблицей.
        """
        enabled = await self._cache.is_enabled_cache()
        if not enabled:
            raise DesabledCache()
        if self._query.is_table_joined:
            raise ErrorDeleteCacheJoin(self._query._table_name)
        await self._cache.delete_cache_table(self._query._table_name)
    
    async def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._query.get()
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            cache_data = await self._cache[query].get()
            if cache_data:
                return cache_data
        async with self._db as db_query:
            await db_query.execute(query, self._query.params)
            data = await db_query.fetchall()
        res = [
            dict(zip(self._query.map_fields, row)) for row in data
        ]
        if enabled and res:
            await self._cache[query].set_data(res, self._query.tables_query)
        return res

    async def insert(self, records: List[Dict]): 
        """Добавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            records (List[Dict]): Записи для вставки в БД.
        """        
        query = self._query.insert(records)
        async with self._db as db_query:
            await db_query.execute(query, self._query.params)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()

    async def update(self, **params):
        """Обнавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            params: Параметры обновления.
        """
        query = self._query.update(**params)
        async with self._db as db_query:
            await db_query.execute(query, self._query.params)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()

    async def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._query.delete()
        async with self._db as db_query:
            await db_query.execute(query, self._query.params)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()