from typing import List, Dict, Optional, Type, Union
from query_tables.cache import BaseCache, AsyncBaseCache
from query_tables.db import BaseDBQuery, BaseAsyncDBQuery
from query_tables.query import BaseQuery, BaseJoin
from query_tables.exceptions import (
    ErrorDeleteCacheJoin,
    DesabledCache
)


class QueryTable(BaseQuery):
    """
        Объединяет работу с запросами и кешем.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: Union[BaseCache, AsyncBaseCache], 
        cls_query: Type[BaseQuery]
    ):
        """
        Args:
            db (BaseDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (Union[BaseCache, AsyncBaseCache]): Кеш.
            query (Type[BaseQuery]): Класс конструктора запросов.
        """
        self._db: BaseDBQuery = db
        self._table_name: str = table_name
        self._fields: List[str] = fields
        self._cache: Union[BaseCache, AsyncBaseCache] = cache
        self._query: BaseQuery = cls_query(table_name, fields)

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
            raise ErrorDeleteCacheJoin(self._table_name)
        self._cache.delete_cache_table(self._table_name)
        
    def select(self, fields: Optional[List[str]] = None) -> 'QueryTable':
        self._query.select(fields)
        return self

    def join(self, table: Union[BaseJoin, BaseQuery]) -> 'QueryTable':
        self._query.join(table)
        return self

    def filter(self, **params) -> 'QueryTable':
        self._query.filter(**params)
        return self

    def order_by(self, **params) -> 'QueryTable':
        self._query.order_by(**params)
        return self

    def limit(self, value: int) -> 'QueryTable':
        self._query.limit(value)
        return self

    def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._query.get()
        if self._cache.is_enabled_cache():
            cache_data = self._cache[query].get()
            if cache_data:
                return cache_data
        with self._db as db_query:
            db_query.execute(query)
            data = db_query.fetchall()
        res = [
            dict(zip(self._query.map_fields, row)) for row in data
        ]
        if self._cache.is_enabled_cache() and res:
            self._cache[query] = res
        return res

    def insert(self, records: List[Dict]): 
        """Добавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            records (List[Dict]): Записи для вставки в БД.
        """        
        query = self._query.insert(records)
        with self._db as db_query:
            db_query.execute(query)
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
            db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._query.delete()
        with self._db as db_query:
            db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()


class AsyncQueryTable(QueryTable):
    """
        Объединяет работу с запросами и кешем в асинхронном режиме.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: BaseCache, 
        cls_query: BaseQuery
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (BaseCache): Кеш.
            query (BaseQuery): Класс конструктора запросов.
        """
        self._db: BaseAsyncDBQuery = None
        self._table_name: str = ''
        self._fields: List[str] = []
        self._cache: BaseCache = None
        self._query: BaseQuery = None
        super().__init__(
            db, table_name, fields,
            cache, cls_query
        )
        
    async def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._query.get()
        if self._cache.is_enabled_cache():
            cache_data = self._cache[query].get()
            if cache_data:
                return cache_data
        async with self._db as db_query:
            await db_query.execute(query)
            data = await db_query.fetchall()
        res = [
            dict(zip(self._query.map_fields, row)) for row in data
        ]
        if self._cache.is_enabled_cache() and res:
            self._cache[query] = res
        return res

    async def insert(self, records: List[Dict]): 
        """Добавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            records (List[Dict]): Записи для вставки в БД.
        """        
        query = self._query.insert(records)
        async with self._db as db_query:
            await db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    async def update(self, **params):
        """Обнавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            params: Параметры обновления.
        """
        query = self._query.update(**params)
        async with self._db as db_query:
            await db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    async def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._query.delete()
        async with self._db as db_query:
            await db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()
            
            
class AsyncRemoteQueryTable(QueryTable):
    """
        Объединяет работу с запросами и удаленным кешем в асинхронном режиме.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: AsyncBaseCache, 
        cls_query: BaseQuery
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (AsyncBaseCache): Кеш.
            query (BaseQuery): Класс конструктора запросов.
        """
        self._db: BaseAsyncDBQuery = None
        self._table_name: str = ''
        self._fields: List[str] = []
        self._cache: AsyncBaseCache = None
        self._query: BaseQuery = None
        super().__init__(
            db, table_name, fields,
            cache, cls_query
        )
        
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
        query = self._query.get()
        await self._cache[query].delete_query()

    async def delete_cache_table(self):
        """
            Удаляет данные из кеша связанные с таблицей.
        """
        enabled = await self._cache.is_enabled_cache()
        if not enabled:
            raise DesabledCache()
        if self._query.is_table_joined:
            raise ErrorDeleteCacheJoin(self._table_name)
        await self._cache.delete_cache_table(self._table_name)
        
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
            await db_query.execute(query)
            data = await db_query.fetchall()
        res = [
            dict(zip(self._query.map_fields, row)) for row in data
        ]
        if enabled and res:
            await self._cache[query].set_data(res)
        return res

    async def insert(self, records: List[Dict]): 
        """Добавляет записи в БД и удаляет 
            кеш (если включен) по данной таблице.

        Args:
            records (List[Dict]): Записи для вставки в БД.
        """        
        query = self._query.insert(records)
        async with self._db as db_query:
            await db_query.execute(query)
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
            await db_query.execute(query)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()

    async def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._query.delete()
        async with self._db as db_query:
            await db_query.execute(query)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()