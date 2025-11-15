from typing import Union
from query_tables.query.functions import Field
from query_tables.query.base_query import BaseQueryTable, BaseQuery, BaseJoin


class CommonJoin(BaseQuery, BaseJoin):
    
    def __init__(
        self, join_table: Union['BaseQueryTable', 'BaseQuery'], 
        join_field: Union[Field, str], ext_field: Union[Field, str],
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (Union[Field, str]): Поле join таблицы.
            ext_field (Union[Field, str]): Поле внешней таблицы.
            table_alias (str, optional): Псевдоним для таблицы. Нужен когда 
                одна и таже таблицы соединяется больше одного раза.
        """
        if issubclass(type(join_table), BaseQueryTable):
            query = join_table._query
        else:
            query = join_table
        if isinstance(join_field, Field):
            if query._table_name == join_field._table:
                query._join_field = join_field._field_name
            else:
                query._ext_field = join_field._field_name
                query._ext_table = join_field._table
        else:
            query._join_field = join_field
        if isinstance(ext_field, Field):
            if query._table_name == ext_field._table:
                query._join_field = ext_field._field_name
            else:
                query._ext_field = ext_field._field_name
                query._ext_table = ext_field._table
        else:
            query._ext_field = ext_field
        query._table_alias = table_alias
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
        join_field: Union[Field, str], ext_field: Union[Field, str],
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (Union[Field, str]): Поле join таблицы.
            ext_field (Union[Field, str]): Поле внешней таблицы.
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
        join_field: Union[Field, str], ext_field: Union[Field, str],
        table_alias: str = ''
    ):
        """
        Args:
            join_table (BaseQueryTable): Таблица для join к другой таблице.
            join_field (Union[Field, str]): Поле join таблицы.
            ext_field (Union[Field, str]): Поле внешней таблицы.
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