
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
        message = f"Таблица '{table_name}' не найдена."
        super().__init__(message)


class ExceptionQueryTable(ExceptionTable):
    """
        Ошибка в экземпляре QueryTable.
    """
    def __init__(self, table_name: str, message: str = ''):
        message = f"Ошибка в экземпляре QueryTable для таблице '{table_name}' : {message}"
        super().__init__(message)


class NotFieldQueryTable(ExceptionTable):
    """
        Попытка обратиться к несуществующему полю таблицы.
    """
    def __init__(self, table_name: str, field_name: str):
        message = f"В таблице '{table_name}' не найдено поле '{field_name}'."
        super().__init__(message)


class ErrorConvertDataQuery(ExceptionTable):
    """
        Ошибка при конвертации значений.
    """
    def __init__(self, value: str):
        message = f"Ошибка при конвертации значения '{value}'."
        super().__init__(message)


class NotQuery(ExceptionTable):
    """
        Ошибка запроса.
    """    
    def __init__(self):
        message = "Ошибка в получение данных из кеша. SQL запрос не был установлен."
        super().__init__(message)


class NoMatchFieldInCache(ExceptionTable):
    """
        Ошибка полей.
    """    
    def __init__(self):
        message = "Попытка обращения к несуществующим полям в кеше."
        super().__init__(message)


class ErrorExecuteJoinQuery(ExceptionTable):
    """
        Ошибка изменение таблицы с JOIN.
    """    
    def __init__(self, method):
        message = f"Ошибка SQL в методе '{method}'. Нельзя изменять таблицу c JOIN таблицами."
        super().__init__(message)


class ErrorAliasTableJoinQuery(ExceptionTable):
    """
        Ошибка псевдонима у JOIN таблиц.
    """    
    def __init__(self, table):
        message = f"Ошибка псевдонима у JOIN таблицы '{table}'. Таблица в запросе используется один раз. Псевдоним не нужен."
        super().__init__(message)


class ErrorDeleteCacheJoin(ExceptionTable):
    """
        Ошибка очишения кеша по таблице JOIN.
    """    
    def __init__(self, table):
        message = f"Ошибка очишения кеша по таблице '{table}'. Нельзя очишать кеш таблицы при JOIN запросах."
        super().__init__(message)


class DesabledCache(ExceptionTable):
    """
        Доступ до кеша не возможен.
    """  
    def __init__(self):
        message = "Доступ до кеша не возможен. Кеш отключен."
        super().__init__(message)


class ErrorLoadingStructTables(ExceptionTable):
    """
        Ошибка при загрузки структуры таблиц.
    """  
    def __init__(self, error):
        message = f"Ошибка при загрузки структуры таблиц: {error}"
        super().__init__(message)


class ErrorConnectDB(ExceptionTable):
    """
        Ошибка соединения с базой данных.
    """  
    def __init__(self, error):
        message = f"Ошибка соединения с базой данных: {error}"
        super().__init__(message)


class ErrorExecuteQueryDB(ExceptionTable):
    """
        Ошибка при выполнение запроса.
    """  
    def __init__(self, error):
        message = f"Ошибка при выполнение запроса. {error}"
        super().__init__(message)
        
        
class ErrorGetOrSaveStructTable(ExceptionTable):
    """
        Ошибка получения или сохранения структуры таблиц.
    """  
    def __init__(self, type_cahe):
        message = f"Для кеша с типом '{type_cahe}' невозможно сохранять или загружать структуру таблиц."
        super().__init__(message)