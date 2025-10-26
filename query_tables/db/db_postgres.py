from typing import List, Any, Dict, Tuple
from psycopg2.pool import ThreadedConnectionPool
import time
from dataclasses import dataclass
import asyncpg
import re
import asyncio
from asyncpg.connection import Connection
from query_tables.db.base_db_query import  DBTypes, BaseDBQuery, BaseAsyncDBQuery
from query_tables.exceptions import ErrorConnectDB
from query_tables.translate import _
from query_tables.utils import logger


class PGQueryStruct(object):
    
    def pg_query_struct(
            self, table_schema: str, 
            prefix_table: str, tables: List
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


class PostgresQuery(PGQueryStruct, BaseDBQuery):
    
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
        return sql, params
    
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
            logger.error(_("Ошибка при подключении к базе данных: {}").format(e))
            return False
        
    def __del__(self):
        self.close_pool()
        
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

    def execute(self, query: str, params: Dict = None) -> 'PostgresQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
            params (dict): Параметры.
        """
        try:
            self._cursor.execute(query, params)
            self._conn.commit()
        except Exception as e:
            logger.error(_("Ошибка при выполнении SQL-запроса: {}").format(e))
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
                logger.error(_("Ошибка при получение результата из запроса: {}").format(e))


class AsyncPostgresQuery(PGQueryStruct, BaseAsyncDBQuery):
    
    def __init__(self, config: DBConfigPg):
        self._config = config
        self._pool = None
        self._conn: Connection = None
        self._cursor = None
        self._res = None
        
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
        converted_sql = sql
        for i, name in enumerate(names, 1):
            new_name = self.placeholder.format(name)
            converted_sql = converted_sql.replace(new_name, f'${i}')
        return converted_sql, values
    
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
            logger.error(_("Ошибка при подключении к базе данных: {}").format(e))
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
            logger.error(_("Ошибка при открытие соединения с курсором к БД: {}").format(e))
        return self

    async def close(self):
        """ Закрываем соединение с курсором. """
        if self._conn is not None:
            await self._pool.release(self._conn)
            self._conn = None
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def execute(self, query: str, params: Dict = None) -> 'AsyncPostgresQuery':
        """Выполнение запроса.

        Args:
            query (str): SQL запрос.
            params (tuple): Параметры.
        """
        try:
            sql, param = self.change_placeholder(query, params)
            self._res = await self._conn.fetch(sql, *param)
        except Exception as e:
            logger.error(_("Ошибка при выполнении SQL-запроса: {}").format(e))
        return self

    async def fetchall(self) -> List[Tuple]:
        """Получение данных из запроса.

        Returns:
            List: Результирующий список.
        """
        if not self._res:
            return []
        return [tuple(row) for row in self._res]