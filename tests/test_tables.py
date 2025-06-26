import shutil
import os
import asyncio
from settings import logger, BaseTest, tests_dir
from query_tables.db import SQLiteQuery, AsyncSQLiteQuery, AsyncPostgresQuery, DBConfigPg
from query_tables.tables import Tables, TablesAsync
from query_tables.query import Join, LeftJoin
from query_tables.exceptions import DesabledCache, ErrorExecuteJoinQuery
from query_tables.cache import RedisCache, RedisConnect, AsyncRedisCache


class TestTables(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_tables.log'
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loop = asyncio.new_event_loop()
        shutil.copy(tests_dir.joinpath('backup', 'test.db'), tests_dir / 'test_tables.db')
        sqlite = SQLiteQuery(tests_dir / 'test_tables.db')
        cls.sqlite_tables = Tables(sqlite) # кеш отключен по умолчанию
        cls.sqlite_tables_cache = Tables(sqlite, non_expired=True) # включен вечный кеш
        cls.sqlite_tables_ttlcache = Tables(sqlite, cache_ttl=300) # включен временный кеш
        
        connect = RedisConnect()
        redis_cache = RedisCache(connect)
        redis_cache.clear()
        cls.sqlite_redis_tables = Tables(sqlite, cache=redis_cache)# кеш redis
        
        shutil.copy(tests_dir.joinpath('backup', 'test.db'), tests_dir / 'test_tables_async.db')
        async_sqlite = AsyncSQLiteQuery(tests_dir / 'test_tables_async.db')
        
        redis = AsyncRedisCache(RedisConnect())
        async def get_async_remote_cache():
            table = TablesAsync(async_sqlite, cache=redis)
            await table.init()
            return table
        cls.remote_cache = cls.loop.run_until_complete(get_async_remote_cache())
        
        async def get_async_sqlite():
            table = TablesAsync(async_sqlite)
            await table.init()
            return table
        cls.async_sqlite_tables = cls.loop.run_until_complete(get_async_sqlite())
        async def get_async_sqlite_cache():
            table = TablesAsync(async_sqlite, non_expired=True)
            await table.init()
            return table
        cls.async_sqlite_cache_tables = cls.loop.run_until_complete(get_async_sqlite_cache())
        
        postgres_async = AsyncPostgresQuery(
            DBConfigPg('localhost', 'query_tables', 'postgres', 'postgres')
        )
        async def get_async_postgres():
            async with postgres_async as db_query:
                await db_query.execute(
                    """
                        CREATE TABLE IF NOT EXISTS public.address (
                            id SERIAL PRIMARY KEY,
                            street VARCHAR(255) NOT NULL,
                            building INTEGER NOT NULL
                        );
                    """
                )
            async with postgres_async as db_query:
                await db_query.execute('delete from public.address')
            async with postgres_async as db_query:
                await db_query.execute(
                    """
                        INSERT INTO public.address (id,street,building) VALUES
                            (1,'Пушкина',10),
                            (2,'Наумова',33),
                            (3,'Гринвич',12),
                            (4,'Приморская',8),
                            (5,'Бэйкер',11)
                    """
                )
            table = TablesAsync(postgres_async, non_expired=True)
            await table.init()
            return table
        cls.async_tables_postgres = cls.loop.run_until_complete(get_async_postgres())
        
    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(tests_dir / 'test_tables.db')
            os.remove(tests_dir / 'test_tables_async.db')
            cls.loop.close()
        except Exception:
            logger.info('----Ошибка удаление временной БД.')
        
    def _common_query(self, table: Tables):
        logger.info('----Проверка доступа к кешу.')
        if not table['person']._cache.is_enabled_cache():
            with self.assertRaises(DesabledCache):
                logger.info('-----Доступ к кешу закрыт.')
                table['person'].cache
        else:
            table['person'].cache
            logger.info('-----Доступ к кешу открыт.')
        
        logger.info('----Получение записи по ИД.')
        res = table['person'].filter(id=2).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        
        logger.info('----Получение записи по части имени.')
        res = table['person'].filter(name__like='%%4').get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записи по вхождению.')
        res = table['person'].filter(age__in=[30]).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        
        logger.info('----Получение записи по диапазону.')
        res = table['person'].filter(age__between=(30, 31)).order_by(id='asc').get()
        logger.debug(res)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['person.id'], 1)
        
        logger.info('----Получение записи по больще или равно.')
        res = table['person'].filter(age__gte=35).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записи по диапазону дат.')
        res = table['company'].filter(registration__between=('2020-01-04', '2020-01-05')).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['company.name'], 'Hex')
        
        logger.info('----Сортировка и лимит записей.')
        res = table['person'].order_by(id='desc').limit(1).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записей с join таблицей.')
        res = table['person'].join(
            Join(table['address'], 'id', 'ref_address')
        ).filter(age__between=(25, 31)).get()
        logger.debug(res)
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[0].keys()), 8)
        
        logger.info('----Получение записей с join таблицей в которой нет записей.')
        res = table['person'].filter(id=4).join(
            Join(table['employees'], 'ref_person', 'id')
        ).get()
        logger.debug(res)
        self.assertEqual(len(res), 0)
        
        logger.info('----Получение записей с left join таблицей в которой нет записей.')
        res = table['person'].filter(id=4).join(
            LeftJoin(table['employees'], 'ref_person', 'id')
        ).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        
        logger.info('----Вложенные join запросы с фильтрацией и выбором полей.')
        res = table['person'].filter(id=2).join(
            Join(table['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(table['employees'], 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(table['company'], 'id', 'ref_company').join(
                    Join(table['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age='desc').get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0].keys()), 17)
        
    async def _async_common_query(self, table: TablesAsync):
        logger.info('----Получение записи по ИД.')
        res = await table['person'].filter(id=2).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        
        logger.info('----Получение записи по части имени.')
        res = await table['person'].filter(name__like='%%4').get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записи по вхождению.')
        res = await table['person'].filter(age__in=[30]).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        
        logger.info('----Получение записи по диапазону.')
        res = await table['person'].filter(age__between=(30, 31)).order_by(id='asc').get()
        logger.debug(res)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['person.id'], 1)
        
        logger.info('----Получение записи по больще или равно.')
        res = await table['person'].filter(age__gte=35).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записи по диапазону дат.')
        res = await table['company'].filter(registration__between=('2020-01-04', '2020-01-05')).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['company.name'], 'Hex')
        
        logger.info('----Сортировка и лимит записей.')
        res = await table['person'].order_by(id='desc').limit(1).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 4')
        
        logger.info('----Получение записей с join таблицей.')
        res = await table['person'].join(
            Join(table['address'], 'id', 'ref_address')
        ).filter(age__between=(25, 31)).get()
        logger.debug(res)
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[0].keys()), 8)
        
        logger.info('----Получение записей с join таблицей в которой нет записей.')
        res = await table['person'].filter(id=4).join(
            Join(table['employees'], 'ref_person', 'id')
        ).get()
        logger.debug(res)
        self.assertEqual(len(res), 0)
        
        logger.info('----Получение записей с left join таблицей в которой нет записей.')
        res = await table['person'].filter(id=4).join(
            LeftJoin(table['employees'], 'ref_person', 'id')
        ).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        
        logger.info('----Вложенные join запросы с фильтрацией и выбором полей.')
        res = await table['person'].filter(id=2).join(
            Join(table['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(table['employees'], 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(table['company'], 'id', 'ref_company').join(
                    Join(table['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age='desc').get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0].keys()), 17)
        
    def _cache_query(self, c_tables: Tables):
        logger.info('----Получение единичной записи.')
        query = c_tables['person'].filter(id=2)
        query.get()
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        c_tables.clear_cache()
        
        logger.info('----Получение нескольких записей.')
        query = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        query.get()
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 3)
        
        logger.info('----Получение записей по фильтру внутри кеша.')
        res = query.cache.filter({'person.id': 1}).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        
        logger.info('----Изменение записей по фильтру внутри кеша.')
        query.cache.filter({'person.id': 1}).update({'person.name': 'Tony 1', 'person.age': 32})
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(res[-1]['person.name'], 'Tony 1')
        self.assertEqual(res[-1]['person.age'], 32)
        
        logger.info('----Добавление записей в кеш.')
        query.cache.insert({
            'person.id': 6, 
            'person.login': 'qqq', 
            'person.name': 'Anton 6', 
            'person.ref_address': 0, 
            'person.age': 0,
            'address.id': 6,
            'address.street': 'ytutyu',
            'address.building': 567
        })
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 4)
        
        logger.info('----Удаление записи из кеша.')
        query.cache.filter({'person.id': 6}).delete()
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 3)
        
        logger.info('----Удаление кеша привязаного к запросу.')
        query.delete_cache_query()
        res = query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 0)
        
        logger.info('----Удаление кеша по таблице при изменение данных в таблице.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        query1.get()
        query2.get()
        query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables['address'].insert([dict(
            street='123',
            building=777
        )])
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице по запросу.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        query1.get()
        query2.get()
        query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables['address'].delete_cache_table()
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице при изменение данных.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        query1.get()
        query2.get()
        query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables['address'].filter(id=1).update(building=11)
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
    async def _async_cache_query(self, c_tables: TablesAsync):
        logger.info('----Получение единичной записи.')
        query = c_tables['person'].filter(id=2)
        await query.get()
        logger.debug(query.cache.get())
        self.assertEqual(len(query.cache.get()), 1)
        self.assertEqual(query.cache.get()[0]['person.name'], 'Anton 2')
        c_tables.clear_cache()
        
        logger.info('----Получение нескольких записей.')
        query = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        await query.get()
        logger.debug(query.cache.get())
        self.assertEqual(len(query.cache.get()), 3)
        
        logger.info('----Получение записей по фильтру внутри кеша.')
        res = query.cache.filter({'person.id': 1}).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        
        logger.info('----Изменение записей по фильтру внутри кеша.')
        query.cache.filter({'person.id': 1}).update({'person.name': 'Tony 1', 'person.age': 32})
        logger.debug(query.cache.get())
        self.assertEqual(query.cache.get()[-1]['person.name'], 'Tony 1')
        self.assertEqual(query.cache.get()[-1]['person.age'], 32)
        
        logger.info('----Добавление записей в кеш.')
        query.cache.insert({
            'person.id': 6, 
            'person.login': 'qqq', 
            'person.name': 'Anton 6', 
            'person.ref_address': 0, 
            'person.age': 0,
            'address.id': 6,
            'address.street': 'ytutyu',
            'address.building': 567
        })
        logger.debug(query.cache.get())
        self.assertEqual(len(query.cache.get()), 4)
        
        logger.info('----Удаление записи из кеша.')
        query.cache.filter({'person.id': 6}).delete()
        logger.debug(query.cache.get())
        self.assertEqual(len(query.cache.get()), 3)
        
        logger.info('----Удаление кеша привязаного к запросу.')
        query.delete_cache_query()
        logger.debug(query.cache.get())
        self.assertEqual(len(query.cache.get()), 0)
        
        logger.info('----Удаление кеша по таблице при изменение данных в таблице.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        await c_tables['address'].insert([dict(
            street='123',
            building=777
        )])
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице по запросу.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables['address'].delete_cache_table()
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице при изменение данных.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(query1.cache.get())
        self.assertTrue(query2.cache.get())
        self.assertTrue(query3.cache.get())
        await c_tables['address'].filter(id=1).update(building=11)
        self.assertFalse(query2.cache.get())
        self.assertFalse(query2.cache.get())
        self.assertTrue(query3.cache.get())
        c_tables.clear_cache()
        
    async def _async_remote_cache_query(self, c_tables: TablesAsync):
        await c_tables.clear_cache()
        logger.info('----Получение единичной записи.')
        query = c_tables['person'].filter(id=2)
        await query.get()
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['person.name'], 'Anton 2')
        await c_tables.clear_cache()
        
        logger.info('----Получение нескольких записей.')
        query = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        await query.get()
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 3)
        
        logger.info('----Получение записей по фильтру внутри кеша.')
        res = await query.cache.filter({'person.id': 1}).get()
        logger.debug(res)
        self.assertEqual(len(res), 1)
        
        logger.info('----Изменение записей по фильтру внутри кеша.')
        await query.cache.filter({'person.id': 1}).update({'person.name': 'Tony 1', 'person.age': 32})
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(res[-1]['person.name'], 'Tony 1')
        self.assertEqual(res[-1]['person.age'], 32)
        
        logger.info('----Добавление записей в кеш.')
        await query.cache.insert({
            'person.id': 6, 
            'person.login': 'qqq', 
            'person.name': 'Anton 6', 
            'person.ref_address': 0, 
            'person.age': 0,
            'address.id': 6,
            'address.street': 'ytutyu',
            'address.building': 567
        })
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 4)
        
        logger.info('----Удаление записи из кеша.')
        await query.cache.filter({'person.id': 6}).delete()
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 3)
        
        logger.info('----Удаление кеша привязаного к запросу.')
        await query.delete_cache_query()
        res = await query.cache.get()
        logger.debug(res)
        self.assertEqual(len(res), 0)
        
        logger.info('----Удаление кеша по таблице при изменение данных в таблице.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(await query1.cache.get())
        self.assertTrue(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables['address'].insert([dict(
            street='123',
            building=777
        )])
        self.assertFalse(await query2.cache.get())
        self.assertFalse(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице по запросу.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(await query1.cache.get())
        self.assertTrue(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables['address'].delete_cache_table()
        self.assertFalse(await query2.cache.get())
        self.assertFalse(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables.clear_cache()
        
        logger.info('----Удаление кеша по таблице при изменение данных.')
        query1 = c_tables['person'].join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
        
        query2 = c_tables['person'].filter(id=2).join(
            Join(c_tables['address'], 'id', 'ref_address')
        ).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id').join(
                Join(c_tables['company'], 'id', 'ref_company').join(
                    Join(c_tables['address'], 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).order_by(age='desc')
        
        query3 = c_tables['person'].filter(id=3).join(
            LeftJoin(c_tables['employees'], 'ref_person', 'id')
        )
        
        await query1.get()
        await query2.get()
        await query3.get()
        self.assertTrue(await query1.cache.get())
        self.assertTrue(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables['address'].filter(id=1).update(building=11)
        self.assertFalse(await query2.cache.get())
        self.assertFalse(await query2.cache.get())
        self.assertTrue(await query3.cache.get())
        await c_tables.clear_cache()
        
    def _change_db_query(self, table: Tables):
        query3 = table['person'].filter(id=3).join(
            LeftJoin(table['employees'], 'ref_person', 'id')
        )
        with self.assertRaises(ErrorExecuteJoinQuery):
            query3.delete()
        
        logger.info('----Встатвка данных в БД.')
        table['person'].insert([dict(
            login='tt',
            name='Ton',
            ref_address=1,
            age=55
        )])
        res = table['person'].get()
        self.assertEqual(len(res), 5)
        self.assertEqual(res[-1]['person.name'], 'Ton')
        self.assertEqual(res[-1]['person.age'], 55)
        id_res = res[-1]['person.id']
        table.clear_cache()
        
        logger.info('----Изменение данных в БД.')
        table['person'].filter(id=id_res).update(login='ant2', age=32)
        res = table['person'].filter(id=id_res).get()
        self.assertEqual(res[0]['person.login'], 'ant2')
        self.assertEqual(res[0]['person.age'], 32)
        table.clear_cache()
        
        logger.info('----Удаление данных из БД.')
        table['person'].filter(id=id_res).delete()
        res = table['person'].filter(id=id_res).get()
        self.assertEqual(len(res), 0)
        
    async def _async_change_db_query(self, table: TablesAsync):
        query3 = table['person'].filter(id=3).join(
            LeftJoin(table['employees'], 'ref_person', 'id')
        )
        with self.assertRaises(ErrorExecuteJoinQuery):
            await query3.delete()
        
        logger.info('----Встатвка данных в БД.')
        await table['person'].insert([dict(
            login='tt',
            name='Ton',
            ref_address=1,
            age=55
        )])
        res = await table['person'].get()
        self.assertEqual(len(res), 5)
        self.assertEqual(res[-1]['person.name'], 'Ton')
        self.assertEqual(res[-1]['person.age'], 55)
        id_res = res[-1]['person.id']
        table.clear_cache()
        
        logger.info('----Изменение данных в БД.')
        await table['person'].filter(id=id_res).update(login='ant2', age=32)
        res = await table['person'].filter(id=id_res).get()
        self.assertEqual(res[0]['person.login'], 'ant2')
        self.assertEqual(res[0]['person.age'], 32)
        table.clear_cache()
        
        logger.info('----Удаление данных из БД.')
        await table['person'].filter(id=id_res).delete()
        res = await table['person'].filter(id=id_res).get()
        self.assertEqual(len(res), 0)
        
    async def _async_remote_change_db_query(self, table: TablesAsync):
        await table.clear_cache()
        query3 = table['person'].filter(id=3).join(
            LeftJoin(table['employees'], 'ref_person', 'id')
        )
        with self.assertRaises(ErrorExecuteJoinQuery):
            await query3.delete()
        
        logger.info('----Встатвка данных в БД.')
        await table['person'].insert([dict(
            login='tt',
            name='Ton',
            ref_address=1,
            age=55
        )])
        res = await table['person'].get()
        self.assertEqual(len(res), 5)
        self.assertEqual(res[-1]['person.name'], 'Ton')
        self.assertEqual(res[-1]['person.age'], 55)
        id_res = res[-1]['person.id']
        await table.clear_cache()
        
        logger.info('----Изменение данных в БД.')
        await table['person'].filter(id=id_res).update(login='ant2', age=32)
        res = await table['person'].filter(id=id_res).get()
        self.assertEqual(res[0]['person.login'], 'ant2')
        self.assertEqual(res[0]['person.age'], 32)
        await table.clear_cache()
        
        logger.info('----Удаление данных из БД.')
        await table['person'].filter(id=id_res).delete()
        res = await table['person'].filter(id=id_res).get()
        self.assertEqual(len(res), 0)
        
        
    def test_case_1(self):
        logger.info("1. Выполнение запросов на получение записей.")
        logger.info("-С отключенным кешем.")
        self._common_query(self.sqlite_tables)
        self.sqlite_tables.clear_cache()
        
        logger.info("-С временным кешем.")
        self._common_query(self.sqlite_tables_ttlcache)
        self.sqlite_tables_ttlcache.clear_cache()
        
        logger.info("-С постоянным кешем.")
        self._common_query(self.sqlite_tables_cache)
        self.sqlite_tables_cache.clear_cache()
        
        logger.info("-Кеш redis.")
        self._common_query(self.sqlite_redis_tables)
        self.sqlite_redis_tables.clear_cache()
        logger.info("-------------------------------------------------------")
        
    def test_case_2(self):
        logger.info("2. Работа с кешем данных через запросы.")
        
        logger.info("-С временным кешем.")
        self._cache_query(self.sqlite_tables_ttlcache)
        self.sqlite_tables_ttlcache.clear_cache()
        
        logger.info("-С постоянным кешем.")
        self._cache_query(self.sqlite_tables_cache)
        self.sqlite_tables_cache.clear_cache()
        
        logger.info("-Кеш redis.")
        self._cache_query(self.sqlite_redis_tables)
        self.sqlite_redis_tables.clear_cache()
        logger.info("-------------------------------------------------------")
        
    def test_case_3(self):
        logger.info("3. Изменение данных в БД.")
        
        logger.info("-С кешем.")
        self._change_db_query(self.sqlite_tables_cache)
        self.sqlite_tables_cache.clear_cache()
        
        logger.info("-Без кеша.")
        self._change_db_query(self.sqlite_tables)
        
        logger.info("-Кеш redis.")
        self._change_db_query(self.sqlite_redis_tables)
        self.sqlite_redis_tables.clear_cache()
        logger.info("-------------------------------------------------------")
        
    def test_case_4(self):
        logger.info("4. Асинхроность.")
        logger.info("Выполнение запросов на получение записей.")
        logger.info("-Без кеша.")
        self.loop.run_until_complete(self._async_common_query(self.async_sqlite_tables))
        self.async_sqlite_tables.clear_cache()
        logger.info("-С постоянным кешем.")
        self.loop.run_until_complete(self._async_common_query(self.async_sqlite_cache_tables))
        self.async_sqlite_cache_tables.clear_cache()
        logger.info("-С redis кешем.")
        self.loop.run_until_complete(self._async_common_query(self.remote_cache))
        logger.info("-------------------------------------------------------")
        
        logger.info("Работа с кешем данных через запросы.")
        logger.info("-С постоянным кешем.")
        self.loop.run_until_complete(self._async_cache_query(self.async_sqlite_cache_tables))
        self.async_sqlite_cache_tables.clear_cache()
        logger.info("-С redis кешем.")
        self.loop.run_until_complete(self._async_remote_cache_query(self.remote_cache))
        logger.info("-------------------------------------------------------")
        
        logger.info("Изменение данных в БД.")
        logger.info("-С кешем.")
        self.loop.run_until_complete(self._async_change_db_query(self.async_sqlite_cache_tables))
        logger.info("-Без кеша.")
        self.loop.run_until_complete(self._async_change_db_query(self.async_sqlite_tables))
        logger.info("-redis кеша.")
        self.loop.run_until_complete(self._async_remote_change_db_query(self.remote_cache))
        logger.info("-------------------------------------------------------")
        
if __name__ == "__main__":
    TestTables.start()