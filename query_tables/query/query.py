from datetime import datetime
from typing import Union, Any, List, Dict, Tuple
from query_tables.query.base_query import BaseQuery, BaseJoin
from query_tables.query.condition import AND, Condition
from query_tables.query.functions import (
    ListOperators, 
    Field, 
    Functions,
    PLACEHOLDER,
    PLACEHOLDER_PATTERN,
    PLACEHOLDER_VARIABLE
)
from query_tables.exceptions import (
    NotFieldQueryTable,
    ErrorExecuteJoinQuery,
    DublicatTableNameQuery,
    NotExistOperatorFilter
)


class Query(BaseQuery):
    """
        Отвечает за сборку sql запросов.
    """
    PLACEHOLDER = PLACEHOLDER
    PLACEHOLDER_PATTERN = PLACEHOLDER_PATTERN
    PLACEHOLDER_VARIABLE = PLACEHOLDER_VARIABLE
    
    OPERATORS = {
        'ilike': 'ilike',
        'notilike': 'not ilike',
        'like': 'like',
        'notlike': 'not like',
        'in': 'in',
        'notin': 'not in',
        'gt': '>',
        'gte': '>=',
        'lt': '<',
        'lte': '<=',
        'notequ': '!=',
        'between': 'between',
        'notbetween': 'not between',
        'isnull': 'is null',
        'isnotnull': 'is not null',
        'iregex': '~*',
        'notiregex': '!~*',
        'regex': '~',
        'notregex': '!~',
    }
    
    def __init__(self, table_name: str, fields: List):
        """
        Args:
            table_name (str): Название таблицы.
            fields (List): Название полей в таблице.
        """
        self._table_name = table_name
        self._fields: List[str] = fields # Все поля в формате <поле> из текущей таблицы.
        self._user_fields = []
        # Карта <таблица>.<поле> или <поле> для построение словаря.
        self._map_select = [
            f'{self._table_name}.{field}' 
            for field in self._fields
        ]
        self._joined_tables: List['Query'] = []
        self._where: List[Union[Condition, ListOperators]] = []
        self._group_by: List[Union[Field, Functions]] = []
        self._having: List[Union[Condition, ListOperators]] = []
        self._order_by: List[Union[Field, Functions]] = []
        self._limit = ''
        self._offset = ''
        self._params: Dict[str, Any] = {}
        # если текущая таблица соединяется с внешней
        self._join_field = ''
        self._ext_field = ''
        self._ext_table = ''
        self._table_alias = ''
        self._join_method = ''
        
    def __str__(self):
        table_alias = self._table_alias or self._table_name
        cls_name = __class__.__name__
        return f'<{cls_name}({table_alias})>'
    
    def __repr__(self):
        return str(self)
    
    @property
    def params(self):
        """Параметры для вставки в sql."""        
        return self._params

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
        """Таблицы участвующие в запросе.

        Returns:
            List: Список таблиц.
        """  
        tables = set()
        tables.add(self._table_name)
        for table in self._joined_tables:
            tables.add(table._table_name)
        return list(tables)
    
    @property
    def is_table_joined(self) -> bool:
        """
            Участвует ли таблица в JOIN связке.
        """        
        if self._joined_tables:
            return True
        return False
    
    def select(self, *args: Union[Field, Functions, List[str]]) -> 'Query':
        """Устанавливает поля для выборки.

        Args:
            args : Поля из БД. `Field('company', 'name'), Max(Field('person', 'age')).as_('person_age')` или `['id', 'name']`

        Returns:
            Query: Экземпляр запроса.
        """
        if not args:
            self._map_select.clear()
            return self
        for field in args:
            if issubclass(type(field), ListOperators):
                self._user_fields.append(field._set_query(self))
            elif isinstance(field, list):
                for field_name in field:
                    self._user_fields.append(Field(self._table_name, field_name)._set_query(self))
        return self

    def join(self, table: Union['BaseJoin', 'Query']) -> 'Query':
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (BaseJoin): Таблица которая присоединяется.

        Returns:
            Query: Экземпляр запроса.
        """
        if issubclass(type(table), BaseJoin):
            table = table.join_table
        if not table._ext_table:
            table._ext_table = self._table_name
        self._joined_tables.append(table)
        self._check_field(table._table_name, table._join_field)
        self._check_field(table._ext_table, table._ext_field)
        return self

    def filter(self, *args: Union[Condition, Functions, Field], **params) -> 'Query':
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            Query: Экземпляр запроса.
        """
        for cond in args:
            if issubclass(type(cond), Condition) or issubclass(type(cond), ListOperators):
                self._where.append(cond._set_query(self))
        if params:
            self._where.append(AND(**params)._set_query(self))
        return self
    
    def group_by(self, *args: Union[Field, List[str]]) -> 'Query':
        """Группировка записей по полю.

        Args:
            args: Поля для группировки. `Field('company', 'name')` или `['name']`

        Returns:
            Query: Экземпляр запроса.
        """
        for field in args:
            if issubclass(type(field), ListOperators):
                self._group_by.append(field._set_query(self))
            elif isinstance(field, list):
                for field_name in field:
                    self._group_by.append(Field(self._table_name, field_name)._set_query(self))
        return self
    
    def having(self, *args: Union[Condition, Functions, Field], **params) -> 'Query':
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            args: Параметры выборки. `AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))`
            params: Параметры выборки. `registration__between=('2021-01-02', '2021-04-06')`

        Returns:
            Query: Экземпляр запроса.
        """
        for cond in args:
            if issubclass(type(cond), Condition) or issubclass(type(cond), ListOperators):
                self._having.append(cond._set_query(self))
        if params:
            self._having.append(AND(**params)._set_query(self))
        return self

    def order_by(self, *args: Union[Field], **kwargs) -> 'Query':
        """Сортировка для sql запроса.
        
        Args:
            args: Параметры сортировки. `Field('company', 'name').desc()`
            params: Параметры сортировки. `age=Ordering.DESC`

        Returns:
            Query: Экземпляр запроса.
        """
        for arg in args:
            if issubclass(type(arg), ListOperators):
                self._order_by.append(arg._set_query(self))
        if kwargs:
            for field, order in kwargs.items():
                order_fn = getattr(Field(self._table_name, field)._set_query(self), order)
                self._order_by.append(order_fn())
        return self

    def limit(self, value: int) -> 'Query':
        """Ограничение записей в sql запросе.

        Args:
            value (int): Количество записей.
        
        Returns:
            Query: Экземпляр запроса.
        """
        self._limit = f' limit {value} '
        return self
    
    def offset(self, value: int) -> 'Query':
        """Смещение.

        Args:
            value (int): Смещение по записям.
        
        Returns:
            Query: Экземпляр запроса.
        """
        self._offset = f' offset {value} '
        return self
    
    def get(self):
        """Запрос на получение записей.
        
        Raises:
            DublicatTableNameQuery: Ошибка псевдонима JOIN таблиц.
        """
        return self._get()
    
    def _get(self) -> str:
        """Запрос на получение записей.
        
        Raises:
            DublicatTableNameQuery: Ошибка псевдонима JOIN таблиц.

        Returns:
            str: SQL запрос.
        """
        self._params = {}
        self._check_dublicate_join()
        join = self._build_join()
        self._check_cross_table_name()
        select = self._build_select()
        where = self._build_filter()
        group_by = self._build_groupby()
        having = self._build_having()
        orderby = self._build_orderby()
        params = self._collect_join_params()
        self._params.update(params)
        return (
            f"{select}"
            f" from {self._table_name}"
            f" {join}"
            f" {where}"
            f" {group_by}"
            f" {having}"
            f" {orderby}"
            f" {self._limit}"
            f' {self._offset}'
        ).strip()
    
    def update(self, **params):
        """Запрос на обновление записей по фильтру.
        
        Args:
            params: Параметры для обновления.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.
        """
        return self._update(**params)

    def _update(self, **params) -> str:
        """Запрос на обновление записей по фильтру.
        
        Args:
            params: Параметры которые будут обновляться.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """
        self._params = {}
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('update')
        fields = []
        set_fields = ''
        for field, value in params.items():
            self._exist_field(field)
            val = self._get_placeholder_value(field, '=', value)
            fields.append(f'{field} = {val}')
        if fields:
            set_fields = ', '.join(fields)
        where = self._build_filter()
        return (
            f" update {self._table_name} set "
            f"{set_fields}"
            f"{where}"
        ).strip()
    
    def insert(self, records: List[Dict]):
        """Вставка записи.
        
        Args:
            params: Параметры для вставки.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.
        """
        return self._insert(records)

    def _insert(self, records: List[Dict]) -> str:
        """Вставка записи.
        
        Args:
            params: Строка для вставки.
            
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """
        self._params = {}
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('insert')
        fields = list(records[0].keys())
        self._exist_fields(fields)
        into_values = []
        for i, record in enumerate(records):
            values = []
            for field in fields:
                if record[field] is None:
                    continue
                val = self._get_placeholder_value(field, '', record[field])
                values.append(val)
            into_values.append('({})'.format(', '.join(values)))
        sql_fields = '({})'.format(', '.join(fields))
        sql_values = ' values {}'.format(', '.join(into_values))
        return (
            f" insert into {self._table_name} "
            f'{sql_fields}'
            f'{sql_values}'
        ).strip()

    def delete(self) -> str:
        """Запрос на удаление записей.
        
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """ 
        return self._delete()
        
    def _delete(self) -> str:
        """Запрос на удаление записей.
        
        Raise:
            ErrorExecuteJoinQuery: Запретить выполнять с join таблицами.

        Returns:
            str: SQL запрос.
        """
        self._params = {}
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('delete')
        where = self._build_filter()
        return (
            f" delete from {self._table_name} "
            f"{where}"
        ).strip()
    
    def _build_join(self) -> str:
        """Собирает join sql. 

        Returns:
            str: join sql.
        """
        join = ''
        for table in self._joined_tables:
            table_alias = table._table_alias or table._table_name
            join += (
                f" {table._join_method} ({table._get()}) as {table_alias} "
                f"on {table_alias}.{table._join_field} = {table._ext_table}.{table._ext_field}"
            )
        return join
    
    def _build_join_map_select(self) -> List[str]:
        """ Собирает select карту для внешней таблице. """
        map_select = []
        for table in self._joined_tables:
            table_alias = table._table_alias or table._table_name
            map_table = table._build_join_map_select()
            for table_field in [*table._map_select, *map_table]:
                _, field = table_field.split('.')
                map_field = f"{table_alias}.{field}"
                if map_field not in map_select:
                    map_select.append(map_field)
        return map_select
    
    def _build_select(self) -> str:
        """ Собирает select по пользовательский функциям и полям.
        
        Returns:
            str: sql строка.
        """        
        select = []
        map_select = []
        if not self._user_fields and not self._map_select:
            return 'select * '
        self._map_select.clear()
        for arg in self._user_fields:
            field, table_name, val = '', '', ''
            if isinstance(arg, Field):
                table_name = arg._table
                field = arg._field_name
                arg._check_field()
                select.append(f'{table_name}.{field}')
                map_select.append(f'{table_name}.{field}')
            elif issubclass(type(arg), Functions):
                field = arg._as_name
                val = arg._get()
                select.append(f'{val} as {field}')
                map_select.append(f'{self._table_name}.{field}')
        join_map = self._build_join_map_select()
        map_select.extend(join_map)
        if select:
            res = 'select {}'.format(', '.join([*select, *join_map]))
            self._map_select.extend(map_select)
        else:
            self._map_select = [
                f'{self._table_name}.{field}' 
                for field in self._fields
            ]
            self._map_select.extend([*join_map])
            res = 'select {}'.format(', '.join(self._map_select))
        return res
    
    def _build_filter(self) -> str:
        """Сборка фильтра where.

        Returns:
            str: sql строка.
        """
        vals = [
            item._get()
            for item in self._where
        ]
        return 'where {}'.format(' and '.join(vals)) if vals else ''
    
    def _build_groupby(self) -> str:
        """Сборка группировки.

        Returns:
            str: sql строка.
        """
        vals = [
            item._get()
            for item in self._group_by
        ]
        return 'group by {}'.format(', '.join(vals)) if vals else ''
    
    def _build_having(self) -> str:
        """Сборка фильтра having.

        Returns:
            str: sql строка.
        """
        vals = [
            item._get()
            for item in self._having
        ]
        return 'having {}'.format(' and '.join(vals)) if vals else ''
    
    def _build_orderby(self) -> str:
        """Сборка сортировки.

        Returns:
            str: sql строка.
        """
        vals = [
            item._get()
            for item in self._order_by
        ]
        return 'order by {}'.format(', '.join(vals)) if vals else ''
    
    def _collect_join_params(self) -> Dict[str, Any]:
        """ Собирает все параметры для внешней таблице. """
        params = {}
        for table in self._joined_tables:
            param = table._collect_join_params()
            params.update(param)
            params.update(table._params)
        return params
    
    def _get_filter(self, relation: str = 'and', **params) -> str:
        """Часть запроса для условия.

        Args:
            relation (str, optional): Связь параметров.

        Returns:
            str: Параметры и часть строки условия.
        """        
        where = []
        for field_op, value in params.items():
            field, operator = self._get_operator_by_field(field_op)
            self._exist_field(field)
            table_alias = self._table_alias or self._table_name
            table_field = f'{table_alias}_{field}'
            val = self._get_placeholder_value(table_field, operator, value)
            where.append(f'{self._table_name}.{field} {operator} {val}')
        return '({})'.format(f' {relation} '.join(where))
    
    def _check_dublicate_join(self):
        """Проверка на дубликат названия без псевдонима.

        Raises:
            DublicatTableNameQuery: Дубль названий таблиц без псевдонима.
        """        
        for table1 in self._joined_tables:
            if self._table_name == table1._table_name:
                if not self.table_alias and not table1.table_alias:
                    # название таблиц не должны совпадать
                    raise DublicatTableNameQuery(table1._table_name)
    
    def _exist_fields(self, fields: List, exception: bool = True) -> bool:
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
    
    def _check_cross_table_name(self):
        """Проверка на пересечение названий таблиц.

        Raises:
            DublicatTableNameQuery: Ошибка дублей.
        """        
        for i, table1 in enumerate(self._joined_tables):
            for j, table2 in enumerate(self._joined_tables):
                if i==j:
                    continue
                if self._table_name != table2._table_name:
                    continue
                if not table1.table_alias and not table2.table_alias:
                    # название таблиц не должны совпадать
                    raise DublicatTableNameQuery(table1._table_name)
    
    def _check_field(self, table: str, field: str, exc: bool = True) -> bool:
        """Проверка. Есть ли данное поле в таблицах.

        Args:
            table (str): Таблица.
            field (str): Поле.
            exc (bool, optional): Выбрасывать ли исключение. Defaults to True.

        Raises:
            NotFieldQueryTable: Нет поля в таблице.

        Returns:
            Union[bool]: Проверка есть ли поле в таблице.
        """
        table_alias = self._table_alias or self._table_name
        if table == table_alias:
            return self._exist_field(field, exc)
        for tbl in self._joined_tables:
            table_alias = tbl._table_alias or tbl._table_name
            if table_alias == table and tbl._exist_field(field, exc):
                return True
    
    def _gen_name_variable(self) -> str:
        """Генерация названия ключа для переменной.

        Returns:
            str: Название ключа.
        """        
        count = len(self.params)
        tbl = self._table_alias or self._table_name
        return self.PLACEHOLDER_VARIABLE.format(tbl, count)
    
    @classmethod
    def _get_operator_by_field(cls, field_op: str) -> Tuple[str, str]:
        """Получение оператора из названия поля.

        Args:
            field (str): Поле.
            
        Raises:
            NotExistOperatorFilter: Нет такого оператора.

        Returns:
            Tuple[str, str]: Название поля и оператор
        """        
        field_operator = field_op.split('__')
        if len(field_operator) >= 2:
            field = field_operator[0]
            operator = field_operator[-1]
            if cls.OPERATORS.get(operator):
                return field, cls.OPERATORS.get(operator)
            else:
                raise NotExistOperatorFilter(operator)
        return field_op, '='
    
    def _get_placeholder_value(self, table_field: str, operator: str, value: Any) -> str:
        """Устанавливает плейсхолдеры и параметры для запроса.

        Args:
            table_field (str): Название поля.
            operator (str): Оператор.
            value (Any): Значения.

        Returns:
            str: Параметры и плейсхолдер на запрос.
        """
        start_num = len(self.params) + 1
        if isinstance(value, (int, float, str, bool, datetime)):
            field = f'{table_field}_{start_num}'
            val = self.PLACEHOLDER.format(field)
            self._params.update({ field: value })
            return val
        elif isinstance(value, (list, tuple)):
            if operator.find('between') != -1 and len(value) == 2:
                field1 = f'{table_field}_{start_num}'
                start_num += 1
                field2 = f'{table_field}_{start_num}'
                self._params.update(
                        {
                            field1: value[0],
                            field2: value[1]
                        }
                    )
                val0 = self.PLACEHOLDER.format(field1)
                val1 = self.PLACEHOLDER.format(field2)
                return f'{val0} and {val1}'
            else:
                in_elements = []
                for item in value:
                    field = f'{table_field}_{start_num}'
                    start_num += 1
                    self._params.update({ field: item })
                    val = self.PLACEHOLDER.format(field)
                    in_elements.append(val)
                val = "({})".format(','.join(in_elements))
                return val
        return ''