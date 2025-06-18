from abc import ABC
from typing import List, Optional, Dict, Union


class BaseJoin(ABC):
    ...


class BaseQuery(ABC):
    
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

    def get(self) -> str:
        """Запрос на получение записей.
        
        Raises:
            ErrorAliasTableJoinQuery: Ошибка псевдонима JOIN таблиц.

        Returns:
            str: SQL запрос.
        """        
        ...

    def update(self, **params) -> str:
        """Запрос на обновление записей по фильтру.
        
        Args:
            params: Параметры которые будут обновляться.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """        
        ...

    def insert(self, records: List[Dict]) -> str:
        """Вставка записи.
        
        Args:
            params: Строка для вставки.
            
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


class CommonJoin(BaseQuery):
    def __init__(
        self, join_table: 'BaseQuery', 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQuery): Таблица для join к другой таблице.
            join_field (str): Поле join таблицы.
            ext_field (str): Поле внешней таблицы.
            table_alias (str, optional): Псевдоним для таблицы. Нужен когда 
                одна и таже таблицы соединяется больше одного раза.
        """
        self.join_table: 'BaseQuery' = getattr(join_table, '_query', None) or join_table
        self.join_table.join_field = join_field
        self.join_table.ext_field = ext_field
        self.join_table.table_alias = table_alias
    
    def __getattribute__(self, name):
        try:
            join_table = object.__getattribute__(self, 'join_table')
            return object.__getattribute__(join_table, name)
        except AttributeError:
            return object.__getattribute__(self, name)