import hashlib
import asyncio
from redis import asyncio as aioredis
import json
import datetime
import logging
import base64
import uuid
from typing import Union, List, Dict, Optional, Iterator, Tuple
from query_tables.cache import AsyncBaseCache, RedisConnect, TypeCache
from query_tables.exceptions import NoMatchFieldInCache

logger = logging.getLogger(__name__)


class AsyncLockDecorator:
    """
        Обертка для async redis.
    """    
    def __init__(self, method, lock):
        self.method = method
        self.lock = lock

    async def __call__(self, *args, **kwargs):
        async with self.lock:
            try:
                return await self.method(*args, **kwargs)
            except ConnectionError as e:
                logger.error(f"Произошла ошибка соединения с Redis: {e}")
            except TimeoutError as e:
                logger.error(f"Время ожидания выполнения команды истекло: {e}")


class AsyncRedisCache(AsyncBaseCache):
    
    type_cache = TypeCache.remote
    
    def __init__(self, conn: RedisConnect):
        self._conn = conn
        self._pool = aioredis.ConnectionPool.from_url(conn.get_url(), encoding="utf-8", decode_responses=True)
        self._redis = aioredis.Redis.from_pool(connection_pool=self._pool)
        self._key_queries = 'queries'
        self._key_tables = 'tables'
        self._key_struct = 'struct_tables'
        self._res: List[Dict] = []
        self._hashkey = ''
        self._filter_params = {}
        self._lock = asyncio.Lock()
        lock_methods = [
            self.is_enabled_cache,
            self.clear,
            self.delete_cache_table,
            self.set_data,
            self.delete_query,
            self.insert,
            self.update,
            self.delete
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
        try:
            async with self._redis as client:
                await client.ping()
            return True
        except aioredis.ConnectionError:
            return False

    async def clear(self):
        """
            Очищение кеша.
        """
        async with self._redis as client:
            await client.flushdb()

    async def delete_cache_table(self, table: str) -> bool:
        """Удаление кеша по таблице. Вседу, где использовалась таблица.
            Не связан с конкретным запросом.

        Args:
            table (str): Название таблицы.
        
        Returns:
            bool: Флаг успешности.
        """
        async with self._redis as client:
            hashes = await client.lrange(f'{self._key_tables}:{table}', 0, -1)
            if not hashes:
                return False
            await client.delete(
                *[f'{self._key_queries}:{hashkey}' for hashkey in hashes]
            )
        for hashkey in hashes:
            await self._delete_hashkey_in_tables(hashkey)
        return True

    def __getitem__(self, query: str) -> 'AsyncBaseCache':
        """Устанавливает контекст SQL запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            AsyncBaseCache: Кеш.
        """
        self._res = []
        self._hashkey = self._get_hashkey_query(query)
        return self
    
    async def get(self) -> Union[List[Dict], List]:
        """Получение данных из кеша по условию или без условия.

        Returns:
            Union[List[Dict], List]: Записи или пустой список.
        """
        if not self._res:
            await self._init_data()
        if not self._filter_params:
            return self._res
        else:
            if not self._check_fields_in_cache(list(self._filter_params.keys())):
                raise NoMatchFieldInCache()
            data = list(self._filtered_data(self._filter_params))
            self._filter_params.clear()
            return data

    async def set_data(self, data: List[Dict]):
        """Сохранить в кеш данные.

        Args:
            data (List[Dict]): Результирующие данные из БД.
        """
        tables = self._get_tables_from_fields(data)
        await self._save_hashkey_in_tables(tables, self._hashkey)
        async with self._redis as client:
            await client.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(data))

    async def delete_query(self):
        """ Удаление из кеша данных. """
        async with self._redis as client:
            await client.delete(f'{self._key_queries}:{self._hashkey}')
        await self._delete_hashkey_in_tables(self._hashkey)

    def filter(self, params: Dict) -> 'AsyncBaseCache':
        """Условие для выборки записей в кеше.
        Выборка учитывает точное совпадение значений.
        
        Args:
            Название полей для выборки. К примеру: `.filter({'person.id': 1, 'person.name': 'Anton'})`
                Название таблицы: person
                Название поля: id

        Returns:
            AsyncBaseCache: Кеш.
        """
        self._filter_params.clear()
        self._filter_params.update(params)
        return self
        
    async def insert(self, record: Dict) -> Optional[Dict]:
        """Добавление записи к кеш.

        Args:
            params (Dict): Запись.
            
        Raises:
            NoMatchFieldInCache: Нет такого поля.
        """
        if not self._res:
            await self._init_data()
        if not self._check_fields_identity(list(record.keys())):
            raise NoMatchFieldInCache()
        async with self._redis as client:
            res_key = await client.exists(f'{self._key_queries}:{self._hashkey}')
        if not res_key:
            await self._delete_hashkey_in_tables(self._hashkey)
            self._res = []
            return None
        self._res.append(record)
        async with self._redis as client:
            await client.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        return record

    async def update(self, params: Dict) -> Union[List[Dict], List]:
        """Обновление записей в кеше по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).update({'person.name': 'Anton'})`
                либо `.update(**params)`
                
        Raises:
            NoMatchFieldInCache: Нет такого поля.

        Returns:
            Union[List[Dict], List]: Обновленные записи или пустой список.
        """
        updateted_records = []
        if not self._res:
            await self._init_data()
        if not self._check_fields_in_cache(list(self._filter_params.keys())):
            raise NoMatchFieldInCache()
        if not self._check_fields_in_cache(list(params.keys())):
            raise NoMatchFieldInCache()
        async with self._redis as client:
            res_key = await client.exists(f'{self._key_queries}:{self._hashkey}')
        if not res_key:
            await self._delete_hashkey_in_tables(self._hashkey)
            self._res = []
            self._filter_params.clear()
            return updateted_records
        for record in self._filtered_data(self._filter_params):
            record.update(params)
            updateted_records.append(record)
        async with self._redis as client:
            await client.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        self._filter_params.clear()
        return updateted_records

    async def delete(self) -> Union[List[Dict], List]:
        """Удаление записей из кеша по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).delete()`

        Returns:
            Union[List[Dict], List]: Удаленные записи из кеша или пустой список.
        """
        deleted = []
        if not self._res:
            await self._init_data()
        if not self._check_fields_in_cache(list(self._filter_params.keys())):
            raise NoMatchFieldInCache()
        async with self._redis as client:
            res_key = await client.exists(f'{self._key_queries}:{self._hashkey}')
        if not res_key:
            await self._delete_hashkey_in_tables(self._hashkey)
            self._res = []
            self._filter_params.clear()
            return deleted
        for i in self._get_index_records(self._filter_params):
            deleted.append(self._res[i])
            del self._res[i]
        async with self._redis as client:
            await client.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        self._filter_params.clear()
        return deleted
    
    async def _get_data_query(self, query: str) -> Union[List[List], List]:
        """Получает данные из произвольного запроса.

        Args:
            query (str): SQL запрос.

        Returns:
            Union[List[List], List]: Данные.
        """        
        hashkey = self._get_hashkey_query(query)
        async with self._redis as client:
            res_str = await client.get(f'{self._key_queries}:{hashkey}')
        if res_str:
            return json.loads(res_str)
        return []
        
    async def _save_data_query(self, query: str, data: List[Tuple]):
        """Сохраняет даннные произвольного запроса в кеш.

        Args:
            query (str): SQL запрос.
            data (List[Tuple]): Данные.
        """        
        hashkey = self._get_hashkey_query(query)
        async with self._redis as client:
            await client.set(f'{self._key_queries}:{hashkey}', self._encode_data(data))
    
    async def _get_struct_tables(self) -> Optional[Dict[str, List[str]]]:
        """Получение из кеша структуры таблиц.

        Returns:
            Optional[Dict[str, List[str]]]: Структура таблиц.
        """
        async with self._redis as client:
            res = await client.get(self._key_struct)
        if not res:
            return None 
        return json.loads(res)
    
    async def _save_struct_tables(self, struct: Dict[str, List[str]]):
        """Сохранение в кеше структуры таблиц.

        Args:
            struct (Dict[str, List[str]]): Структура таблиц.
        """        
        res = json.dumps(struct)
        async with self._redis as client:
            await client.set(self._key_struct, res)
    
    async def _init_data(self):
        """ Инициализирует переменную с данными по запросу. """
        async with self._redis as client:
            res_str = await client.get(f'{self._key_queries}:{self._hashkey}')
        if res_str:
            self._res = json.loads(res_str)
        else:
            await self._delete_hashkey_in_tables(self._hashkey)
    
    def _encode_data(self, data: List[Dict]) -> str:
        """Кодирование данных для redis.

        Args:
            data (List[Dict]): Список из БД.

        Returns:
            str: json строка.
        """        
        class Encoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime.datetime):
                    return o.isoformat()
                elif isinstance(o, memoryview):
                    return bytes(o).hex()
                elif isinstance(o, tuple):
                    return list(o)
                elif isinstance(o, bytes):
                    return base64.b64encode(o).decode('utf-8')
                elif isinstance(o, uuid.UUID):
                    return str(o)
                return super().default(o)
        return json.dumps(data, cls=Encoder)
    
    def _get_index_records(self, params: Dict) -> Iterator[int]:
        """Получение индексов записей в кеше.

        Args:
            hashkey (str): Ключ запроса.
            params (Dict): Параметры выборки.

        Yields:
            Iterator: Индекс.
        """
        for i, record in enumerate(self._res):
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                yield i
    
    def _check_fields_identity(self, keys: List) -> bool:
        """Проверить чтобы список полей был идентичен.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """        
        for record in self._res:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(record.keys()):
                return True
            break
        return False
    
    def _check_fields_in_cache(self, keys: List) -> bool:
        """Проверить поля на существование в записи кеша.

        Args:
            hashkey (str): Ключ запроса.
            keys (List): Список полей.

        Returns:
            bool: Флаг.
        """        
        for record in self._res:
            common_values = set(record.keys()) & set(keys)
            if len(common_values) == len(keys):
                return True
            break
        return False
    
    async def _save_hashkey_in_tables(
        self, tables: List[str], hashkey: str
    ):
        """Сохраняет для каждой таблицы хеш запроса.
        (В каком запросе участвовала таблица)
        Args:
            hashkey (str): Хеш от запроса.
            tables (List[str]): Список названий таблиц.
        """
        async with self._redis as client:
            for table in tables:
                await client.lpush(f'{self._key_tables}:{table}', hashkey)
        
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
    
    def _filtered_data(self, params: Dict) -> Iterator[Dict]:
        """Фильтрация данных.

        Args:
            params (Dict): Параметры фильтрации.

        Yields:
            Iterator: Отфильтрованный элемент из кеша.
        """        
        for record in self._res:
            common_values = record.items() & params.items()
            if len(params.keys()) == len(common_values):
                yield record
    
    async def _delete_hashkey_in_tables(self, hashkey: str):
        """ Удаление hashkey из таблиц. """
        async with self._redis as client:
            tables_name = await client.keys(f'{self._key_tables}:*')
            for table in tables_name:
                _, _table = table.split(':')
                await client.lrem(f'{self._key_tables}:{_table}', 0, hashkey)
    
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