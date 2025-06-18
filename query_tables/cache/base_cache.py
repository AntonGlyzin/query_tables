from abc import ABC
from typing import Union, List, Dict, Optional


class BaseCache(ABC):
    
    def is_enabled_cache(self) -> bool:
        """
            Включен ли кеш.
        """    
        ...
    
    def clear(self):
        """
            Очищение кеша.
        """ 
        ...
        
    def delete_cache_table(self, table: str) -> bool:
        """Удаление кеша по таблице. Вседу, где использовалась таблица.

        Args:
            table (str): Название таблицы.
        
        Returns:
            bool: Флаг успешности.
        """
        ...
        
    def __getitem__(self, query: str) -> 'BaseCache':
        """Устанавливает контекст SQL запроса.

        Args:
            query (str): SQL Запрос.

        Returns:
            BaseCache: Кеш.
        """
        ...
        
    def get(self) -> Union[List[Dict], List]:
        """Получение данных из кеша по условию или без условия.

        Returns:
            Union[List[Dict], List]: Записи или пустой список.
        """        
        ...

    def __setitem__(self, query: str, data: List[Dict]):
        """Сохранить в кеш данные.

        Args:
            query (str): SQL запрос.
            data (List[Dict]): Результирующие данные из БД.
        """
        ...

    def __delitem__(self, query: str):
        """Удаление из кеша данных.

        Args:
            query (str): SQL запрос.
        """        
        ...

    def filter(self, params: Dict) -> 'BaseCache':
        """Условие для выборки записей в кеше.
        Выборка учитывает точное совпадение значений.
        
        Args:
            Название полей для выборки. К примеру: .filter({'person.id': 1, 'person.name': 'Anton'})
                Название таблицы: person
                Название поля: id

        Returns:
            BaseCache: Кеш.
        """        
        ...
        
    def insert(self, record: Dict) -> Optional[Dict]:
        """Добавление записи к кеш.

        Args:
            params (Dict): Запись.

        Returns:
            Optional[Dict]: Запись или ничего.
        """        
        ...

    def update(self, params: Dict) -> Union[List[Dict], List]:
        """Обновление записей в кеше по условию.
        
        Args:
            Название полей для обновления. К примеру: .filter({'person.id': 1}).update({'person.name': 'Anton'})
                либо .update(**params)

        Returns:
            Union[List[Dict], List]: Обновленные записи или пустой список.
        """        
        ...

    def delete(self) -> Union[List[Dict], List]:
        """Удаление записей из кеша по условию.
        
        Args:
            Название полей для обновления. К примеру: .filter({'person.id': 1}).delete()

        Returns:
            Union[List[Dict], List]: Удаленные записи из кеша или пустой список.
        """        
        ...