import hashlib
from cachetools import TTLCache, LRUCache
from typing import Union, List, Dict, Iterator, Optional, Tuple
from threading import RLock
from query_tables.exceptions import NotQuery, NoMatchFieldInCache
from query_tables.cache import BaseCache, TypeCache


class SyncLockDecorator:
    """
        Обертка для методов в многопоточном приложение.
    """    
    def __init__(self, method, rlock):
        self.method = method
        self.rlock = rlock

    def __call__(self, *args, **kwargs):
        with self.rlock:
            return self.method(*args, **kwargs)


class CacheQuery(BaseCache):
    """
        Синхронно-асинхронное кеширование данных в памяти процесса на основе запроса к БД.
    """
    
    type_cache = TypeCache.local
    
    def __init__(
        self, ttl: int = 0, 
        maxsize: int = 1024,
        use_async: bool = False,
        non_expired: bool = False
    ):
        """
        
        Args:
            ttl (int, optional): Время кеша запроса. По умолчанию 0 секунд - кеширование отключено.
            maxsize (int, optional): Размер кеша.
            use_async (bool, optional): Включить если ваш код асинхронный.
            non_expired (bool, optional): Если нужен кеш без истечения времени.
        """
        self._ttl = ttl
        self._maxsize = maxsize
        self._use_async = use_async
        self._non_expired = non_expired
        self._hashkey = '' # хэш от SQL запроса
        self._filter_params = {}
        self._tables = LRUCache(maxsize=maxsize) # в каких запросах участвует таблица
        self._cache = (
            LRUCache(maxsize=maxsize)
            if non_expired 
            else TTLCache(ttl=ttl, maxsize=maxsize) 
        )
        if use_async:
            return None
        self._rlock = RLock()
        lock_methods = [
            self.clear,
            self.delete_cache_table,
            self._getitem_,
            self._setitem_,
            self._delitem_,
            self.filter,
            self.get,
            self.insert,
            self.update,
            self.delete
        ]
        for method in lock_methods:
            setattr(
                self, method.__name__, 
                SyncLockDecorator(method, self._rlock)
            )
            
    def is_enabled_cache(self) -> bool:
        """
            Включен ли кеш.
        """        
        return self._non_expired or bool(self._ttl)

    def clear(self):
        """
            Очищение кеша.
        """
        if self.is_enabled_cache():
            self._cache.clear()
            self._tables.clear()

    def delete_cache_table(self, table: str) -> bool:
        """Удаление кеша по таблице. Вседу, где использовалась таблица.

        Args:
            table (str): Название таблицы.
        
        Returns:
            bool: Флаг успешности.
        """
        if not self._tables.get(table):
            return False
        # копируем список
        hashkeys = [*self._tables[table]]
        for hashkey in hashkeys:
            self._cache.pop(hashkey, None)
            self._delete_hashkey_in_tables(hashkey)
        return True
        
    def __getitem__(self, query: str) -> 'BaseCache':
        """Устанавливает контекст SQL запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            BaseCache: Кеш.
        """
        if not query:
            raise NotQuery()
        return self._getitem_(query)
    
    def _getitem_(self, query: str) -> 'BaseCache':
        self._hashkey = self._get_hashkey_query(query)
        return self
        
    def get(self) -> Union[List[Dict], List]:
        """Получение данных из кеша по условию или без условия.

        Returns:
            Union[List[Dict], List]: Записи или пустой список.
        """
        if not self._hashkey:
            raise NotQuery()
        if not any([bool(self._ttl), self._non_expired]):
            return []
        if self._hashkey in self._cache:
            if not self._filter_params:
                return self._cache[self._hashkey]
            else:
                data = list(self._filtered_data(self._hashkey, self._filter_params))
                self._filter_params.clear()
                return data
        self._delete_hashkey_in_tables(self._hashkey)
        return []

    def __setitem__(self, query: str, data: List[Dict]):
        """Сохранить в кеш данные.

        Args:
            query (str): SQL запрос.
            data (List[Dict]): Результирующие данные из БД.
        """
        return self._setitem_(query, data)

    def _setitem_(self, query: str, data: List[Dict]):
        if not any([bool(self._ttl), self._non_expired]):
            return None
        hashkey = self._get_hashkey_query(query)
        tables = self._get_tables_from_fields(data)
        self._save_hashkey_in_tables(tables, hashkey)
        self._cache[hashkey] = data

    def __delitem__(self, query: str):
        """Удаление из кеша данных.

        Args:
            query (str): SQL запрос.
        """  
        return self._delitem_(query)

    def _delitem_(self, query: str):
        hashkey = self._get_hashkey_query(query)
        self._cache.pop(hashkey, None)
        self._delete_hashkey_in_tables(hashkey)
        
    def filter(self, params: Dict) -> 'BaseCache':
        """Условие для выборки записей в кеше.
        Выборка учитывает точное совпадение значений.
        
        Args:
            Название полей для выборки. К примеру: `.filter({'person.id': 1, 'person.name': 'Anton'})`
                Название таблицы: person
                Название поля: id
                
        Raises:
            NotQuery: Запрос не установлен.
            NoMatchFieldInCache: Нет такого поля.

        Returns:
            BaseCache: Кеш.
        """ 
        if not self._hashkey:
            raise NotQuery()
        if not self._check_fields_in_cache(self._hashkey, list(params.keys())):
            raise NoMatchFieldInCache()
        self._filter_params.clear()
        self._filter_params.update(params)
        return self
    
    def insert(self, record: Dict) -> Optional[Dict]:
        """Добавление записи к кеш.

        Args:
            params (Dict): Запись.
            
        Raises:
            NotQuery: Запрос не установлен.
            NoMatchFieldInCache: Нет такого поля.
        """ 
        if not self._hashkey:
            raise NotQuery()
        if not self._check_fields_identity(self._hashkey, list(record.keys())):
            raise NoMatchFieldInCache()
        if self._hashkey not in self._cache:
            self._cache[self._hashkey] = [record]
        else:
            self._cache[self._hashkey].append(record)
        return record
        
    def update(self, params: Dict) -> Union[List[Dict], List]:
        """Обновление записей в кеше по условию.
        
        Args:
            params (Dict): Название полей для обновления. К примеру: `.filter({'person.id': 1}).update({'person.name': 'Anton'})`
                либо `.update(**params)`
                
        Raises:
            NotQuery: Запрос не установлен.
            NoMatchFieldInCache: Нет такого поля.

        Returns:
            Union[List[Dict], List]: Обновленные записи или пустой список.
        """ 
        if not self._hashkey:
            raise NotQuery()
        if not self._check_fields_in_cache(self._hashkey, list(params.keys())):
            raise NoMatchFieldInCache()
        updateted_records = []
        if self._hashkey not in self._cache:
            return updateted_records
        for record in self._filtered_data(self._hashkey, self._filter_params):
            record.update(params)
            updateted_records.append(record)
        self._filter_params.clear()
        return updateted_records
        
    def delete(self) -> Union[List[Dict], List]:
        """Удаление записей из кеша по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).delete()`

        Returns:
            Union[List[Dict], List]: Удаленные записи из кеша или пустой список.
        """  
        if not self._hashkey:
            raise NotQuery()
        deleted = []
        if self._hashkey not in self._cache:
            return deleted
        for i in self._get_index_records(self._hashkey, self._filter_params):
            deleted.append(self._cache[self._hashkey][i])
            del self._cache[self._hashkey][i]
        self._filter_params.clear()
        return deleted
    
    def _get_data_query(self, query: str) -> Union[List[Tuple], List]:
        """Получает данные из произвольного запроса.

        Args:
            query (str): SQL запрос.

        Returns:
            Union[List[List], List]: Данные.
        """
        hashkey = self._get_hashkey_query(query)
        if hashkey in self._cache:
            return self._cache[self._hashkey]
        return []
        
    def _save_data_query(self, query: str, data: List[Tuple]):
        """Сохраняет даннные произвольного запроса в кеш.

        Args:
            query (str): SQL запрос.
            data (List[Tuple]): Данные.
        """
        hashkey = self._get_hashkey_query(query)
        self._cache[hashkey] = data

    def _get_index_records(self, hashkey: str, params: Dict) -> Iterator[int]:
        """Получение индексов записей в кеше.

        Args:
            hashkey (str): Ключ запроса.
            params (Dict): Параметры выборки.

        Yields:
            Iterator: Индекс.
        """
        for i, record in enumerate(self._cache[hashkey]):
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                yield i

    def _check_fields_identity(self, hashkey: str, keys: List) -> bool:
        """Проверить чтобы список полей был идентичен.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """        
        for record in self._cache[hashkey]:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(record.keys()):
                return True
            break
        return False

    def _check_fields_in_cache(self, hashkey: str, keys: List) -> bool:
        """Проверить поля на существование в записи кеша.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """        
        for record in self._cache[hashkey]:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(keys):
                return True
            break
        return False

    def _filtered_data(self, hashkey: str, params: Dict) -> Iterator[Dict]:
        """Фильтрация данных.

        Args:
            hashkey (str): Ключ запроса.
            params (Dict): Параметры фильрации.

        Yields:
            Iterator: Отфильтрованный элемент из кеша.
        """        
        for record in self._cache[hashkey]:
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                yield record

    def _get_tables_from_fields(self, data: List[Dict]) -> List:
        """Список таблиц которые участвуют в запросе.

        Args:
            data (List[Dict]): Данные из БД.

        Returns:
            List: Список названий таблиц.
        """        
        tables = set()
        for field in data[0].keys():
            table_field = field.split('.')
            # если в название поля есть таблица
            if len(table_field) > 1:
                tables.add(table_field[0])
        return list(tables)

    def _save_hashkey_in_tables(
        self, tables: List[str], hashkey: str
    ):
        """Сохраняет для каждой таблицы хеш запроса.
        (В каком запросе участвовала таблица)
        Args:
            hashkey (str): Хеш от запроса.
            tables (List[str]): Список названий таблиц.
        """
        for table in tables:
            if self._tables.get(table) is None:
                self._tables[table] = [hashkey]
                continue
            self._tables[table].append(hashkey)

    def _delete_hashkey_in_tables(self, hashkey: str):
        """Удаление hashkey из таблиц.

        Args:
            hashkey (str): Хеш.
        """        
        for _, hashkeys in self._tables.items():
            if hashkey not in hashkeys:
                continue
            hashkeys.remove(hashkey)

    def _get_hashkey_query(self, query: str) -> str:
        """Получение кеша от запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            str: Хеш от запроса.
        """        
        query = query.strip().lower().replace(" ", "")
        hash_object = hashlib.sha256(query.encode('utf-8'))
        return hash_object.hexdigest()