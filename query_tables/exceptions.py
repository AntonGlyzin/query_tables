from query_tables.translate import _


class ExceptionTable(Exception):
    
    def __str__(self):
        return f"[{self.__class__.__name__}] {self.args[0]}"
    
    def __repr__(self):
        return (f"{self.__class__.__name__}(message={self.args[0]!r})")


class NotTable(ExceptionTable):
    """
        Попытка обратиться к несуществующей таблице.
    """
    def __init__(self, table_name: str):
        message = _("Таблица '{}' не найдена.").format(table_name)
        super().__init__(message)


class ExceptionQueryTable(ExceptionTable):
    """
        Ошибка в экземпляре QueryTable.
    """
    def __init__(self, table_name: str, message: str = ''):
        message = _("Ошибка в экземпляре QueryTable для таблице '{}' : {}").format(table_name, message)
        super().__init__(message)


class NotFieldQueryTable(ExceptionTable):
    """
        Попытка обратиться к несуществующему полю таблицы.
    """
    def __init__(self, table_name: str, field_name: str):
        message = _("В таблице '{}' не найдено поле '{}'.").format(table_name, field_name)
        super().__init__(message)


class ErrorConvertDataQuery(ExceptionTable):
    """
        Ошибка при конвертации значений.
    """
    def __init__(self, value: str):
        message = _("Ошибка при конвертации значения '{}'.").format(value)
        super().__init__(message)


class NotQuery(ExceptionTable):
    """
        Ошибка запроса.
    """    
    def __init__(self):
        message = _("Ошибка в получение данных из кеша. SQL запрос не был установлен.")
        super().__init__(message)


class NoMatchFieldInCache(ExceptionTable):
    """
        Ошибка полей.
    """    
    def __init__(self):
        message = _("Попытка обращения к несуществующим полям в кеше.")
        super().__init__(message)


class ErrorExecuteJoinQuery(ExceptionTable):
    """
        Ошибка изменение таблицы с JOIN.
    """    
    def __init__(self, method):
        message = _("Ошибка SQL в методе '{}'. Нельзя изменять таблицу c JOIN таблицами.").format(method)
        super().__init__(message)


class ErrorDeleteCacheJoin(ExceptionTable):
    """
        Ошибка очишения кеша по таблице JOIN.
    """    
    def __init__(self, table):
        message = _("Ошибка очишения кеша по таблице '{}'. Нельзя очишать кеш таблицы при JOIN запросах.").format(table)
        super().__init__(message)


class DesabledCache(ExceptionTable):
    """
        Доступ до кеша не возможен.
    """  
    def __init__(self):
        message = _("Доступ до кеша не возможен. Кеш отключен.")
        super().__init__(message)


class ErrorLoadingStructTables(ExceptionTable):
    """
        Ошибка при загрузки структуры таблиц.
    """  
    def __init__(self, error):
        message = _("Ошибка при загрузки структуры таблиц: {}").format(error)
        super().__init__(message)


class ErrorConnectDB(ExceptionTable):
    """
        Ошибка соединения с базой данных.
    """  
    def __init__(self, error):
        message = _("Ошибка соединения с базой данных: {}").format(error)
        super().__init__(message)


class ErrorExecuteQueryDB(ExceptionTable):
    """
        Ошибка при выполнение запроса.
    """  
    def __init__(self, error):
        message = _("Ошибка при выполнение запроса. {}").format(error)
        super().__init__(message)
        
        
class ErrorGetOrSaveStructTable(ExceptionTable):
    """
        Ошибка получения или сохранения структуры таблиц.
    """  
    def __init__(self, type_cahe):
        message = _("Для кеша с типом '{}' невозможно сохранять или загружать структуру таблиц.").format(type_cahe)
        super().__init__(message)


class NotExistOperatorFilter(ExceptionTable):
    """
        Отсутствие реализации для оператора.
    """  
    def __init__(self, operator):
        message = _("Для такого оператора '{}' нет реализации.").format(operator)
        super().__init__(message)


class DublicatTableNameQuery(ExceptionTable):
    """
        Дубликат названия таблицы в запросе.
    """  
    def __init__(self, table_name):
        message = _("Ошибка псевдонима у JOIN таблицы. Название таблицы '{}' повторяется без псевдонима.").format(table_name)
        super().__init__(message)