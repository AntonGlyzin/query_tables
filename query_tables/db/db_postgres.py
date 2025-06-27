from typing import List, Any, Dict
import logging
from psycopg2.pool import ThreadedConnectionPool
import time
from dataclasses import dataclass
import asyncpg
import asyncio
from query_tables.db import BasePostgreDBQuery, BaseAsyncPostgreDBQuery
from query_tables.exceptions import ErrorConnectDB

logger = logging.getLogger(__name__)

@dataclass
class DBConfigPg:
    host: str = '127.0.0.1'
    database: str = ''
    user: str = ''
    password: str = ''
    port: int = 5432
    minconn: int = 1
    maxconn: int = 10
    
    def get_conn(self) -> Dict:
        return {
            'host': self.host,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }


class PostgresQuery(BasePostgreDBQuery):
    
    def __init__(self, config: DBConfigPg):
        self._config = config
        self._pool = None
        self._conn = None
        self._cursor = None
        while True:
            res = self.create_pool()
            if res:
                break
            time.sleep(3)
        
    def create_pool(self):
        """
            Создаем пул соединений.
        """        
        try:
            self.close_pool()
            self._pool = ThreadedConnectionPool(
                self._config.minconn, self._config.maxconn,
                **self._config.get_conn()
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            return False
        
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
            logger.error(f"Ошибка при выполнении SQL-запроса: {e}")
        return self

    def fetchall(self) -> List[Any]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """
        try:
            return self._cursor.fetchall()
        except Exception as e:
            if str(e).startswith('no results to fetch'):
                pass  # Игнорируем ошибку, если операция не возвращает строк
            else:
                logger.error(f"Ошибка при получение результата из запроса: {e}")


class AsyncPostgresQuery(BaseAsyncPostgreDBQuery):
    
    def __init__(self, config: DBConfigPg):
        self._config = config
        self._pool = None
        self._conn = None
        self._cursor = None
        self._res = None
        
    async def _create_pool(self):
        """ Создаем пул соединений к БД. """
        try:
            self._pool = await asyncpg.create_pool(
                **self._config.get_conn(), 
                min_size=self._config.minconn, 
                max_size=self._config.maxconn
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            return False

    async def create_pool(self):
        """ Создаем пул соединений к БД. """
        while True:
            res = await self._create_pool()
            if res:
                break
            await asyncio.sleep(3)

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
            logger.error(f"Ошибка при открытие соединения с курсором к БД: {e}")
        return self

    async def close(self):
        """ Закрываем соединение с курсором. """
        if self._conn is not None:
            await self._pool.release(self._conn)
            self._conn = None
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def execute(self, query: str) -> 'AsyncPostgresQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
        """
        try:
            res = await self._conn.fetch(query)
            self._res = []
            for row in res:
                self._res.append(tuple(row))
        except Exception as e:
            logger.error(f"Ошибка при выполнении SQL-запроса: {e}")
        return self

    async def fetchall(self) -> List[dict]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """
        return self._res