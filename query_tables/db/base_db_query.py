from typing import List, Any
from abc import ABC
from dataclasses import dataclass

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


class BaseSQLiteDBQuery(BaseDBQuery):
    
    def get_type(self):
        return DBTypes.sqlite


class BasePostgreDBQuery(BaseDBQuery):
    
    def get_type(self):
        return DBTypes.postgres
    
    
class BaseAsyncSQLiteDBQuery(BaseAsyncDBQuery):
    
    def get_type(self):
        return DBTypes.sqlite


class BaseAsyncPostgreDBQuery(BaseAsyncDBQuery):
    
    def get_type(self):
        return DBTypes.postgres