from datetime import datetime
from typing import Any, List, Literal, Union, TypeVar
from query_tables.query.base_query import BaseQuery, BaseField, BaseFunctions


PLACEHOLDER = '%({})s'
PLACEHOLDER_PATTERN = r'%\((\w+)\)s'
PLACEHOLDER_VARIABLE = '%({}_var_{})s'


class Operators:
    ILIKE = 'ilike'
    NOTILIKE = 'not ilike'
    LIKE = 'like'
    NOTLIKE = 'not like'
    IN = 'in'
    NOTIN = 'not in'
    GT = '>'
    GTE = '>='
    LT = '<'
    LTE = '<='
    EQU = '='
    NOTEQU = '!='
    BETWEEN = 'between'
    NOTBETWEEN = 'not between'
    ISNULL = 'is null'
    ISNOTNULL = 'is not null'
    IREGEX = '~*'
    NOTIREGEX = '!~*'
    REGEX = '~'
    NOTREGEX = '!~'
    ASC = 'asc'
    DESC = 'desc'


T = TypeVar('T', bound='ListOperators')


class ListOperators(object):
    
    def __init__(self, field: str):
        self._field = field
        self._operator = ''
        self._value: Any = None
        self._placeholder_value = ''
        self._query = None
    
    def _set_query(self, query: BaseQuery):
        """Устанавливает запрос.

        Args:
            query (BaseQuery): Экземпляр запроса.
        """        
        self._query = query
        return self
    
    def _install_placeholder(self):
        """ Устанавливает плейсхолдеры и параметры для запроса. """
        start_num = len(self._query.params) + 1
        alias = self._query._table_alias or self._query._table_name
        if isinstance(self._value, (int, float, str, bool, datetime)):
            field = f'{alias}_{self._field}_{start_num}'
            self._query._params.update({ field: self._value })
            self._placeholder_value = PLACEHOLDER.format(field)
        elif isinstance(self._value, (list, tuple)):
            if self._operator.find('between') != -1 and len(self._value) == 2:
                field1 = f'{alias}_{self._field}_{start_num}'
                start_num += 1
                field2 = f'{alias}_{self._field}_{start_num}'
                self._query._params.update(
                    {
                        field1: self._value[0],
                        field2: self._value[1]
                    }
                )
                val0 = PLACEHOLDER.format(field1)
                val1 = PLACEHOLDER.format(field2)
                self._placeholder_value = f'{val0} and {val1}'
            else:
                in_elements = []
                for item in self._value:
                    field = f'{alias}_{self._field}_{start_num}'
                    start_num += 1
                    self._query._params.update({ field: item })
                    val = PLACEHOLDER.format(field)
                    in_elements.append(val)
                self._placeholder_value = "({})".format(','.join(in_elements))
    
    def ilike(self: T, value: str) -> T:
        """ Поиск без учета регистра. """
        self._operator = Operators.ILIKE
        self._value = value
        return self
    
    def not_ilike(self: T, value: str) -> T:
        """ Не входит в поиск без учета регистра. """
        self._operator = Operators.NOTILIKE
        self._value = value
        return self
    
    def like(self: T, value: str) -> T:
        """ Поиск с учетом регистра. """
        self._operator = Operators.LIKE
        self._value = value
        return self
    
    def not_like(self: T, value: str) -> T:
        """ Не входит в поиск с учетом регистра. """
        self._operator = Operators.NOTLIKE
        self._value = value
        return self
        
    def in_(self: T, value: List[Any]) -> T:
        """ Вхождение. """
        self._operator = Operators.IN
        self._value = value
        return self
    
    def not_in(self: T, value: List[Any]) -> T:
        """ Отсутствие вхождения. """
        self._operator = Operators.NOTIN
        self._value = value
        return self
    
    def gt(self: T, value: Any) -> T:
        """ Больше. """
        self._operator = Operators.GT
        self._value = value
        return self
    
    def gte(self: T, value: Any) -> T:
        """ Больше и равно. """
        self._operator = Operators.GTE
        self._value = value
        return self
    
    def lt(self: T, value: Any) -> T:
        """ Меньше. """
        self._operator = Operators.LT
        self._value = value
        return self
    
    def lte(self: T, value: Any) -> T:
        """ Меньше и равно. """
        self._operator = Operators.LTE
        self._value = value
        return self
    
    def equ(self: T, value: Any) -> T:
        """ Равно. """
        self._operator = Operators.EQU
        self._value = value
        return self
    
    def not_equ(self: T, value: Any) -> T:
        """ Неравно. """
        self._operator = Operators.NOTEQU
        self._value = value
        return self
    
    def between(self: T, value: List[Any]) -> T:
        """ Между значениями. """
        self._operator = Operators.BETWEEN
        self._value = value
        return self
    
    def not_between(self: T, value: List[Any]) -> T:
        """ Не входит между значенями. """
        self._operator = Operators.NOTBETWEEN
        self._value = value
        return self
    
    def is_null(self: T) -> T:
        """ Должно быть NULL. """
        self._operator = Operators.ISNULL
        return self
    
    def is_not_null(self: T) -> T:
        """ Не дожно быть NULL. """
        self._operator = Operators.ISNOTNULL
        return self
    
    def iregex(self: T, value: str) -> T:
        """ Поиск по регулярке без учета регистра. """
        self._operator = Operators.IREGEX
        self._value = value
        return self
    
    def not_iregex(self: T, value: str) -> T:
        """ Не входит в поиск по регулярке без учета регистра. """
        self._operator = Operators.NOTIREGEX
        self._value = value
        return self
    
    def regex(self: T, value: str) -> T:
        """ Поиск по регулярке с учета регистра. """
        self._operator = Operators.REGEX
        self._value = value
        return self
    
    def not_regex(self: T, value: str) -> T:
        """ Не входит в поиск по регулярке с учета регистра. """
        self._operator = Operators.NOTREGEX
        self._value = value
        return self
    
    def asc(self: T) -> T:
        """ По увеличению. """
        self._operator = Operators.ASC
        return self
    
    def desc(self: T) -> T:
        """ По уменьшению. """
        self._operator = Operators.DESC
        return self


class Field(ListOperators, BaseField):
    """ Поле для фильтрации или выборки. """
    def __init__(self, table: str, field_name: str):
        super().__init__(field_name)
        self._table = table
        self._field_name = field_name
        self._query = None
    
    def _get(self) -> str:
        self._check_field()
        self._install_placeholder()
        field_value = ' '.join([
                f'{self._table}.{self._field_name}', 
                self._operator, 
                self._placeholder_value
            ])
        return field_value.strip()
    
    def _check_field(self, exc: bool = True) -> bool:
        """Существует ли такое поле в таблице.

        Args:
            exc (bool, optional): Исключение если поле не существует.

        Returns:
            bool: Результат.
        """
        return self._query._check_field(self._table, self._field_name, exc)


class Functions(ListOperators, BaseFunctions):
    
    def __init__(self, fn_field: str = ''):
        alias = self.__class__.__name__.lower()
        super().__init__(alias)
        self._fn_field = fn_field
        self._as_name = ''
    
    def _get(self) -> str:
        self._install_placeholder()
        field_value = ' '.join([
                self._fn_field, 
                self._operator, 
                self._placeholder_value
            ])
        return field_value.strip()
    
    def _get_key_params(self, value: Union['Field', Any]) -> str:
        """Возвращает строку ключ для вставки в sql.

        Args:
            value (Union[Field, Any]): Значение.

        Returns:
            str: Ключ.
        """        
        if isinstance(value, Field):
            self._query._check_field(value._table, value._field_name, True)
            return f'{value._table}.{value._field_name}'
        else:
            name = self._query._gen_name_variable()
            key_name = name[2:-2]
        self._query._params.update({ key_name: value })
        return name
    
    def as_(self, name: str) -> 'Functions':
        self._as_name = name
        return self


class Count(Functions):
    """ Подсчет количества строк. """
    def __init__(self, field: Field):
        super().__init__()
        self.field = field
    
    def _get(self) -> str:
        self._fn_field = 'count({})'.format(self._get_key_params(self.field))
        return super()._get()


class Sum(Functions):
    """ Сумма значений.  """
    def __init__(self, field: Field):
        super().__init__()
        self.field = field
    
    def _get(self) -> str:
        self._fn_field = 'sum({})'.format(self._get_key_params(self.field))
        return super()._get()


class Avg(Functions):
    """ Среднее значение. """
    def __init__(self, field: Field):
        super().__init__()
        self.field = field
    
    def _get(self) -> str:
        self._fn_field = 'avg({})'.format(self._get_key_params(self.field))
        return super()._get()


class Min(Functions):
    """ Минимальное значение. """
    def __init__(self, field: Field):
        super().__init__()
        self.field = field
    
    def _get(self) -> str:
        self._fn_field = 'min({})'.format(self._get_key_params(self.field))
        return super()._get()


class Max(Functions):
    """ Максимальное значение. """
    def __init__(self, field: Field):
        super().__init__()
        self.field = field
    
    def _get(self) -> str:
        self._fn_field = 'max({})'.format(self._get_key_params(self.field))
        return super()._get()


class Concat(Functions):
    """ Конкатенация. """
    def __init__(self, *fields_values: Union[Field, str]):
        super().__init__()
        self.fields_values = fields_values
    
    def _get(self) -> str:
        concats = [
            self._get_key_params(field_val)
            for field_val in self.fields_values
        ]
        self._fn_field = 'concat({})'.format(', '.join(concats))
        return super()._get()


class Upper(Functions):
    """ Верхний регистр. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self._fn_field = 'upper({})'.format(self._get_key_params(self.field_value))
        return super()._get()


class Lower(Functions):
    """ Нижний регистр. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self._fn_field = 'lower({})'.format(self._get_key_params(self.field_value))
        return super()._get()


class Length(Functions):
    """ Длина строки. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self._fn_field = 'length({})'.format(self._get_key_params(self.field_value))
        return super()._get()


class Trim(Functions):
    """ Обрезка пробелов. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self._fn_field = 'trim({})'.format(self._get_key_params(self.field_value))
        return super()._get()


class Substring(Functions):
    """ Извлечение подстроки. """
    def __init__(self, field_value: Union[Field, str], index: int, count: int):
        super().__init__()
        self.field_value = field_value
        self.index = int(index)
        self.count = int(count)
    
    def _get(self) -> str:
        name = self._get_key_params(self.field_value)
        self._fn_field = f'substring({name}, {self.index}, {self.count})'
        return super()._get()


class Replace(Functions):
    """ Замена текста. """
    def __init__(
            self, 
            field_value: Union[Field, str], 
            old_word: Union[Field, str], 
            new_word: Union[Field, str]
        ):
        super().__init__()
        self.field_value = field_value
        self.old_word = old_word
        self.new_word = new_word
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self.old_word = self._get_key_params(self.old_word)
        self.new_word = self._get_key_params(self.new_word)
        self._fn_field = f'replace({self.field_value}, {self.old_word}, {self.new_word})'
        return super()._get()


class Position(Functions):
    """ Поиск позиции. """
    def __init__(self, substring: Union[Field, str], string: Union[Field, str]):
        super().__init__()
        self.substring = substring
        self.string = string
    
    def _get(self) -> str:
        self.substring = self._get_key_params(self.substring)
        self.string = self._get_key_params(self.string)
        self._fn_field = f'position({self.substring} in {self.string})'
        return super()._get()


class Round(Functions):
    """Округление. """
    def __init__(self, field_value: Union[Field, str], num: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
        self.num = num
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self.num = self._get_key_params(self.num)
        self._fn_field = f'round({self.field_value}, {self.num})'
        return super()._get()


class Ceil(Functions):
    """Округление. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f'ceil({self.field_value})'
        return super()._get()


class Floor(Functions):
    """Округление. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f'floor({self.field_value})'
        return super()._get()


class Abs(Functions):
    """Абсолютное значение. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f'abs({self.field_value})'
        return super()._get()


class Mod(Functions):
    """Остаток от деления. """
    def __init__(self, num1: Union[Field, str], num2: Union[Field, str]):
        super().__init__()
        self.num1 = num1
        self.num2 = num2
    
    def _get(self) -> str:
        self.num1 = self._get_key_params(self.num1)
        self.num2 = self._get_key_params(self.num2)
        self._fn_field = f'mod({self.num1}, {self.num2})'
        return super()._get()


class Power(Functions):
    """Степень. """
    def __init__(self, num1: Union[Field, str], num2: Union[Field, str]):
        super().__init__()
        self.num1 = num1
        self.num2 = num2
    
    def _get(self) -> str:
        self.num1 = self._get_key_params(self.num1)
        self.num2 = self._get_key_params(self.num2)
        self._fn_field = f'power({self.num1}, {self.num2})'
        return super()._get()


class Sqrt(Functions):
    """ Корень. """
    def __init__(self, field_value: Union[Field, str]):
        super().__init__()
        self.field_value = field_value
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f'sqrt({self.field_value})'
        return super()._get()


class Random(Functions):
    """ Случайное число. """
    
    def __init__(self):
        super().__init__()
    
    def _get(self) -> str:
        self._fn_field = 'random()'
        return super()._get()


class NowDatetime(Functions):
    """ Текущее дата время. """
    
    def __init__(self):
        super().__init__()
    
    def _get(self) -> str:
        self._fn_field = 'now()'
        return super()._get()


class NowDate(Functions):
    """ Текущее дата. """
    
    def __init__(self):
        super().__init__()
    
    def _get(self) -> str:
        self._fn_field = 'current_date'
        return super()._get()


class NowTime(Functions):
    """ Текущее время. """
    
    def __init__(self):
        super().__init__()
    
    def _get(self) -> str:
        self._fn_field = 'current_time'
        return super()._get()


class NowTimestamp(Functions):
    """ Текущее время. """
    
    def __init__(self):
        super().__init__()
    
    def _get(self) -> str:
        self._fn_field = 'current_timestamp'
        return super()._get()


class Extract(Functions):
    """ Извлечение компонентов. """
    def __init__(
            self, field_value: Union[Field, str], 
            part: Literal['year', 'month', 'day']
        ):
        super().__init__()
        self.field_value = field_value
        if part not in ['year', 'month', 'day']:
            part = 'day'
        self.part = part
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f'extract({self.part} from {self.field_value})'
        return super()._get()


class Char(Functions):
    """ Форматирование даты. """
    def __init__(self, date: Union[Field, Any], pattern: str = 'DD-MM-YYYY HH24:MI:SS'):
        super().__init__()
        self.pattern = pattern
        self.date = date
    
    def _get(self) -> str:
        self.date = self._get_key_params(self.date)
        self.pattern = self._get_key_params(self.pattern)
        self._fn_field = f'to_char({self.date}, {self.pattern})'
        return super()._get()


class Age(Functions):
    """ Разность дат. """
    def __init__(self, field_value1: Union[Field, str], field_value2: Union[Field, str]):
        super().__init__()
        self.field_value1 = field_value1
        self.field_value2 = field_value2
    
    def _get(self) -> str:
        self.field_value1 = self._get_key_params(self.field_value1)
        self.field_value2 = self._get_key_params(self.field_value2)
        self._fn_field = f'age({self.field_value1}, {self.field_value2})'
        return super()._get()


class Interval(Functions):
    """ Добавление интервала. """
    def __init__(
            self, field_value: Union[Field, Any], count: int, 
            type_interval: Literal['year', 'month', 'week', 'day', 'hour', 'minute'] = 'day', 
            op: Literal['+', '-'] = '+'
        ):
        super().__init__()
        self.field_value = field_value
        self.count = int(count)
        if type_interval not in ['year', 'month', 'week', 'day', 'hour', 'minute']:
            type_interval = 'day'
        self.type_interval = type_interval
        if op not in ['+', '-']:
            op = '+'
        self.op = op
    
    def _get(self) -> str:
        self.field_value = self._get_key_params(self.field_value)
        self._fn_field = f"({self.field_value} {self.op} interval '{self.count} {self.type_interval}')"
        return super()._get()


class Case(Functions):
    """ Простое условие. """
    def __init__(self):
        super().__init__()
        self._when = []
        self._when_val = []
        self._op = []
        self._then = []
        self._els = []
    
    def when(self, field_value: Union[Field, str]) -> 'Case':
        self._when.append(field_value)
        return self
    
    def then(self, field_value: Union[Field, str]) -> 'Case':
        self._op.append(self._operator)
        self._when_val.append(self._value)
        self._then.append(field_value)
        return self
    
    def elseif(self, field_value: Union[Field, str]) -> 'Case':
        self._els.append(field_value)
        return self
    
    def _get(self) -> str:
        sql = 'case '
        when = []
        el = ' else {} end'
        for whenthen in zip(self._when, self._op, self._when_val, self._then):
            val1 = self._get_key_params(whenthen[0])
            val2 = self._get_key_params(whenthen[2])
            val3 = self._get_key_params(whenthen[3])
            when.append('when {} {} {} then {}'.format(val1, whenthen[1], val2, val3))
        val_el = self._get_key_params(self._els[0])
        el = el.format(val_el)
        sql += ' '.join(when)
        sql += el
        return sql


class Coalesce(Functions):
    """ возвращает первое не NULL значение. """
    def __init__(self, *field_values: Union[Field, str], default: Union[Field, str]):
        super().__init__()
        self.default = default
        self.field_values = field_values
    
    def _get(self) -> str:
        coalesce = [
            self._get_key_params(field_val)
            for field_val in self.field_values
        ]
        self.default = self._get_key_params(self.default)
        self._fn_field = "coalesce({}, {})".format(', '.join(coalesce), self.default)
        return super()._get()