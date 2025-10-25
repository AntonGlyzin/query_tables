from datetime import datetime
from typing import Union, Any, List, Optional, Dict, Tuple
from query_tables.query.base_query import BaseQuery, BaseJoin
from query_tables.query.join_table import CommonJoin
from query_tables.query.condition import AND, Condition
from query_tables.exceptions import (
    NotFieldQueryTable, 
    ErrorConvertDataQuery,
    ErrorExecuteJoinQuery,
    DublicatTableNameQuery,
    NotExistOperatorFilter
)


class Query(BaseQuery):
    """
        Отвечает за сборку sql запросов.
    """
    PLACEHOLDER = '%({})s'
    PLACEHOLDER_PATTERN = r'%\((\w+)\)s'
    
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
        self._fields = fields # Все поля в формате <поле> из текущей таблицы.
        self._user_fields = [] # Пользовательские поля в формате <поле> текущей таблицы.
        # Формат поля <таблица>.<поле> 
        self._map_select = [
            f'{self._table_name}.{field}' 
            for field in self._fields
        ]
        self._join = ''
        self._joined_tables: List['Query'] = []
        self._where = ''
        self._group_by = ''
        self._having = ''
        self._order_by = ''
        self._limit = ''
        self._offset = ''
        self._params: Dict[str, Any] = {}
        # если текущая таблица соединяется с внешней
        self._join_field = ''
        self._ext_field = ''
        self._ext_table = ''
        self._table_alias = ''
        self._join_method = ''
    
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
        if self._joined_tables:
            return True
        return False
    
    def select(self, fields: Optional[List[str]] = None) -> 'Query':
        """Устанавливает поля для выборки.

        Args:
            fields (List[str]): Поля из БД.

        Returns:
            Query: Экземпляр запроса.
        """
        if not fields:
            self._map_select.clear()
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

    def join(self, table: Union[BaseJoin, 'Query']) -> 'Query':
        """Присоединение таблиц через join оператор sql. 

        Args:
            table (BaseJoin): Таблица которая присоединяется.

        Returns:
            Query: Экземпляр запроса.
        """
        if issubclass(type(table), CommonJoin):
            table = table.join_table
        self._exist_field(table._ext_field)
        table._exist_field(table._join_field)
        table._ext_table = self._table_name
        self._params.update(table._params)
        table._params.clear()
        self._joined_tables.append(table)
        self._joined_tables.extend(table._joined_tables)
        table._joined_tables.clear()
        return self

    def filter(self, *args, **params) -> 'Query':
        """Добавление фильтров в where блок запроса sql.
        
        Args:
            params: Параметры выборки.

        Returns:
            Query: Экземпляр запроса.
        """
        if args and issubclass(type(args[0]), Condition):
            param, val = args[0]._set_query(self)._parse()
        else:
            param, val = AND(**params)._set_query(self)._parse()
        self._params.update(param)
        self._where = f' where {val}'
        return self
    
    def group_by(self, params: list[str]) -> 'Query':
        """Группировка записей по полю.

        Args:
            params (list[str]): Список строк.

        Returns:
            Query: Экземпляр запроса.
        """        
        groupby = []
        for field in params:
            self._exist_field(field)
            groupby.append(field)
        if groupby:
            self._group_by = ' group by '
            self._group_by += ', '.join(groupby)
        return self
    
    def having(self, *args, **params) -> 'Query':
        """Добавление фильтров в having блок запроса sql.
        
        Args:
            params: Параметры выборки.

        Returns:
            Query: Экземпляр запроса.
        """
        if args and issubclass(type(args[0]), Condition):
            param, val = args[0]._set_query(self)._parse()
        else:
            param, val = AND(**params)._set_query(self)._parse()
        self._params.update(param)
        self._having = f' having {val}'
        return self

    def order_by(self, **kwargs) -> 'Query':
        """Сортировка для sql запроса.

        Returns:
            Query: Экземпляр запроса.
        """
        order_by = [
            f'{self._table_name}.{field} {order}'
            for field, order in kwargs.items()
        ]
        if order_by:
            self._order_by = ' order by '
            self._order_by += ', '.join(order_by)
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
        self._check_dublicate_join()
        self._join = self._build_join()
        for i, table1 in enumerate(self._joined_tables):
            for j, table2 in enumerate(self._joined_tables):
                if i==j:
                    continue
                if self._table_name != table2._table_name:
                    continue
                if not table1.table_alias and not table2.table_alias:
                    # название таблиц не должны совпадать
                    raise DublicatTableNameQuery(table1._table_name)
        select = 'select ' + ', '.join(self._map_select)
        if not self._map_select:
            select = 'select * '
        return (
            f"{select}"
            f" from {self._table_name} "
            f"{self._join}"
            f"{self._where}"
            f"{self._group_by}"
            f"{self._having}"
            f"{self._order_by}"
            f"{self._limit}"
            f'{self._offset}'
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
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('update')
        fields = []
        set_fields = ''
        for field, value in params.items():
            self._exist_field(field)
            param, val = self._get_placeholder_value(field, '=', value)
            self._params.update(param)
            fields.append(f'{field} = {val}')
        if fields:
            set_fields = ', '.join(fields)
        return (
            f" update {self._table_name} set "
            f"{set_fields}"
            f"{self._where}"
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
                param, val = self._get_placeholder_value(f'{field}{i}', '', record[field])
                self._params.update(param)
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
        if self.is_table_joined:
            raise ErrorExecuteJoinQuery('delete')
        return (
            f" delete from {self._table_name} "
            f"{self._where}"
        ).strip()
    
    def _build_join(self) -> str:
        """Собирает join sql. 

        Returns:
            str: join sql.
        """
        join = ''
        for table in self._joined_tables:
            table_alias = table._table_alias or table._table_name
            for table_field in table._map_select:
                table_name, field = table_field.split('.')
                if table_name == table._table_name:
                    map_field = f"{table_alias}.{field}"
                else:
                    map_field = table_field
                if map_field not in self._map_select:
                    self._map_select.append(map_field)
            join += (
                f" {table._join_method} ({table._get()}) as {table_alias} "
                f"on {table_alias}.{table._join_field} = {table._ext_table}.{table._ext_field}"
            )
        return join
    
    def _get_filter(self, relation: str = 'and', **params) -> Tuple[Dict, str]:
        """Часть запроса для условия.

        Args:
            relation (str, optional): Связь параметров.

        Returns:
            Tuple[Dict, str]: Параметры и часть строки условия.
        """        
        where = []
        new_params = {}
        for field_op, value in params.items():
            field, operator = self._get_operator_by_field(field_op)
            self._exist_field(field)
            table_alias = self._table_alias or self._table_name
            table_field = f'{table_alias}_{field}'
            param, val = self._get_placeholder_value(table_field, operator, value)
            new_params.update(param)
            where.append(f'{self._table_name}.{field} {operator} {val}')
        return new_params, '({})'.format(f' {relation} '.join(where))
    
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
    
    def _exist_fields_identity(
        self, fields: List, 
        exclude_fields: Optional[List] = None, 
        exception: bool = True
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
    
    @classmethod
    def _get_placeholder_value(
            cls, table_field: str, operator: str, value: Any
        ) -> Tuple[Dict, str]:
        """Устанавливает плейсхолдеры и параметры для запроса.

        Args:
            table_field (str): Название поля.
            operator (str): Оператор.
            value (Any): Значения.

        Returns:
            Tuple[Dict, str]: Параметры и плейсхолдер на запрос.
        """
        params = {}
        if isinstance(value, (int, float, str, bool, datetime)):
            val = cls.PLACEHOLDER.format(table_field)
            params.update({ table_field: value })
            return params, val
        elif isinstance(value, (list, tuple)):
            if operator.find('between') != -1 and len(value) == 2:
                params.update(
                        {
                            f'{table_field}0': value[0],
                            f'{table_field}1': value[1]
                        }
                    )
                val0 = cls.PLACEHOLDER.format(f'{table_field}0')
                val1 = cls.PLACEHOLDER.format(f'{table_field}1')
                return params, f'{val0} and {val1}'
            else:
                in_elements = []
                for i, item in enumerate(value):
                    params.update({ f'{table_field}{i}': item })
                    val = cls.PLACEHOLDER.format(f'{table_field}{i}')
                    in_elements.append(val)
                val = "({})".format(','.join(in_elements))
                return params, val
        return params, ''

    @classmethod
    def _convert_simple_format_data(
        cls, value: Optional[Union[list, tuple, int, float, str, bool]] = None
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
                    cls._convert_simple_format_data(item) for item in value
                ])
            if len(value) > 2:
                value = list(value)
        if isinstance(value, list):
            value = [
                cls._convert_simple_format_data(item) for item in value
            ]
            return "({})".format(','.join(map(str, value)))
        elif isinstance(value, bool):
            ret_value = 'true' if value else 'false'
            return ret_value
        elif isinstance(value, (int, float)):
            return f'{value}'
        elif isinstance(value, str):
            new_value = value.replace("'", "''").replace('\\', '\\\\')
            return f"'{new_value}'"
        raise ErrorConvertDataQuery(value)