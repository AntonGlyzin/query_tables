import hashlib
import redis
import json
import datetime
import logging
import base64
import uuid
from threading import RLock
from typing import Union, List, Dict, Optional, Iterator, Tuple
from dataclasses import dataclass
from query_tables.cache import BaseCache, TypeCache
from query_tables.exceptions import NoMatchFieldInCache
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class SyncLockDecorator:
    """
        Обертка для redis в многопоточном приложение.
    """    
    def __init__(self, method, rlock):
        self.method = method
        self.rlock = rlock

    def __call__(self, *args, **kwargs):
        with self.rlock:
            try:
                return self.method(*args, **kwargs)
            except ConnectionError as e:
                logger.error(f"Произошла ошибка соединения с Redis: {e}")
            except TimeoutError as e:
                logger.error(f"Время ожидания выполнения команды истекло: {e}")


@dataclass
class RedisConnect:
    host: str = '127.0.0.1'
    user: str = ''
    password: str = ''
    port: int = 6379
    db: int = 0
    
    def get_conn(self) -> Dict:
        return {
            'host': self.host,
            'db': self.db,
            'password': self.password,
            'port': self.port
        }
        
    def get_url(self):
        if not self.password:
            return f'redis://{self.host}:{self.port}/{self.db}'
        return f'redis://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}'

        
class RedisCache(BaseCache):
    
    type_cache = TypeCache.remote
    
    def __init__(self, conn: RedisConnect):
        self._conn = conn
        self._pool = redis.ConnectionPool(**self._conn.get_conn())
        self._redis = redis.StrictRedis(
            decode_responses=True, 
            connection_pool=self._pool
        )
        self._key_queries = 'queries'
        self._key_tables = 'tables'
        self._key_struct = 'struct_tables'
        self._res: List[Dict] = []
        self._hashkey = ''
        self._filter_params = {}
        self._rlock = RLock()
        lock_methods = [
            self.is_enabled_cache,
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
        try:
            self._redis.ping()
            return True
        except redis.ConnectionError:
            return False

    def clear(self):
        """
            Очищение кеша.
        """ 
        self._redis.flushdb()

    def delete_cache_table(self, table: str) -> bool:
        """Удаление кеша по таблице. Вседу, где использовалась таблица.
            Не связан с конкретным запросом.

        Args:
            table (str): Название таблицы.
        
        Returns:
            bool: Флаг успешности.
        """
        hashes = self._redis.lrange(f'{self._key_tables}:{table}', 0, -1)
        if not hashes:
            return False
        for hashkey in hashes:
            _hashkey = hashkey.decode()
            self._redis.delete(f'{self._key_queries}:{_hashkey}')
            self._delete_hashkey_in_tables(_hashkey)
        return True

    def __getitem__(self, query: str) -> 'BaseCache':
        """Устанавливает контекст SQL запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            BaseCache: Кеш.
        """
        return self._getitem_(query)
    
    def _getitem_(self, query: str) -> 'BaseCache':
        self._res = []
        self._hashkey = self._get_hashkey_query(query)
        res_str = self._redis.get(f'{self._key_queries}:{self._hashkey}')
        if res_str:
            self._res = json.loads(res_str)
        else:
            self._delete_hashkey_in_tables(self._hashkey)
        return self
    
    def get(self) -> Union[List[Dict], List]:
        """Получение данных из кеша по условию или без условия.

        Returns:
            Union[List[Dict], List]: Записи или пустой список.
        """
        if not self._filter_params:
            return self._res
        else:
            data = list(self._filtered_data(self._filter_params))
            self._filter_params.clear()
            return data

    def __setitem__(self, query: str, data: List[Dict]):
        """Сохранить в кеш данные.

        Args:
            query (str): SQL запрос.
            data (List[Dict]): Результирующие данные из БД.
        """
        return self._setitem_(query, data)

    def _setitem_(self, query: str, data: List[Dict]):
        hashkey = self._get_hashkey_query(query)
        tables = self._get_tables_from_fields(data)
        self._save_hashkey_in_tables(tables, hashkey)
        self._redis.set(f'{self._key_queries}:{hashkey}', self._encode_data(data))

    def __delitem__(self, query: str):
        """Удаление из кеша данных.

        Args:
            query (str): SQL запрос.
        """
        return self._delitem_(query)

    def _delitem_(self, query: str):
        hashkey = self._get_hashkey_query(query)
        self._redis.delete(f'{self._key_queries}:{hashkey}')
        self._delete_hashkey_in_tables(hashkey)

    def filter(self, params: Dict) -> 'BaseCache':
        """Условие для выборки записей в кеше.
        Выборка учитывает точное совпадение значений.
        
        Args:
            Название полей для выборки. К примеру: `.filter({'person.id': 1, 'person.name': 'Anton'})`
                Название таблицы: person
                Название поля: id

        Returns:
            BaseCache: Кеш.
        """
        if not self._check_fields_in_cache(list(params.keys())):
            raise NoMatchFieldInCache()
        self._filter_params.clear()
        self._filter_params.update(params)
        return self
        
    def insert(self, record: Dict) -> Optional[Dict]:
        """Добавление записи к кеш.

        Args:
            params (Dict): Запись.
            
        Raises:
            NoMatchFieldInCache: Нет такого поля.
        """
        if not self._check_fields_identity(list(record.keys())):
            raise NoMatchFieldInCache()
        if not self._redis.exists(f'{self._key_queries}:{self._hashkey}'):
            return None
        self._res.append(record)
        self._redis.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        return record

    def update(self, params: Dict) -> Union[List[Dict], List]:
        """Обновление записей в кеше по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).update({'person.name': 'Anton'})`
                либо `.update(**params)`
                
        Raises:
            NoMatchFieldInCache: Нет такого поля.

        Returns:
            Union[List[Dict], List]: Обновленные записи или пустой список.
        """
        if not self._check_fields_in_cache(list(params.keys())):
            raise NoMatchFieldInCache()
        updateted_records = []
        if not self._redis.exists(f'{self._key_queries}:{self._hashkey}'):
            self._filter_params.clear()
            return updateted_records
        for record in self._filtered_data(self._filter_params):
            record.update(params)
            updateted_records.append(record)
        self._redis.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        self._filter_params.clear()
        return updateted_records

    def delete(self) -> Union[List[Dict], List]:
        """Удаление записей из кеша по условию.
        
        Args:
            Название полей для обновления. К примеру: `.filter({'person.id': 1}).delete()`

        Returns:
            Union[List[Dict], List]: Удаленные записи из кеша или пустой список.
        """
        deleted = []
        if not self._redis.exists(f'{self._key_queries}:{self._hashkey}'):
            self._res = []
            self._filter_params.clear()
            return deleted
        for i in self._get_index_records(self._filter_params):
            deleted.append(self._res[i])
            del self._res[i]
        self._redis.set(f'{self._key_queries}:{self._hashkey}', self._encode_data(self._res))
        self._filter_params.clear()
        return deleted
    
    def _get_data_query(self, query: str) -> Union[List[List], List]:
        """Получает данные из произвольного запроса.

        Args:
            query (str): SQL запрос.

        Returns:
            Union[List[List], List]: Данные.
        """        
        hashkey = self._get_hashkey_query(query)
        res_str = self._redis.get(f'{self._key_queries}:{hashkey}')
        if res_str:
            return json.loads(res_str)
        return []
        
    def _save_data_query(self, query: str, data: List[Tuple]):
        """Сохраняет даннные произвольного запроса в кеш.

        Args:
            query (str): SQL запрос.
            data (List[Tuple]): Данные.
        """        
        hashkey = self._get_hashkey_query(query)
        self._redis.set(f'{self._key_queries}:{hashkey}', self._encode_data(data))
    
    def _get_struct_tables(self) -> Optional[Dict[str, List[str]]]:
        """Получение из кеша структуры таблиц.

        Returns:
            Optional[Dict[str, List[str]]]: Структура таблиц.
        """        
        res = self._redis.get(self._key_struct)
        if not res:
            return None 
        return json.loads(res)
        
    def _save_struct_tables(self, struct: Dict[str, List[str]]):
        """Сохранение в кеше структуры таблиц.

        Args:
            struct (Dict[str, List[str]]): Структура таблиц.
        """        
        res = json.dumps(struct)
        self._redis.set(self._key_struct, res)
    
    def _encode_data(self, data: List[Dict]) -> str:
        """Кодирование данных перед отправкой в редис.

        Args:
            data (List[Dict]): Данные.

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
            self._redis.lpush(f'{self._key_tables}:{table}', hashkey)
        
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
    
    def _delete_hashkey_in_tables(self, hashkey: str):
        """ Удаление hashkey из таблиц. """
        tables_name = self._redis.keys(f'{self._key_tables}:*')
        for table in tables_name:
            _table = table.decode()
            _, _table = _table.split(':')
            self._redis.lrem(f'{self._key_tables}:{_table}', 0, hashkey)
    
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