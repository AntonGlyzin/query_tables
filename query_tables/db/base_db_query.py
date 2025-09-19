from typing import List, Any, Dict
from abc import ABC
from dataclasses import dataclass
from query_tables.exceptions import (
    ErrorLoadingStructTables
)


@dataclass
class DBTypes:
    sqlite = 1
    postgres = 2


class BaseDBQuery(ABC):
    
    def get_type(self) -> int:
        """
            Возвращает тип БД.
        """        
        ...
        
    def get_tables_struct(
            self, table_schema: str = None, 
            prefix_table: str = None, tables: List = None
        ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            table_schema (str): Название схемы.
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """        
        ...
    
    def connect(self) -> 'BaseDBQuery':
        """ Открываем соединение с курсором. """
        ...
        
    def close(self):
        """ Закрываем соединение с курсором. """
        ...
    
    def __enter__(self) -> 'BaseDBQuery':
        """Открывает соединение или получаем из пула."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрывает соединение с БД."""
        self.close()

    def execute(self, query: str) -> 'BaseDBQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """        
        ...

    def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """     
        ...


class BaseAsyncDBQuery(ABC):
    
    def get_type(self) -> int:
        """
            Возвращает тип БД.
        """        
        ...
        
    async def get_tables_struct(
            self, table_schema: str = None, 
            prefix_table: str = None, tables: List = None
        ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            table_schema (str): Название схемы.
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """        
        ...
    
    async def connect(self) -> 'BaseAsyncDBQuery':
        """ Открываем соединение с курсором. """
        ...
        
    async def close(self):
        """ Закрываем соединение с курсором. """
        ...
    
    async def __aenter__(self) -> 'BaseAsyncDBQuery':
        """Открывает соединение или получаем из пула."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает соединение с БД."""
        await self.close()

    async def execute(self, query: str) -> 'BaseAsyncDBQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """        
        ...

    async def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """     
        ...


class BaseDBPGStruct(object):
    
    def pg_query_struct(
        self, table_schema: str, prefix_table: str, tables: List
    ):
        query = """ 
            select it.table_name, ic.column_name
            from information_schema.tables it
            join information_schema.columns ic on it.table_name = ic.table_name 
                                                and it.table_schema = ic.table_schema
            where 1=1 
        """
        if table_schema:
            query += f" and it.table_schema = '{table_schema}'"
        if prefix_table:
            query += f" and it.table_name like '{prefix_table}%%'"
        elif tables:
            tables = ', '.join(f"'{i}'" for i in tables)
            query += f" and it.table_name in ({tables})"
        return query


class BaseSQLiteDBQuery(BaseDBQuery):
    
    def get_type(self):
        return DBTypes.sqlite
    
    def get_tables_struct(
        self, prefix_table: str = None, 
        tables: List = None, *args, **kwargs
    ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """ 
        tables_struct: Dict[str, List] = {}
        tables = tables or []
        try:
            db_query = self.connect()
            db_query.execute("select name from sqlite_master where type='table';")
            for row in db_query.fetchall():
                if not row[0]:
                    continue
                if tables and row[0] in tables:
                    tables_struct[row[0]] = []
                    continue
                if prefix_table and row[0].startswith(prefix_table):
                    tables_struct[row[0]] = []
                    continue
                tables_struct[row[0]] = []
            for table in tables_struct.keys():
                db_query.execute(f"PRAGMA table_info({table});")
                for row in db_query.fetchall():
                    tables_struct[table].append(row[1])
        except Exception as e:
            raise ErrorLoadingStructTables(e)
        finally:
            self.close()
        return tables_struct


class BasePostgreDBQuery(BaseDBQuery, BaseDBPGStruct):
    
    def get_type(self):
        return DBTypes.postgres
    
    def get_tables_struct(
        self, table_schema: str = None, 
        prefix_table: str = None, tables: List = None
    ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            table_schema (str): Название схемы.
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """ 
        tables_struct: Dict[str, List] = {}
        query = self.pg_query_struct(table_schema, prefix_table, tables)
        with self as db_query:
            db_query.execute(query)
            data = db_query.fetchall()
        for row in data:
            if row[0] in tables_struct:
                tables_struct[row[0]].append(row[1])
            else:
                tables_struct[row[0]] = [row[1]]
        return tables_struct


class BaseAsyncSQLiteDBQuery(BaseAsyncDBQuery):
    
    def get_type(self):
        return DBTypes.sqlite
    
    async def get_tables_struct(
        self, prefix_table: str = None, 
        tables: List = None, *args, **kwargs
    ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """ 
        tables_struct: Dict[str, List] = {}
        tables = tables or []
        try:
            db_query = await self.connect()
            await db_query.execute("select name from sqlite_master where type='table';")
            rows = await db_query.fetchall()
            for row in rows:
                if not row[0]:
                    continue
                if tables and row[0] in tables:
                    tables_struct[row[0]] = []
                    continue
                if prefix_table and row[0].startswith(prefix_table):
                    tables_struct[row[0]] = []
                    continue
                tables_struct[row[0]] = []
            for table in tables_struct.keys():
                await db_query.execute(f"PRAGMA table_info({table});")
                rows = await db_query.fetchall()
                for row in rows:
                    tables_struct[table].append(row[1])
        except Exception as e:
            raise ErrorLoadingStructTables(e)
        finally:
            await self.close()
        return tables_struct


class BaseAsyncPostgreDBQuery(BaseAsyncDBQuery, BaseDBPGStruct):
    
    def get_type(self):
        return DBTypes.postgres
    
    async def get_tables_struct(
        self, table_schema: str = None, 
        prefix_table: str = None, tables: List = None
    ) -> Dict[str, List]:
        """Получение структуры.

        Args:
            table_schema (str): Название схемы.
            prefix_table (str): Префикс таблиц.
            tables (List): Таблицы.

        Returns:
            Dict[str, List]: Название таблиц и полей.
        """ 
        tables_struct: Dict[str, List] = {}
        query = self.pg_query_struct(table_schema, prefix_table, tables)
        async with self as db_query:
            await db_query.execute(query)
            data = await db_query.fetchall()
        for row in data:
            if row[0] in tables_struct:
                tables_struct[row[0]].append(row[1])
            else:
                tables_struct[row[0]] = [row[1]]
        return tables_struct