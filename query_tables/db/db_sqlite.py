from typing import List, Any, Dict, Tuple
import sqlite3
import aiosqlite
import re
from query_tables.db.base_db_query import  DBTypes, BaseDBQuery, BaseAsyncDBQuery
from query_tables.exceptions import ErrorLoadingStructTables


class Placeholders(object):
    
    def change_placeholder(
            self, sql: str, params: dict = None
        ) -> Tuple[str, List]:
        """Замена плейсхолдеров для текущей БД.

        Args:
            sql (str): sql.
            params (dict): Параметры.

        Returns:
            Tuple[str, List]: sql и параметры (может быть изменен порядок).
        """
        if not params:
            return sql, []
        names = re.findall(self.pattern, sql)
        values = [params[name] for name in names]
        converted_sql = re.sub(self.pattern, '?', sql)
        return converted_sql, values


class SQLiteQuery(Placeholders, BaseDBQuery):
    
    def __init__(self, path: str):
        self._path = path
        self.conn = None
        self.cursor = None
        
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
    
    def connect(self) -> 'SQLiteQuery':
        """ Открываем соединение с курсором. """
        self.conn = sqlite3.connect(self._path)
        self.cursor = self.conn.cursor()
        return self
        
    def close(self):
        """ Закрываем соединение с курсором. """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def execute(self, query: str, params: Dict = None) -> 'SQLiteQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """
        sql, param = self.change_placeholder(query, params)
        self.cursor.execute(sql, param)
        self.conn.commit()
        return self

    def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """     
        return self.cursor.fetchall()


class AsyncSQLiteQuery(Placeholders, BaseAsyncDBQuery):
    
    def __init__(self, path: str):
        self._path = path
        self.conn = None
        self.cursor = None
    
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
    
    async def connect(self) -> 'AsyncSQLiteQuery':
        """ Открываем соединение с курсором. """
        self.conn = await aiosqlite.connect(self._path)
        self.cursor = await self.conn.cursor()
        return self
        
    async def close(self):
        """ Закрываем соединение с курсором. """
        if self.cursor:
            await self.cursor.close()
        if self.conn:
            await self.conn.close()

    async def execute(self, query: str, params: Dict = None) -> 'AsyncSQLiteQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """
        sql, param = self.change_placeholder(query, params)
        await self.cursor.execute(sql, param)
        await self.conn.commit()
        return self

    async def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """     
        return await self.cursor.fetchall()