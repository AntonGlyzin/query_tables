
from typing import List, Optional, Union, Type, Tuple
from query_tables.exceptions import (
    NotTable, ExceptionQueryTable, 
    ErrorLoadingStructTables
)
from query_tables.query import Query
from query_tables.cache import CacheQuery, BaseCache, TypeCache, AsyncBaseCache
from query_tables.db import BaseDBQuery, BaseAsyncDBQuery, DBTypes
from query_tables.query_table import QueryTable, AsyncQueryTable, AsyncRemoteQueryTable



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
        self._db: Union[BaseDBQuery, BaseAsyncDBQuery] = db
        self._cls_query_table: Type[Union[QueryTable, AsyncQueryTable]] = cls_query_table
        self._cache: BaseCache = None
        self._prefix_table: str = prefix_table
        self._tables: Optional[List[str]] = tables
        self._table_schema: str = table_schema
        self._tables_struct: dict[str, list] = {}
        
    @property
    def _pg_query_struct(self):
        query = """ 
            select it.table_name, ic.column_name
            from information_schema.tables it
            join information_schema.columns ic on it.table_name = ic.table_name 
                                                and it.table_schema = ic.table_schema
            where 1=1 
        """
        if self._table_schema:
            query += f" and it.table_schema = '{self._table_schema}'"
        if self._prefix_table:
            query += f" and it.table_name like '{self._prefix_table}%%'"
        elif self._tables:
            tables = ', '.join(f"'{i}'" for i in self._tables)
            query += f" and it.table_name in ({tables})"
        return query
        
    def __getitem__(self, table_name: str) -> QueryTable:
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
                self._db, table_name, fields, 
                self._cache, Query
            )
        except Exception as e:
            raise ExceptionQueryTable(table_name, e)
        
    def clear_cache(self):
        """
            Вызов очищение всего кеша.
        """        
        self._cache.clear()


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
            db (Union[BaseDBQuery, BaseAsyncDBQuery]): Объект для доступа к БД.
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
        super().__init__(
            db, QueryTable, 
            prefix_table, tables, table_schema
        )
        self._cache = cache or CacheQuery(cache_ttl, cache_maxsize, False, non_expired)
        if TypeCache.remote == self._cache.type_cache:
            _tables_struct = self._cache._get_struct_tables()
            if _tables_struct:
                self._tables_struct = _tables_struct
                return
        if DBTypes.postgres == db.get_type():
            self._fill_tables_pg_struct()
        elif DBTypes.sqlite == db.get_type():
            self._fill_tables_sqlite_struct()
        if TypeCache.remote == self._cache.type_cache:
            self._cache._save_struct_tables(self._tables_struct)
            
    def query(
        self, sql: str,
        cache: bool = False,
        is_new_data: bool = False
    ) -> Optional[List[Tuple]]:
        """Выполнение произвольного SQL запроса.
        Могут выполняться запросы на изменения и получения данных.

        Args:
            sql (str): SQL запрос.
            cache (bool): Работать ли с кешем.
            is_new_data (bool): Установить новые данные из запроса, если вы работает с кешем.

        Returns:
            Optional[List[Tuple]]: Результат.
        """
        if cache and not is_new_data:
            data = self._cache._get_data_query(sql)
            if data:
                return data
        with self._db as db_query:
            db_query.execute(sql)
            data = db_query.fetchall()
        if cache:
            self._cache._save_data_query(sql, data)
        return data

    def _fill_tables_pg_struct(self):
        """
            Получает таблицы и название колоннок из postgres.
        """
        with self._db as db_query:
            db_query.execute(self._pg_query_struct)
            data = db_query.fetchall()
        for row in data:
            if row[0] in self._tables_struct:
                self._tables_struct[row[0]].append(row[1])
            else:
                self._tables_struct[row[0]] = [row[1]]
                
    def _fill_tables_sqlite_struct(self):
        """
            Получает таблицы и название колоннок из sqlite.
        """
        try:
            db_query = self._db.connect()
            db_query.execute("select name from sqlite_master where type='table';")
            for row in db_query.fetchall():
                self._tables_struct[row[0]] = []
            for table in self._tables_struct.keys():
                db_query.execute(f"PRAGMA table_info({table});")
                for row in db_query.fetchall():
                    self._tables_struct[table].append(row[1])
        except Exception as e:
            raise ErrorLoadingStructTables(e)
        finally:
            self._db.close()


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
        cache_maxsize: int = 1024,
        cache: Optional[Union[BaseCache, AsyncBaseCache]] = None
    ):
        """
        Args:
            db (Union[BaseDBQuery, BaseAsyncDBQuery]): Объект для доступа к БД.
            prefix_table (str, optional): Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
                Загружает таблцы по первой части названия, к примеру: common%. Если пустая строка, загрузить все таблицы из схемы.
            tables (Optional[List[str]], optional): Список подключаемых таблиц. По умолчанию - нет.
            table_schema (str, optional): Схема данных. По умолчанию - 'public'.
            cache_ttl (int, optional): Время кеширования данных. По умолчанию 0 секунд - кеширование отключено.
            non_expired (bool, optional): Вечный кеш без времени истечения. По умолчанию - выключен.
                Если включить, будет использоваться вне зависимости от cache_ttl.
                При non_expired=False и cache_ttl=0 - кеш отключен.
            cache_maxsize (int, optional): Размер элементов в кеше.
            cache (AsyncBaseCache, optional): Пользовательская реализация кеша.
        """
        cls_query_table = AsyncQueryTable
        if cache and (TypeCache.remote == cache.type_cache):
            cls_query_table = AsyncRemoteQueryTable
        super().__init__(
            db, cls_query_table, 
            prefix_table, tables, table_schema
        )
        self._cache = cache or CacheQuery(cache_ttl, cache_maxsize, True, non_expired)
    
    async def init(self):
        if TypeCache.remote == self._cache.type_cache:
            _tables_struct = await self._cache._get_struct_tables()
            if _tables_struct:
                self._tables_struct = _tables_struct
                return
        if DBTypes.postgres == self._db.get_type():
            await self._fill_tables_pg_struct()
        elif DBTypes.sqlite == self._db.get_type():
            await self._fill_tables_sqlite_struct()
        if TypeCache.remote == self._cache.type_cache:
            await self._cache._save_struct_tables(self._tables_struct)
            
    async def query(
        self, sql: str,
        cache: bool = False,
        is_new_data: bool = False
    ) -> Optional[List[Tuple]]:
        """Выполнение произвольного SQL запроса.
        Могут выполняться запросы на изменения и получения данных.

        Args:
            sql (str): SQL запрос.
            cache (bool): Работать ли с кешем.
            is_new_data (bool): Установить новые данные из запроса, если вы работает с кешем.

        Returns:
            Optional[List[Tuple]]: Результат.
        """
        if cache and not is_new_data:
            if TypeCache.remote == self._cache.type_cache:
                data = await self._cache._get_data_query(sql)
            else:
                data = self._cache._get_data_query(sql)
            if data:
                return data
        async with self._db as db_query:
            await db_query.execute(sql)
            data = await db_query.fetchall()
        if cache:
            if TypeCache.remote == self._cache.type_cache:
                await self._cache._save_data_query(sql, data)
            else:
                self._cache._save_data_query(sql, data)
        return data
            
    async def clear_cache(self):
        """
            Вызов очищение всего кеша.
        """
        if TypeCache.remote == self._cache.type_cache:
            await self._cache.clear()
        else:
            self._cache.clear()
    
    async def _fill_tables_pg_struct(self):
        """
            Получает таблицы и название колоннок из postgres.
        """
        async with self._db as db_query:
            await db_query.execute(self._pg_query_struct)
            data = await db_query.fetchall()
        for row in data:
            if row[0] in self._tables_struct:
                self._tables_struct[row[0]].append(row[1])
            else:
                self._tables_struct[row[0]] = [row[1]]
                
    async def _fill_tables_sqlite_struct(self):
        """
            Получает таблицы и название колоннок из sqlite.
        """
        try:
            db_query = await self._db.connect()
            await db_query.execute("select name from sqlite_master where type='table';")
            rows = await db_query.fetchall()
            for row in rows:
                self._tables_struct[row[0]] = []
            for table in self._tables_struct.keys():
                await db_query.execute(f"PRAGMA table_info({table});")
                rows = await db_query.fetchall()
                for row in rows:
                    self._tables_struct[table].append(row[1])
        except Exception as e:
            raise ErrorLoadingStructTables(e)
        finally:
            await self._db.close()