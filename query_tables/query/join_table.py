from typing import Union
from query_tables.query.base_query import BaseQueryTable, BaseQuery, BaseJoin


class CommonJoin(BaseQuery, BaseJoin):
    
    def __init__(
        self, join_table: Union['BaseQueryTable', 'BaseQuery'], 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (str): Поле join таблицы.
            ext_field (str): Поле внешней таблицы.
            table_alias (str, optional): Псевдоним для таблицы. Нужен когда 
                одна и таже таблицы соединяется больше одного раза.
        """
        if issubclass(type(join_table), BaseQueryTable):
            join_table._query._join_field = join_field
            join_table._query._ext_field = ext_field
            join_table._query._table_alias = table_alias
        else:
            join_table._join_field = join_field
            join_table._ext_field = ext_field
            join_table._table_alias = table_alias
        self.join_table = join_table
    
    def __getattribute__(self, name):
        try:
            join_table = object.__getattribute__(self, 'join_table')
            return object.__getattribute__(join_table, name)
        except AttributeError:
            return object.__getattribute__(self, name)


class Join(CommonJoin):
    """
        Обертка для join запросах.
    """    
    def __init__(
        self, join_table: Union['BaseQueryTable', 'BaseQuery'], 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (str): Поле join таблицы.
            ext_field (str): Поле внешней таблицы.
            table_alias (str, optional): Псевдоним для таблицы. Нужен когда 
                одна и таже таблицы соединяется больше одного раза.
        """
        if issubclass(type(join_table), BaseQueryTable):
            join_table._query._join_method = 'join'
        else:
            join_table._join_method = 'join'
        super().__init__(
            join_table, join_field,
            ext_field, table_alias
        )


class LeftJoin(CommonJoin):
    """
        Обертка для left join запросах.
    """    
    def __init__(
        self, join_table: Union['BaseQueryTable', 'BaseQuery'], 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (str): Поле join таблицы.
            ext_field (str): Поле внешней таблицы.
            table_alias (str, optional): Псевдоним для таблицы. Нужен когда 
                одна и таже таблицы соединяется больше одного раза.
        """
        if issubclass(type(join_table), BaseQueryTable):
            join_table._query._join_method = 'left join'
        else:
            join_table._join_method = 'left join'
        super().__init__(
            join_table, join_field,
            ext_field, table_alias
        )