from settings import logger, BaseTest
from threading import Thread
import time

from query_tables.cache.cache_query import CacheQuery, SyncLockDecorator

from query_tables.exceptions import NoMatchFieldInCache


class TestCacheQuery(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_cache_query.log'
    
    def test_case_1(self):
        logger.info('1. Получение и удаление данных из кеша по sql запросу.')
        
        cache = CacheQuery(ttl=300)
        logger.info('----Запись в кеш.')
        query1 = "очень длинная строка sql запроса 1"
        cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton' }
        ]
        
        query2 = "очень длинная строка sql запроса 2"
        cache[query2] = [
            { 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }
        ]
        
        query3 = "очень длинная строка sql запроса 3"
        cache[query3] = [
            { 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }
        ]
        logger.info('----Чтение записей из кеша.')
        self.assertIsInstance(cache[query1].get(), list)
        self.assertListEqual(cache[query1].get(), [{ 'person.id': 1, 'person.name': 'Anton' }])
        self.assertListEqual(cache[query2].get(), [{ 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }])
        self.assertListEqual(cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
        
        logger.info('----Удаление закешированные записи связанные с таблицей person.')
        cache.delete_cache_table('person')
        self.assertFalse(cache[query1].get())
        self.assertFalse(cache[query2].get())
        self.assertListEqual(cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
        
        logger.info('----Удаление закешированную запись по sql запросу.')
        del cache[query3]
        self.assertFalse(cache[query3].get())
        
    def test_case_2(self):
        logger.info('2. Попытка удалить кеш из потока 2 при попытки чтения из потока 1.')
        logger.info('----Чтение будет 3 секунды. Запуск удаление через 1 секунду.')
        
        from queue import Queue
        q = Queue()
        
        cache = CacheQuery(ttl=300)
        query1 = "очень длинная строка sql запроса 1"
        cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton' }
        ]
        
        query2 = "очень длинная строка sql запроса 2"
        cache[query2] = [
            { 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }
        ]
        def read(query):
            time.sleep(3)
            q.put('Значение прочитано.')
            
        def delete(s):
            q.put('Удаление отработано.')
        
        cache._get_item = SyncLockDecorator(read)
        cache.delete_cache_table = SyncLockDecorator(delete)
        th1 = Thread(target=lambda : cache[query2])
        th1.start()
        time.sleep(1)
        th2 = Thread(target=lambda : cache.delete_cache_table('person'))
        th2.start()
        
        self.assertEqual(q.get(timeout=4), 'Значение прочитано.')
        self.assertEqual(q.get(timeout=4), 'Удаление отработано.')
        logger.info('----Порядок выполнений операций не нарушен.')
        
    def test_case_3(self):
        logger.info('3. Асинхроность.')
        import asyncio
        
        cache = CacheQuery(ttl=300, use_async=True)
        
        async def main():
            logger.info('----Запись в кеш.')
            query1 = "очень длинная строка sql запроса 1"
            cache[query1] = [
                { 'person.id': 1, 'person.name': 'Anton' }
            ]
            
            query2 = "очень длинная строка sql запроса 2"
            cache[query2] = [
                { 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }
            ]
            logger.info('----Чтение записей из кеша.')
            self.assertIsInstance(cache[query1].get(), list)
            self.assertListEqual(cache[query1].get(), [{ 'person.id': 1, 'person.name': 'Anton' }])
            self.assertListEqual(cache[query2].get(), [{ 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }])
            
            logger.info('----Удаление закешированные записи связанные с таблицей person.')
            cache.delete_cache_table('person')
            self.assertFalse(cache[query1].get())
            self.assertFalse(cache[query2].get())
            
        asyncio.run(main())
        
    def test_case_4(self):
        logger.info('4. Изменение единичной записи в кеше по ссылки.')
        cache = CacheQuery(ttl=300)
        logger.info('----Запись в кеш.')
        query1 = "очень длинная строка sql запроса 1"
        cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton 1' },
            { 'person.id': 2, 'person.name': 'Anton 2' },
            { 'person.id': 3, 'person.name': 'Anton 3' }
        ]
        
        def changed1(item):
            item['person.name'] = 'Tony 2'
            
        logger.info('----Изменение во внутренней функции.')
        for item in cache[query1].get():
            if item['person.id']==2:
                changed1(item)
        self.assertDictEqual(cache[query1].get()[1], { 'person.id': 2, 'person.name': 'Tony 2' })
        
        logger.info('----Update словаря.')
        for item in cache[query1].get():
            if item['person.id']==1:
                item.update(
                    { 'person.id': 1, 'person.name': 'Tony 1' }
                )
        self.assertDictEqual(cache[query1].get()[0], { 'person.id': 1, 'person.name': 'Tony 1' })
        
        logger.info('----Поиск и обновление по индексу.')
        index = 0
        for _index, item in enumerate(cache[query1].get()):
            if item['person.id']==3:
                index = _index
                cache[query1].get()[_index].update(
                    { 'person.id': 3, 'person.name': 'Tony 3' }
                )
                cache[query1].get()[_index]['person.id'] = 4
                break
        self.assertDictEqual(cache[query1].get()[index], { 'person.id': 4, 'person.name': 'Tony 3' })
        
    def test_case_5(self):
        logger.info('5. Получение и изменение данных в кеше по фильтрации.')
        cache = CacheQuery(non_expired=True) #вечный кеш
        logger.info('----Запись в кеш.')
        query1 = "очень длинная строка sql запроса 1"
        cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton 1' },
            { 'person.id': 2, 'person.name': 'Anton 2' },
            { 'person.id': 3, 'person.name': 'Anton 3' }
        ]
        logger.info('----Получение по фильтрации.')
        pers1 = cache[query1].filter({ 'person.id': 2 }).get()
        self.assertDictEqual(pers1[0], { 'person.id': 2, 'person.name': 'Anton 2' })
        
        logger.info('----Обновление записи по фильтрации.')
        cache[query1].filter({ 'person.id': 2 }).update({ 'person.name': 'Tony 2' })
        pers2 = cache[query1].filter({ 'person.id': 2 }).get()
        self.assertDictEqual(pers2[0], { 'person.id': 2, 'person.name': 'Tony 2' })
        
        logger.info('----Удаление записи по фильтрации.')
        cache[query1].filter({ 'person.id': 2 }).delete()
        self.assertFalse(cache[query1].filter({ 'person.id': 2 }).get())
        self.assertEqual(len(cache[query1].get()), 2)
        
        logger.info('----Добавление записи в кеш.')
        cache[query1].insert({ 'person.id': 2, 'person.name': 'Anton 2' })
        self.assertEqual(len(cache[query1].get()), 3)
        
        logger.info('----Добавление записи с не правильными полями в кеш.')
        with self.assertRaises(NoMatchFieldInCache):
            cache[query1].insert({ 'person.id': 5, 'person.name12': 'Anton 2' })
            
        with self.assertRaises(NoMatchFieldInCache):
            cache[query1].insert({ 'person.id': 5 })


if __name__ == "__main__":
    TestCacheQuery.start()