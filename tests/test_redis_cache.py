from settings import logger, BaseTest
import asyncio
from query_tables.cache import RedisCache, RedisConnect, AsyncRedisCache

from query_tables.exceptions import NoMatchFieldInCache


class TestRedisQuery(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_cache_redis.log'
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connect = RedisConnect()
        cls.cache = RedisCache(connect)
        cls.cache.clear()
        
        cls.async_cache = AsyncRedisCache(connect)
        
        cls.loop = asyncio.new_event_loop()
        
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.cache.clear()
        cls.loop.close()
        
    def test_case_1(self):
        logger.info('1. Получение и удаление данных из кеша по sql запросу.')
        
        logger.info('----Запись в кеш.')
        query1 = "очень длинная строка sql запроса 1"
        self.cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton' }
        ]
        
        query2 = "очень длинная строка sql запроса 2"
        self.cache[query2] = [
            { 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }
        ]
        
        query3 = "очень длинная строка sql запроса 3"
        self.cache[query3] = [
            { 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }
        ]
        logger.info('----Чтение записей из кеша.')
        self.assertIsInstance(self.cache[query1].get(), list)
        self.assertListEqual(self.cache[query1].get(), [{ 'person.id': 1, 'person.name': 'Anton' }])
        self.assertListEqual(self.cache[query2].get(), [{ 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }])
        self.assertListEqual(self.cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
        
        logger.info('----Удаление закешированные записи связанные с таблицей person.')
        self.cache.delete_cache_table('person')
        self.assertFalse(self.cache[query1].get())
        self.assertFalse(self.cache[query2].get())
        self.assertListEqual(self.cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
        
        logger.info('----Удаление закешированную запись по sql запросу.')
        del self.cache[query3]
        self.assertFalse(self.cache[query3].get())
        logger.info("-------------------------------------------------------")
        
    def test_case_2(self):
        logger.info('2. Получение и изменение данных в кеше по фильтрации.')
        
        logger.info('----Запись в кеш.')
        query1 = "очень длинная строка sql запроса 1"
        self.cache[query1] = [
            { 'person.id': 1, 'person.name': 'Anton 1' },
            { 'person.id': 2, 'person.name': 'Anton 2' },
            { 'person.id': 3, 'person.name': 'Anton 3' }
        ]
        logger.info('----Получение по фильтрации.')
        pers1 = self.cache[query1].filter({ 'person.id': 2 }).get()
        self.assertDictEqual(pers1[0], { 'person.id': 2, 'person.name': 'Anton 2' })
        
        logger.info('----Обновление записи по фильтрации.')
        self.cache[query1].filter({ 'person.id': 2 }).update({ 'person.name': 'Tony 2' })
        pers2 = self.cache[query1].filter({ 'person.id': 2 }).get()
        self.assertDictEqual(pers2[0], { 'person.id': 2, 'person.name': 'Tony 2' })
        
        logger.info('----Удаление записи по фильтрации.')
        self.cache[query1].filter({ 'person.id': 2 }).delete()
        self.assertFalse(self.cache[query1].filter({ 'person.id': 2 }).get())
        self.assertEqual(len(self.cache[query1].get()), 2)
        
        logger.info('----Добавление записи в кеш.')
        self.cache[query1].insert({ 'person.id': 2, 'person.name': 'Anton 2' })
        self.assertEqual(len(self.cache[query1].get()), 3)
        
        logger.info('----Добавление записи с не правильными полями в кеш.')
        with self.assertRaises(NoMatchFieldInCache):
            self.cache[query1].insert({ 'person.id': 5, 'person.name12': 'Anton 2' })
            
        with self.assertRaises(NoMatchFieldInCache):
            self.cache[query1].insert({ 'person.id': 5 })
        logger.info("-------------------------------------------------------")
        
    def test_case_2(self):
        logger.info('3. Асинхронный кеш редис.')
        
        async def test1():
            logger.info(' Получение и удаление данных из кеша по sql запросу.')
            logger.info('----Запись в кеш.')
            query1 = "очень длинная строка sql запроса 1"
            await self.async_cache[query1].set_data([
                { 'person.id': 1, 'person.name': 'Anton' }
            ])
            
            query2 = "очень длинная строка sql запроса 2"
            await self.async_cache[query2].set_data([
                { 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }
            ])
            
            query3 = "очень длинная строка sql запроса 3"
            await self.async_cache[query3].set_data([
                { 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }
            ])
            logger.info('----Чтение записей из кеша.')
            self.assertIsInstance(await self.async_cache[query1].get(), list)
            self.assertListEqual(await self.async_cache[query1].get(), [{ 'person.id': 1, 'person.name': 'Anton' }])
            self.assertListEqual(await self.async_cache[query2].get(), [{ 'person.id': 1, 'person.name': 'Anton', 'company.id': 1, 'company.name': 'SD' }])
            self.assertListEqual(await self.async_cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
            
            logger.info('----Удаление закешированные записи связанные с таблицей person.')
            await self.async_cache.delete_cache_table('person')
            self.assertFalse(await self.async_cache[query1].get())
            self.assertFalse(await self.async_cache[query2].get())
            self.assertListEqual(await self.async_cache[query3].get(), [{ 'company.id': 1, 'company.name': 'SD', 'address.id': 1, 'address.name': '33' }])
            
            logger.info('----Удаление закешированную запись по sql запросу.')
            await self.async_cache[query3].delete_query()
            self.assertFalse(await self.async_cache[query3].get())
            
        async def test2():
            logger.info(' Получение и изменение данных в кеше по фильтрации.')
        
            logger.info('----Запись в кеш.')
            query1 = "очень длинная строка sql запроса 1"
            await self.async_cache[query1].set_data([
                { 'person.id': 1, 'person.name': 'Anton 1' },
                { 'person.id': 2, 'person.name': 'Anton 2' },
                { 'person.id': 3, 'person.name': 'Anton 3' }
            ])
            logger.info('----Получение по фильтрации.')
            pers1 = await self.async_cache[query1].filter({ 'person.id': 2 }).get()
            self.assertDictEqual(pers1[0], { 'person.id': 2, 'person.name': 'Anton 2' })
            
            logger.info('----Обновление записи по фильтрации.')
            await self.async_cache[query1].filter({ 'person.id': 2 }).update({ 'person.name': 'Tony 2' })
            pers2 = await self.async_cache[query1].filter({ 'person.id': 2 }).get()
            self.assertDictEqual(pers2[0], { 'person.id': 2, 'person.name': 'Tony 2' })
            
            logger.info('----Удаление записи по фильтрации.')
            await self.async_cache[query1].filter({ 'person.id': 2 }).delete()
            self.assertFalse(await self.async_cache[query1].filter({ 'person.id': 2 }).get())
            self.assertEqual(len(await self.async_cache[query1].get()), 2)
            
            logger.info('----Добавление записи в кеш.')
            await self.async_cache[query1].insert({ 'person.id': 2, 'person.name': 'Anton 2' })
            self.assertEqual(len(await self.async_cache[query1].get()), 3)
            
            logger.info('----Добавление записи с не правильными полями в кеш.')
            with self.assertRaises(NoMatchFieldInCache):
                await self.async_cache[query1].insert({ 'person.id': 5, 'person.name12': 'Anton 2' })
                
            with self.assertRaises(NoMatchFieldInCache):
                await self.async_cache[query1].insert({ 'person.id': 5 })
            logger.info("-------------------------------------------------------")
        
        self.loop.run_until_complete(test1())
        self.loop.run_until_complete(test2())
   
    
    
if __name__ == "__main__":
    TestRedisQuery.start()