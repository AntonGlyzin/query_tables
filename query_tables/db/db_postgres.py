from typing import List, Any, Dict, Optional
from psycopg2.pool import ThreadedConnectionPool
from dataclasses import dataclass
import asyncpg
from query_tables.db import BasePostgreDBQuery, BaseAsyncPostgreDBQuery
from query_tables.exceptions import ErrorConnectDB, ErrorExecuteQueryDB


@dataclass
class DBConfigPg:
    host: str = ''
    database: str = ''
    user: str = ''
    password: str = ''
    port: int = 5432
    minconn: int = 1
    maxconn: int = 10
    
    def get_conn(self) -> Dict:
        return dict(
            host = self.host,
            database = self.database,
            user = self.user,
            password = self.password,
            port = self.port
        )


class PostgresQuery(BasePostgreDBQuery):
    
    def __init__(self, config: DBConfigPg):
        self._config = config
        self._pool = None
        self._conn = None
        self._cursor = None
        self.create_pool()
        
    def create_pool(self):
        """
            Создаем пул соединений.
        """        
        try:
            self._pool = ThreadedConnectionPool(
                self._config.minconn, self._config.maxconn,
                **self._config.get_conn()
            )
        except Exception as e:
            raise ErrorConnectDB(e)
        
    def close_pool(self):
        """
            Закрывает все соединения в пуле.
        """
        if self._pool:     
            self._pool.closeall()
            self._pool = None
    
    def connect(self) -> 'PostgresQuery':
        """ Открываем соединение с курсором. """
        try:
            self._conn = self._pool.getconn()
            self._cursor = self._conn.cursor()
        except Exception as e:
            raise ErrorConnectDB(e)
        return self
        
    def close(self):
        """ Закрываем соединение с курсором. """
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn is not None:
            self._pool.putconn(self._conn)
            self._conn = None

    def execute(self, query: str) -> 'PostgresQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """
        try:
            self._cursor.execute(query)
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            raise ErrorExecuteQueryDB(e)
        return self

    def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """     
        return self._cursor.fetchall()


class AsyncPostgresQuery(BaseAsyncPostgreDBQuery):
    
    def __init__(self, config: DBConfigPg):
        self._config = config
        self._pool = None
        self._conn = None
        self._cursor = None
        self._res = None

    async def create_pool(self):
        """ Создаем пул соединений к БД. """
        try:
            self._pool = await asyncpg.create_pool(**self._config.get_conn())
        except Exception as e:
            raise ErrorConnectDB(e)

    async def close_pool(self):
        """ Закрываем весь пул соединений. """
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            
    async def connect(self) -> 'AsyncPostgresQuery':
        """ Открываем соединение с курсором. """
        try:
            if self._pool is None:
                await self.create_pool()
            self._conn = await self._pool.acquire()
        except Exception as e:
            raise ErrorConnectDB(e)
        return self

    async def close(self):
        """ Закрываем соединение с курсором. """
        if self._conn is not None:
            await self._pool.release(self._conn)
            self._conn = None

    async def execute(self, query: str) -> 'AsyncPostgresQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """
        try:
            self._res = await self._conn.fetch(query)
        except Exception as e:
            raise ErrorExecuteQueryDB(e)
        return self

    async def fetchall(self) -> List[dict]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """
        return self._res