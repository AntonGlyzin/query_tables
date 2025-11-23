from __future__ import annotations
from abc import ABC
from typing import List, Dict, Union, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from query_tables.query.join_table import CommonJoin
    from query_tables.query.functions import Field, Functions
    from query_tables.query_table import BuilderQueryTable


class BaseJoin(ABC): ...

class BaseQueryTable(ABC): ...

class BaseQuery(Protocol):
    
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
        """Таблицы участвующие в запросе.

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
    
    def distinct(self) -> BuilderQueryTable:
        """Включает distinct в запрос. 
        
        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...

    def select(self, *args: Union[Field, Functions, str, List[str]]) -> BuilderQueryTable:
        """Устанавливает поля для выборки.

        Args:
            args : Поля из БД. `Field('company', 'name'), Max(Field('person', 'age')).as_('person_age')` или `['id', 'name']`

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...

    def join(self, table: Union[CommonJoin, BuilderQueryTable]) -> BuilderQueryTable:
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (Union[CommonJoin, BuilderQueryTable]): Таблица которая присоединяется.

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """ 
        ...

    def filter(self, *args: Union[CommonJoin, Field, Functions], **params) -> BuilderQueryTable:
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...
    
    def group_by(self, *args: Union[Field, str, List[str]]) -> BuilderQueryTable:
        """Группировка записей по полю.

        Args:
            args: Поля для группировки. `Field('company', 'name')` или `['name']`

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...
    
    def having(self, *args: Union[CommonJoin, Field, Functions], **params) -> BuilderQueryTable:
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...

    def order_by(self, *args: Union[Field], **kwargs) -> BuilderQueryTable:
        """Сортировка для sql запроса.
        
        Args:
            args: Параметры сортировки. `Field('company', 'name').desc()`
            params: Параметры сортировки. `age=Ordering.DESC`

        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...

    def limit(self, value: int) -> BuilderQueryTable:
        """Ограничение записей в sql запросе.

        Args:
            value (int): Экземпляр запроса.
        
        Returns:
            BuilderQueryTable: Экземпляр запроса.
        """
        ...
    
    def offset(self, value: int) -> BuilderQueryTable:
        """Смещение.

        Args:
            value (int): Смещение по записям.
        
        Returns:
            BuilderQueryTable: Экземпляр запроса.
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

    def insert(self, *args: Union[List[Dict]], **params) -> str:
        """Вставка записи.
        
        Args:
            records: Параметры для вставки.
            
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