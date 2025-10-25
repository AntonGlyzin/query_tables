from typing import List, Any, Dict
import sqlite3
import aiosqlite
from query_tables.db.base_db_query import BaseSQLiteDBQuery, BaseAsyncSQLiteDBQuery


class SQLiteQuery(BaseSQLiteDBQuery):
    
    def __init__(self, path: str):
        self._path = path
        self.conn = None
        self.cursor = None
    
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


class AsyncSQLiteQuery(BaseAsyncSQLiteDBQuery):
    
    def __init__(self, path: str):
        self._path = path
        self.conn = None
        self.cursor = None
    
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