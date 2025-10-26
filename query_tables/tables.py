
from typing import List, Optional, Union, Type, Tuple
from query_tables.exceptions import (
    NotTable, ExceptionQueryTable
)
from query_tables.cache import CacheQuery, BaseCache, AsyncBaseCache, AsyncCacheQuery
from query_tables.db import BaseDBQuery, BaseAsyncDBQuery
from query_tables.query_table import QueryTable, AsyncQueryTable
from query_tables.query import Query


class BaseTables(object):
    """
        Реализует доступ к таблицам.
    """    
    def __init__(
        self, db: Union[BaseDBQuery, BaseAsyncDBQuery],
        cls_query_table: Type[Union[QueryTable, AsyncQueryTable]],
        prefix_table: str = '', 
        tables: Optional[List[str]] = None,
        table_schema: str = 'public'
    ):
        """
        Args:
            db (Union[BaseDBQuery, BaseAsyncDBQuery]): Объект для доступа к БД.
            cls_query_table (Type[Union[QueryTable, AsyncQueryTable]]): Класс запросов.
            prefix_table (str, optional): Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
                Загружает таблцы по первой части названия, к примеру: common%. Если пустая строка, загрузить все таблицы из схемы.
            tables (Optional[List[str]], optional): Список подключаемых таблиц. По умолчанию - нет.
            table_schema (str, optional): Схема данных. По умолчанию - 'public'.
        """
        self._db = db
        self._cls_query_table = cls_query_table
        self._cache: BaseCache = None
        self._prefix_table: str = prefix_table
        self._tables: Optional[List[str]] = tables
        self._table_schema: str = table_schema
        self._tables_struct: dict[str, list] = {}
        self._db.set_placeholder_pattern(
                Query.PLACEHOLDER_PATTERN, 
                Query.PLACEHOLDER
            )
    
    def __getitem__(self, table_name: str) -> Union[QueryTable, AsyncQueryTable]:
        """Получение экземпляра для запроса.

        Args:
            table_name (str): Название таблицы.

        Raises:
            NotTable: Такой таблице нет.

        Returns:
            QueryTable: Экземпляр запроса.
        """        
        try:
            fields: list = self._tables_struct[table_name]
        except Exception as e:
            raise NotTable(table_name)
        try:
            return self._cls_query_table(
                self._db, table_name, 
                fields, self._cache
            )
        except Exception as e:
            raise ExceptionQueryTable(table_name, e)


class Tables(BaseTables):
    
    def __init__(
        self, db: BaseDBQuery,
        prefix_table: str = '', 
        tables: Optional[List[str]] = None,
        table_schema:str = 'public',
        cache_ttl: int = 0,
        non_expired: bool = False,
        cache_maxsize: int = 1024,
        cache: Optional[BaseCache] = None
    ):
        """
        Args:
            db (BaseDBQuery): Объект для доступа к БД.
            prefix_table (str, optional): Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
                Загружает таблцы по первой части названия, к примеру: common%. Если пустая строка, загрузить все таблицы из схемы.
            tables (Optional[List[str]], optional): Список подключаемых таблиц. По умолчанию - нет.
            table_schema (str, optional): Схема данных. По умолчанию - 'public'.
            cache_ttl (int, optional): Время кеширования данных. По умолчанию 0 секунд - кеширование отключено.
            non_expired (bool, optional): Вечный кеш без времени истечения. По умолчанию - выключен.
                Если включить, будет использоваться вне зависимости от cache_ttl.
                При non_expired=False и cache_ttl=0 - кеш отключен.
            cache_maxsize (int, optional): Размер элементов в кеше.
            cache (BaseCache, optional): Пользовательская реализация кеша.
        """
        super().__init__(db, QueryTable, prefix_table, tables, table_schema)
        self._cache = cache or CacheQuery(cache_ttl, cache_maxsize, non_expired)
        self._tables_struct = self._db.get_tables_struct(
                table_schema=table_schema,
                prefix_table=prefix_table,
                tables=tables
            )
    
    def query(
            self, sql: str,
            params: dict = None,
            cache: bool = False,
            delete_cache: bool = False
        ) -> Optional[List[Tuple]]:
        """Выполнение произвольного SQL запроса.
        Могут выполняться запросы на изменения и получения данных.

        Args:
            sql (str): SQL запрос.
            params (dict): Парамтеры запроса.
            cache (bool): Подгружать и сохранять данные в кеше.
            delete_cache (bool): Удалить данные из кеша, если они там есть.

        Returns:
            Optional[List[Tuple]]: Результат.
        """
        if delete_cache:
            data = self._cache.delete_data_query(sql)
        if cache:
            data = self._cache.get_data_query(sql)
            if data:
                return data
        with self._db as db_query:
            db_query.execute(sql, params)
            data = db_query.fetchall()
        if cache:
            self._cache.save_data_query(sql, data)
        return data
    
    def clear_cache(self):
        """
            Вызов очищение всего кеша.
        """        
        self._cache.clear()


class TablesAsync(BaseTables):
    """
        Реализует доступ к таблицам через асинхронный код.
    """    
    
    def __init__(
        self, db: BaseAsyncDBQuery,
        prefix_table: str = '', 
        tables: Optional[List[str]] = None,
        table_schema:str = 'public',
        cache_ttl: int = 0,
        non_expired: bool = False,
        cache: Optional[AsyncBaseCache] = None
    ):
        """
        Args:
            db (BaseAsyncDBQuery): Объект для доступа к БД.
            prefix_table (str, optional): Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
                Загружает таблцы по первой части названия, к примеру: common%. Если пустая строка, загрузить все таблицы из схемы.
            tables (Optional[List[str]], optional): Список подключаемых таблиц. По умолчанию - нет.
            table_schema (str, optional): Схема данных. По умолчанию - 'public'.
            cache_ttl (int, optional): Время кеширования данных. По умолчанию 0 секунд - кеширование отключено.
            non_expired (bool, optional): Вечный кеш без времени истечения. По умолчанию - выключен.
                При non_expired=False и cache_ttl=0 - кеш отключен.
            cache (AsyncBaseCache, optional): Пользовательская реализация кеша.
        """
        super().__init__(db, AsyncQueryTable, prefix_table, tables, table_schema)
        self._cache = cache or AsyncCacheQuery(cache_ttl, non_expired)
    
    async def init(self):
        self._tables_struct = await self._db.get_tables_struct(
                table_schema=self._table_schema,
                prefix_table=self._prefix_table,
                tables=self._tables
            )
    
    async def query(
            self, sql: str,
            params: dict = None,
            cache: bool = False,
            delete_cache: bool = False
        ) -> Optional[List[Tuple]]:
        """Выполнение произвольного SQL запроса.
        Могут выполняться запросы на изменения и получения данных.

        Args:
            sql (str): SQL запрос.
            params (dict): Парамтеры запроса.
            cache (bool): Получать и устанавливать данные в кеш.
            delete_cache (bool): Удалить данные из кеша, если они там есть.

        Returns:
            Optional[List[Tuple]]: Результат.
        """
        if delete_cache:
            data = await self._cache.delete_data_query(sql)
        if cache:
            data = await self._cache.get_data_query(sql)
            if data:
                return data
        async with self._db as db_query:
            await db_query.execute(sql, params)
            data = await db_query.fetchall()
        if cache:
            await self._cache.save_data_query(sql, data)
        return data
    
    async def clear_cache(self):
        """
            Вызов очищение всего кеша.
        """
        await self._cache.clear()