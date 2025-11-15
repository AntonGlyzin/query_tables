from abc import ABC
from typing import List, Dict, Union

class BaseField(ABC): ...

class BaseFunctions(ABC): ...

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
    
    def distinct(self) -> 'BaseQuery':
        """Включает distinct в запрос. 
        
        Returns:
            QueryTable: Экземпляр запроса.
        """
        ...

    def select(self, *args: Union[BaseField, BaseFunctions, str, List[str]]) -> 'BaseQuery':
        """Устанавливает поля для выборки.

        Args:
            args : Поля из БД. `Field('company', 'name'), Max(Field('person', 'age')).as_('person_age')` или `['id', 'name']`

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

    def filter(self, *args: Union[BaseJoin, BaseFunctions, BaseField], **params) -> 'BaseQuery':
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...
    
    def group_by(self, *args: Union[BaseField, str, List[str]]) -> 'BaseQuery':
        """Группировка записей по полю.

        Args:
            args: Поля для группировки. `Field('company', 'name')` или `['name']`

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...
    
    def having(self, *args: Union[BaseJoin, BaseFunctions, BaseField], **params) -> 'BaseQuery':
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        ...

    def order_by(self, *args: Union[BaseField], **kwargs) -> 'BaseQuery':
        """Сортировка для sql запроса.
        
        Args:
            args: Параметры сортировки. `Field('company', 'name').desc()`
            params: Параметры сортировки. `age=Ordering.DESC`

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