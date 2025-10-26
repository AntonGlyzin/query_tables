from typing import List, Any, Dict, Tuple
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
    
    def set_placeholder_pattern(self, pattern: str, placeholder: str):
        """Установить паттерн и плейсхолдер.

        Args:
            pattern (str): Паттерн из query.
            placeholder (str): Плейсхолдер.
        """  
        self.pattern = pattern
        self.placeholder = placeholder
    
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
    
    def set_placeholder_pattern(self, pattern: str, placeholder: str):
        """Установить паттерн и плейсхолдер.

        Args:
            pattern (str): Паттерн из query.
            placeholder (str): Плейсхолдер.
        """  
        self.pattern = pattern
        self.placeholder = placeholder
    
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