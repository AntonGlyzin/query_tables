from typing import Union, Any, List, Optional, Dict
from query_tables.query import BaseJoin, BaseQuery
from query_tables.exceptions import (
    NotFieldQueryTable, 
    ErrorConvertDataQuery,
    ErrorExecuteJoinQuery,
    ErrorAliasTableJoinQuery
)

class Query(BaseQuery):
    """
        Отвечает за сборку sql запросов.
    """    
    def __init__(self, table_name: str, fields: List):
        """
        Args:
            table_name (str): Название таблицы.
            fields (List): Название полей в таблице.
        """
        self._table_name = table_name
        self._fields = fields # Все поля в формате <поле> из текущей таблицы.
        self._user_fields = [] # Пользовательские подля в формате <поле> текущей таблицы.
        # Формат поля <таблица>.<поле> 
        self._map_select = [
            f'{self._table_name}.{field}' for field in self._fields
        ]
        self._from = f' from {self._table_name}'
        self._delete = f'delete from {self._table_name} '
        self._insert = f'insert into {self._table_name} '
        self._update = f'update {self._table_name} set '
        self._join = ''
        self._joined_tables: List[BaseQuery] = []
        self._where = ''
        self._order_by = ''
        self._limit = ''
        self._operators = {
            'ilike': 'ilike',
            'like': 'like',
            'in': 'in',
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
            'between': 'between',
            'isnull': 'is null',
            'isnotnull': 'is not null',
            'notequ': '!='
        }
        # если текущая таблица соединяется с другой
        self.join_field = ''
        self.ext_field = ''
        self.table_alias = ''
        self.join_method = ''

    @property
    def map_fields(self) -> List:
        """Поля участвующие в выборки.
            Если в выборке есть join, то формат полей: <таблица><поле>
        
        Returns:
            List: Список полей.
        """
        return self._map_select

    @property
    def tables_query(self) -> List[str]:
        """Привязанные JOIN таблицы к запросу.

        Returns:
            List: Список таблиц.
        """  
        tables = set()
        for table in self.is_table_joined:
            tables.add(table._table_name)
        return list(tables)
    
    @property
    def is_table_joined(self) -> bool:
        """
            Участвует ли таблица в JOIN связке.
        """        
        if self._join or self.join_method:
            return True
        return False
    
    def select(self, fields: Optional[List[str]] = None) -> 'Query':
        """Устанавливает поля для выборки.

        Args:
            fields (List[str]): Поля из БД.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        if not fields:
            return self
        self._exist_fields(fields)
        self._map_select = list(filter(
            lambda x: not x.startswith(f'{self._table_name}.'),
            self._map_select
        ))
        for field in fields:
            self._user_fields.append(field)
            self._map_select.append(f'{self._table_name}.{field}')
        return self

    def join(self, table: BaseJoin) -> 'Query':
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (BaseJoin): Таблица которая присоединяется.

        Returns:
            BaseQuery: Экземпляр запроса.
        """ 
        self._exist_field(table.ext_field)
        table._exist_field(table.join_field)
        table_alias = table.table_alias or table._table_name
        for table_field in table._map_select:
            table_name, field = table_field.split('.')
            if table_name == table._table_name:
                self._map_select.append(f"{table_alias}.{field}")
            else:
                self._map_select.append(table_field)
        table._map_select.clear()        
        fields = table._user_fields or table._fields
        for field in fields:
            table._map_select.append(f"{table._table_name}.{field}")
        self._joined_tables.append(table)
        self._joined_tables.extend(table._joined_tables)
        table._joined_tables.clear()    
        self._join += (
            f" {table.join_method} ({table.get()}) as {table_alias} "
            f"on {table_alias}.{table.join_field} = {self._table_name}.{table.ext_field}"
        ) + table._join
        table._join = ''
        return self

    def filter(self, **params) -> 'Query':
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            params: Параметры выборки.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        where = []
        for field, value in params.items():
            _field, operator = self._get_operator_by_field(field)
            self._exist_field(_field)
            val = self._convert_simple_format_data(value)
            where.append(
                f'{self._table_name}.{_field} {operator} {val}'
            )
        if where:
            self._where = ' where '
            self._where += ' and '.join(where)
        return self

    def order_by(self, **kwargs) -> 'Query':
        """Сортировка для sql запроса.

        Returns:
            BaseQuery: Экземпляр запроса.
        """
        order_by = []
        for field, order in kwargs.items():
            order_by.append(
                f'{self._table_name}.{field} {order}'
            )
        if order_by:
            self._order_by = ' order by '
            self._order_by += ', '.join(order_by)
        return self

    def limit(self, value: int) -> 'Query':
        """Ограничение записей в sql запросе.

        Args:
            value (int): Экземпляр запроса.
        
        Returns:
            BaseQuery: Экземпляр запроса.
        """
        self._limit = f' limit {value}'
        return self

    def get(self) -> str:
        """Запрос на получение записей.
        
        Raises:
            ErrorAliasTableJoinQuery: Ошибка псевдонима JOIN таблиц.

        Returns:
            str: SQL запрос.
        """
        for table1 in self._joined_tables:
            if not table1.table_alias:
                continue
            table_alias = True
            # если у таблицы есть псевдоним, 
            # то должна быть еще одна таблицы без псевдонима
            for table2 in self._joined_tables:
                if table1._table_name == table2._table_name:
                    if not table2.table_alias:
                        table_alias = False
                        break
            if table_alias:
                raise ErrorAliasTableJoinQuery(table1._table_name)
        select = 'select ' + ', '.join(self._map_select)
        return (
            f"{select}"
            f"{self._from}"
            f"{self._join}"
            f"{self._where}"
            f"{self._order_by}"
            f"{self._limit}"
        ).strip()

    def update(self, **params) -> str:
        """Запрос на обновление записей по фильтру.
        
        Args:
            params: Параметры которые будут обновляться.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('update')
        fields = []
        set_fields = ''
        for field, value in params.items():
            self._exist_field(field)
            val = self._convert_simple_format_data(value)
            fields.append(f'{field} = {val}')
        if fields:
            set_fields = ', '.join(fields)
        return (
            f"{self._update}"
            f"{set_fields}"
            f"{self._where}"
        ).strip()
        

    def insert(self, records: List[Dict]) -> str:
        """Вставка записи.
        
        Args:
            params: Строка для вставки.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """ 
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('insert')
        fields = list(records[0].keys())
        self._exist_fields(fields)
        into_values = []
        for record in records:
            values = []
            for field in fields:
                if record[field] is None:
                    continue
                val = self._convert_simple_format_data(record[field])
                values.append(val)
            into_values.append('({})'.format(', '.join(values)))
        text_fields = '({})'.format(', '.join(fields))
        text_values = ' values {}'.format(', '.join(into_values))
        return (
            f"{self._insert}"
            f'{text_fields}'
            f'{text_values}'
        ).strip()

    def delete(self) -> str:
        """Запрос на удаление записей.
        
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """ 
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('delete')
        return (
            f"{self._delete}"
            f"{self._where}"
        ).strip()
        
    def _exist_fields_identity(
        self, fields: List, exclude_fields: Optional[List] = None, exception: bool = True
    ) -> bool:
        """Проверить что все поля в таблицы предоставлены в списке.

        Args:
            fields (List): Список полей.
            exception (bool, optional): Нужно ли искючение.
            
        Raises:
            NotFieldQueryTable: Нет такого поля.

        Returns:
            bool: Успешность.
        """
        common_fields = set(self._fields) & set(fields)
        if exclude_fields:
            common_fields -= set(exclude_fields)
        need_fields = set(self._fields) - set(exclude_fields)
        if len(common_fields) == len(need_fields):
            return True
        if exception:
            raise NotFieldQueryTable(self._table_name, str(fields))
        return False
    
    def _exist_fields(
        self, fields: List, exception: bool = True
    ) -> bool:
        """Проверить список полей, что они есть в таблице.

        Args:
            fields (List): Поля.
            exception (bool, optional): Нужно ли вызывать исключение.

        Raises:
            NotFieldQueryTable: Нет такого поля.

        Returns:
            bool: Успешность.
        """
        common_fields = set(self._fields) & set(fields)
        if len(common_fields) == len(fields):
            return True
        if exception:
            raise NotFieldQueryTable(self._table_name, str(fields))
        return False

    def _exist_field(self, field: str, exception: bool = True) -> bool:
        """Проверка. Есть ли данное поле в таблице.

        Args:
            field (str): Поле.
            exception (bool, optional): Выбрасывать ли исключение. Defaults to True.

        Raises:
            NotFieldQueryTable: Нет поля в таблице.

        Returns:
            Union[bool]: Проверка есть ли поле в таблице.
        """        
        if field not in self._fields:
            if exception:
                raise NotFieldQueryTable(self._table_name, field)
            else:
                return False
        return True
        
    def _get_operator_by_field(self, field: str) -> tuple[str, str]:
        """Получение оператора из названия поля.

        Args:
            field (str): Поле.

        Returns:
            tuple[str, str]: Название поля и оператор
        """        
        field_operator = field.split('__')
        if len(field_operator) >= 2:
            _field = field_operator[0]
            operator = field_operator[-1]
            if self._operators.get(operator):
                return _field, self._operators.get(operator)
        return field, '='

    def _convert_simple_format_data(
        self, value: Optional[Union[list, tuple, int, float, str, bool]] = None
    ) -> Any:
        """Конвертация данных в нативные типы для sql.

        Args:
            value (Union[list, tuple, int, float, str, bool]): Значение.

        Raises:
            ErrorConvertDataQuery: Ошибка конвертации.

        Returns:
            Any: Сконвертированное значение.
        """        
        if value is None:
            return ''
        if isinstance(value, tuple):
            if len(value) == 2:
                return "{} and {}".format(*[
                    self._convert_simple_format_data(item) for item in value
                ])
            if len(value) > 2:
                value = list(value)
        if isinstance(value, list):
            value = [
                self._convert_simple_format_data(item) for item in value
            ]
            return "({})".format(','.join(map(str, value)))
        elif isinstance(value, (int, float)):
            return f'{value}'
        elif isinstance(value, str):
            return "'{}'".format(value)
        elif isinstance(value, bool):
            ret_value = 'true' if value else 'false'
            return ret_value
        raise ErrorConvertDataQuery(value)