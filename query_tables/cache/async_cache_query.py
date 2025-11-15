import hashlib
from typing import Union, List, Dict, Optional, Tuple, Any
from query_tables.exceptions import NotQuery, NoMatchFieldInCache, DesabledCache
from query_tables.cache.base_cache import AsyncBaseCache, TypeCache
import asyncio
from aiocache import Cache


class AsyncLockDecorator:
    """
        Обертка для async.
    """    
    def __init__(self, method, lock):
        self.method = method
        self.lock = lock

    async def __call__(self, *args, **kwargs):
        async with self.lock:
            return await self.method(*args, **kwargs)


class AsyncCacheQuery(AsyncBaseCache):
    """
        Асинхронное кеширование данных в памяти процесса на основе запроса к БД.
    """
    
    type_cache = TypeCache.local
    
    def __init__(self, ttl: int = 0, non_expired: bool = False):
        """
        
        Args:
            ttl (int, optional): Время кеша запроса. По умолчанию 0 секунд - кеширование отключено.
            non_expired (bool, optional): Если нужен кеш без истечения времени.
        """
        self._ttl = ttl
        self._non_expired = non_expired
        self._hashkey = '' # хэш от SQL запроса
        self._filter_params = {}
        self._tables = Cache(Cache.MEMORY)
        self._cache = Cache(Cache.MEMORY)
        self._lock = asyncio.Lock()
        lock_methods = [
            self.is_enabled_cache,
            self.clear,
            self.delete_cache_table,
            self.get,
            self.set_data,
            self.delete_query,
            self.insert,
            self.update,
            self.delete,
            self.get_data_query,
            self.save_data_query,
            self.delete_data_query
        ]
        for method in lock_methods:
            setattr(
                self, method.__name__, 
                AsyncLockDecorator(method, self._lock)
            )
    
    async def is_enabled_cache(self) -> bool:
        """
            Включен ли кеш.
        """        
        return self._non_expired or bool(self._ttl)

    async def clear(self):
        """
            Очищение кеша.
        """
        await self._cache.clear()
        await self._tables.clear()

    async def delete_cache_table(self, table: str) -> bool:
        """Удаление кеша по таблице. Вседу, где использовалась таблица.

        Args:
            table (str): Название таблицы.
        
        Returns:
            bool: Флаг успешности.
        """
        hashkeys = await self._tables.get(table)
        if not hashkeys:
            return False
        for hashkey in [*hashkeys]:
            await self._cache.delete(hashkey)
            await self._delete_hashkey_in_tables(hashkey)
        return True
        
    def __getitem__(self, query: str) -> 'AsyncBaseCache':
        """Устанавливает контекст SQL запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            BaseCache: Кеш.
        """
        if not query:
            raise NotQuery()
        if not (self._non_expired or bool(self._ttl)):
            raise DesabledCache()
        self._hashkey = self._get_hashkey_query(query)
        return self
        
    async def get(self) -> Union[List[Dict], List]:
        """Получение данных из кеша по условию или без условия.

        Returns:
            Union[List[Dict], List]: Записи или пустой список.
        """
        if not self._hashkey:
            raise NotQuery()
        if self._hashkey in self._get_hashkeys_cache():
            if not self._filter_params:
                return await self._cache.get(self._hashkey)
            else:
                check = await self._check_fields_in_cache(self._hashkey, list(self._filter_params.keys()))
                if not check:
                    raise NoMatchFieldInCache()
                data = await self._filtered_data(self._hashkey, self._filter_params)
                self._filter_params.clear()
                return data
        await self._delete_hashkey_in_tables(self._hashkey)
        return []

    async def set_data(self, data: List[Dict], tables: List[str] = None):
        """Сохранить в кеш данные.

        Args:
            data (List[Dict]): Результирующие данные из БД.
            tables: List[str]: Список таблиц.
        """
        tables = tables or self._get_tables_from_fields(data)
        await self._save_hashkey_in_tables(tables, self._hashkey)
        await self._set_cache(self._hashkey, data)

    async def delete_query(self):
        """Удаление из кеша данных.

        Args:
            query (str): SQL запрос.
        """
        await self._cache.delete(self._hashkey)
        await self._delete_hashkey_in_tables(self._hashkey)
    
    def filter(self, params: Dict) -> 'AsyncBaseCache':
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
        self._filter_params.clear()
        self._filter_params.update(params)
        return self
    
    async def insert(self, record: Dict) -> Optional[Dict]:
        """Добавление записи к кеш.

        Args:
            params (Dict): Запись.
            
        Raises:
            NotQuery: Запрос не установлен.
            NoMatchFieldInCache: Нет такого поля.
        """ 
        if not self._hashkey:
            raise NotQuery()
        identity = await self._check_fields_identity(self._hashkey, list(record.keys()))
        if not identity:
            raise NoMatchFieldInCache()
        if self._hashkey not in self._get_hashkeys_cache():
            await self._set_cache(self._hashkey, [record])
        else:
            data = await self._cache.get(self._hashkey)
            data.append(record)
            await self._set_cache(self._hashkey, data)
        return record
        
    async def update(self, params: Dict) -> Union[List[Dict], List]:
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
        check = await self._check_fields_in_cache(self._hashkey, list(params.keys()))
        if not check:
            raise NoMatchFieldInCache()
        updateted_records = []
        if self._hashkey not in self._get_hashkeys_cache():
            return updateted_records
        filtered_data = await self._filtered_data(self._hashkey, self._filter_params)
        for record in filtered_data:
            record.update(params)
            updateted_records.append(record)
        self._filter_params.clear()
        return updateted_records
    
    async def delete(self) -> Union[List[Dict], List]:
        """Удаление записей из кеша по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).delete()`

        Returns:
            Union[List[Dict], List]: Удаленные записи из кеша или пустой список.
        """  
        if not self._hashkey:
            raise NotQuery()
        check = await self._check_fields_in_cache(self._hashkey, list(self._filter_params.keys()))
        if not check:
            raise NoMatchFieldInCache()
        deleted = []
        if self._hashkey not in self._get_hashkeys_cache():
            return deleted
        indexes = await self._get_index_records(self._hashkey, self._filter_params)
        data = await self._cache.get(self._hashkey)
        for i in indexes:
            deleted.append(data[i])
            del data[i]
        if data:
            await self._set_cache(self._hashkey, data)
        else:
            await self._cache.delete(self._hashkey)
        self._filter_params.clear()
        return deleted
    
    async def get_data_query(self, query: str) -> Union[List[Tuple], List]:
        """Получает данные из произвольного запроса.

        Args:
            query (str): SQL запрос.

        Returns:
            Union[List[List], List]: Данные.
        """
        hashkey = self._get_hashkey_query(query)
        data = await self._cache.get(hashkey)
        if not data:
            return []
        return data
    
    async def save_data_query(self, query: str, data: List[Tuple]):
        """Сохраняет даннные произвольного запроса в кеш.

        Args:
            query (str): SQL запрос.
            data (List[Tuple]): Данные.
        """
        hashkey = self._get_hashkey_query(query)
        await self._set_cache(hashkey, data)
    
    async def delete_data_query(self, query: str):
        """Удаляет даннные произвольного запроса из кеша.

        Args:
            query (str): SQL запрос.
        """        
        hashkey = self._get_hashkey_query(query)
        await self._cache.delete(hashkey)

    async def _get_index_records(self, hashkey: str, params: Dict) -> List[int]:
        """Получение индексов записей в кеше.

        Args:
            hashkey (str): Ключ запроса.
            params (Dict): Параметры выборки.

        Yields:
            Iterator: Индекс.
        """
        data = []
        records = await self._cache.get(hashkey)
        for i, record in enumerate(records):
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                data.append(i)
        return data

    async def _check_fields_identity(self, hashkey: str, keys: List) -> bool:
        """Проверить чтобы список полей был идентичен.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """
        records = await self._cache.get(hashkey)
        for record in records:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(record.keys()):
                return True
            break
        return False

    async def _check_fields_in_cache(self, hashkey: str, keys: List) -> bool:
        """Проверить поля на существование в записи кеша.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """
        records = await self._cache.get(hashkey)
        if not records:
            return True
        for record in records:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(keys):
                return True
            break
        return False

    async def _filtered_data(self, hashkey: str, params: Dict) -> List[Dict]:
        """Фильтрация данных.

        Args:
            hashkey (str): Ключ запроса.
            params (Dict): Параметры фильрации.

        Yields:
            Iterator: Отфильтрованный элемент из кеша.
        """
        data = []
        records = await self._cache.get(hashkey)
        for record in records:
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                data.append(record)
        return data

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

    async def _save_hashkey_in_tables(
        self, tables: List[str], hashkey: str
    ):
        """Сохраняет для каждой таблицы хеш запроса.
        (В каком запросе участвовала таблица)
        
        Args:
            hashkey (str): Хеш от запроса.
            tables (List[str]): Список названий таблиц.
        """
        for table in tables:
            values = await self._tables.get(table)
            if values is None:
                await self._tables.set(table, [hashkey])
                continue
            values.append(hashkey)
            await self._tables.set(table, values)

    async def _delete_hashkey_in_tables(self, hashkey: str):
        """Удаление hashkey из таблиц.

        Args:
            hashkey (str): Хеш.
        """
        if not hasattr(self._tables, '_cache'):
            return
        items = list(self._tables._cache.items())
        for table, hashkeys in items:
            if hashkey not in hashkeys:
                continue
            hashkeys.remove(hashkey)
            await self._tables.set(table, hashkeys)
            
    async def _set_cache(self, key: str, value: Any):
        """Установить в кеш данные в зависимости от опций.

        Args:
            key (str): Значение.
            value (Any): Данные.
        """        
        if self._non_expired:
            return await self._cache.set(key, value)
        if self._ttl:
            return await self._cache.set(key, value, self._ttl)
    
    def _get_tables_cache(self) -> List[str]:
        """Таблицы участвующие в запросах.

        Returns:
            List[str]: Список таблиц.
        """
        if not hasattr(self._tables, '_cache'):
            return []
        return list(self._tables._cache.keys())
    
    def _get_hashkeys_cache(self) -> List[str]:
        """Ключи по которым хранятся данные.

        Returns:
            List[str]: Список ключей.
        """
        if not hasattr(self._cache, '_cache'):
            return []
        return list(self._cache._cache.keys())

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