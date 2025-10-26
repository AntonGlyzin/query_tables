from abc import ABC
from typing import List, Optional, Dict, Union


class BaseJoin(ABC): ...


class BaseQueryTable(object): ...


class BaseQuery(ABC):
    
    @property
    def params(self):
        """Параметры для вставки в sql."""
        ...
    
    @property
    def map_fields(self) -> List[str]:
        """Поля участвующие в выборки.
            Если в выборке есть join, то формат полей: <таблица><поле>
        
        Returns:
            List: Список полей.
        """        
        ...

    @property
    def tables_query(self) -> List[str]:
        """Привязанные JOIN таблицы к запросу.

        Returns:
            List: Список таблиц.
        """        
        ...
        
    @property
    def is_table_joined(self) -> bool:
        """
            Участвует ли таблица в JOIN связке.
        """
        ...

    def select(self, fields: Optional[List[str]] = None) -> 'BaseQuery':
        """Устанавливает поля для выборки.

        Args:
            fields (List[str]): Поля из БД.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...

    def join(self, table: Union[BaseJoin, 'BaseQuery']) -> 'BaseQuery':
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (Union[BaseJoin, 'BaseQuery']): Таблица которая присоединяется.

        Returns:
            BaseQuery: Экземпляр запроса.
        """ 
        ...

    def filter(self, **params) -> 'BaseQuery':
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            params: Параметры выборки.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...
    
    def group_by(self, params: list[str]) -> 'BaseQuery':
        """Группировка записей по полю.

        Args:
            params (list[str]): Список строк.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...
    
    def having(self, **params) -> 'BaseQuery':
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            params: Параметры выборки.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...

    def order_by(self, **params) -> 'BaseQuery':
        """Сортировка для sql запроса.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...

    def limit(self, value: int) -> 'BaseQuery':
        """Ограничение записей в sql запросе.

        Args:
            value (int): Экземпляр запроса.
        
        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...
    
    def offset(self, value: int) -> 'BaseQuery':
        """Смещение.

        Args:
            value (int): Смещение по записям.
        
        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...

    def get(self) -> str:
        """Запрос на получение записей.
        
        Raises:
            DublicatTableNameQuery: Ошибка псевдонима JOIN таблиц.

        Returns:
            str: SQL запрос.
        """        
        ...

    def update(self, **params) -> str:
        """Запрос на обновление записей по фильтру.
        
        Args:
            params: Параметры для обновления.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """        
        ...

    def insert(self, records: List[Dict]) -> str:
        """Вставка записи.
        
        Args:
            params: Параметры для вставки.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """        
        ...

    def delete(self) -> str:
        """Запрос на удаление записей.
        
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """        
        ...