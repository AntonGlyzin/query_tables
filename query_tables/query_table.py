from typing import List, Dict, Union
from query_tables.cache import BaseCache, AsyncBaseCache
from query_tables.db import BaseDBQuery, BaseAsyncDBQuery
from query_tables.query import Query
from query_tables.exceptions import (
    ErrorDeleteCacheJoin,
    DesabledCache
)


class QueryTable(Query):
    """
        Объединяет работу с запросами и кешем.
    """    
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
            cache (Union[BaseCache, AsyncBaseCache]): Кеш.
        """
        super().__init__(table_name, fields)
        self._db: Union[BaseDBQuery, BaseAsyncDBQuery] = db
        self._cache: Union[BaseCache, AsyncBaseCache] = cache

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
        query = self._get()
        return self._cache[query]

    def delete_cache_query(self):
        """
            Удаление кеша привязанного к запросу. 
        """
        if not self._cache.is_enabled_cache():
            raise DesabledCache()
        query = self._get()
        del self._cache[query]

    def delete_cache_table(self):
        """
            Удаляет данные из кеша связанные с таблицей.
        """
        if not self._cache.is_enabled_cache():
            raise DesabledCache()
        if self.is_table_joined:
            raise ErrorDeleteCacheJoin(self._table_name)
        self._cache.delete_cache_table(self._table_name)

    def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._get()
        if self._cache.is_enabled_cache():
            cache_data = self._cache[query].get()
            if cache_data:
                return cache_data
        with self._db as db_query:
            db_query.execute(query)
            data = db_query.fetchall()
        res = [
            dict(zip(self.map_fields, row)) for row in data
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
        query = self._insert(records)
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
        query = self._update(**params)
        with self._db as db_query:
            db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._delete()
        with self._db as db_query:
            db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()


class AsyncQueryTable(QueryTable):
    """
        Объединяет работу с запросами в асинхронном режиме и локальным кешем.
    """    
    def __init__(
        self, db: object, 
        table_name: str,
        fields: List[str],
        cache: BaseCache
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (BaseCache): Кеш.
        """
        super().__init__(db, table_name, fields, cache)
    
    async def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._get()
        if self._cache.is_enabled_cache():
            cache_data = self._cache[query].get()
            if cache_data:
                return cache_data
        async with self._db as db_query:
            await db_query.execute(query)
            data = await db_query.fetchall()
        res = [
            dict(zip(self.map_fields, row)) for row in data
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
        query = self._insert(records)
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
        query = self._update(**params)
        async with self._db as db_query:
            await db_query.execute(query)
        if self._cache.is_enabled_cache():
            self.delete_cache_table()

    async def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._delete()
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
        cache: AsyncBaseCache
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            table_name (str): Название таблицы.
            fields List[str]: Список полей.
            cache (AsyncBaseCache): Кеш.
        """
        super().__init__(db, table_name, fields, cache)
        
    @property
    def cache(self) -> AsyncBaseCache:
        """Кеш данных связанный со своим SQL запросом.

        Returns:
            AsyncBaseCache: Кеш.
        """
        query = self._get()
        return self._cache[query]

    async def delete_cache_query(self):
        """
            Удаление кеша привязанного к запросу. 
        """
        enabled = await self._cache.is_enabled_cache()
        if not enabled:
            raise DesabledCache()
        query = self._get()
        await self._cache[query].delete_query()

    async def delete_cache_table(self):
        """
            Удаляет данные из кеша связанные с таблицей.
        """
        enabled = await self._cache.is_enabled_cache()
        if not enabled:
            raise DesabledCache()
        if self.is_table_joined:
            raise ErrorDeleteCacheJoin(self._table_name)
        await self._cache.delete_cache_table(self._table_name)
        
    async def get(self) -> List[Dict]:
        """
            Запрос на получение записей.
        """
        query = self._get()
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            cache_data = await self._cache[query].get()
            if cache_data:
                return cache_data
        async with self._db as db_query:
            await db_query.execute(query)
            data = await db_query.fetchall()
        res = [
            dict(zip(self.map_fields, row)) for row in data
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
        query = self._insert(records)
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
        query = self._update(**params)
        async with self._db as db_query:
            await db_query.execute(query)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()

    async def delete(self):
        """Удаляет записи из БД и удаляет 
            кеш (если включен) по данной таблице.
        """
        query = self._delete()
        async with self._db as db_query:
            await db_query.execute(query)
        enabled = await self._cache.is_enabled_cache()
        if enabled:
            await self.delete_cache_table()