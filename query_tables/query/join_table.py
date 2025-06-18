from query_tables.query import CommonJoin, BaseQuery


class Join(CommonJoin):
    """
        Обертка для join запросах.
    """    
    def __init__(
        self, join_table: 'BaseQuery', 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        super().__init__(
            join_table, join_field,
            ext_field, table_alias
        )
        self.join_table.join_method = 'join'


class LeftJoin(CommonJoin):
    """
        Обертка для left join запросах.
    """    
    def __init__(
        self, join_table: 'BaseQuery', 
        join_field: str, ext_field: str,
        table_alias: str = ''
    ):
        super().__init__(
            join_table, join_field,
            ext_field, table_alias
        )
        self.join_table.join_method = 'left join'