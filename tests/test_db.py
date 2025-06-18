from settings import logger, BaseTest, tests_dir
import shutil
import os
import asyncio
from query_tables.db import (
    SQLiteQuery, AsyncSQLiteQuery, 
    DBConfigPg, PostgresQuery, AsyncPostgresQuery,
    BaseDBQuery, BaseAsyncDBQuery
)

class TestQuery(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_db.log'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        shutil.copy(tests_dir.joinpath('backup', 'test.db'), tests_dir / 'test_db.db')
        
        cls.sqlite = SQLiteQuery(tests_dir / 'test_db.db')
        cls.sqlite_async = AsyncSQLiteQuery(tests_dir / 'test_db.db')
        
        cls.postgres = PostgresQuery(
            DBConfigPg('localhost', 'test', 'postgres', 'postgres')
        )
        cls.postgres_async = AsyncPostgresQuery(
            DBConfigPg('localhost', 'test', 'postgres', 'postgres')
        )

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(tests_dir / 'test_db.db')
        except Exception:
            logger.info('----Ошибка удаление временной sqlite БД.')

    def _db_query(self, db: BaseDBQuery):
        logger.info('----Получение из БД.')
        with db as db_query:
            db_query.execute("select * from address")
            data = db_query.fetchall()
            self.assertEqual(len(data), 5)
            
        db_query = db.connect()
        db_query.execute("select * from address")
        data = db_query.fetchall()
        db.close()
        self.assertEqual(len(data), 5)
        
        logger.info('----Вставка в БД.')
        with db as db_query:
            db_query.execute("insert into address (id, street, building) values (8, 'qwer', 555)")
            
        with db as db_query:
            db_query.execute("select * from address")
            data = db_query.fetchall()
            self.assertEqual(len(data), 6)
            
        id_res = 8
        
        logger.info('----Обновление в БД.')
        with db as db_query:
            db_query.execute(f"update address set building=111 where id={id_res}")
        
        logger.info('----Удаление из БД.')
        with db as db_query:
            db_query.execute(f"delete from address where id={id_res}")
            
        with db as db_query:
            db_query.execute("select * from address")
            data = db_query.fetchall()
            self.assertEqual(len(data), 5)

    async def _db_query_async(self, db: BaseAsyncDBQuery):
        logger.info('----Получение из БД.')
        async with db as db_query:
            await db_query.execute("select * from address")
            data = await db_query.fetchall()
            self.assertEqual(len(data), 5)
            
        db_query = await db.connect()
        await db_query.execute("select * from address")
        data = await db_query.fetchall()
        await db.close()
        self.assertEqual(len(data), 5)
        
        logger.info('----Вставка в БД.')
        async with db as db_query:
            await db_query.execute("insert into address (id, street, building) values (8, 'qwer', 555)")
            
        async with db as db_query:
            await db_query.execute("select * from address")
            data = await db_query.fetchall()
            self.assertEqual(len(data), 6)
        
        id_res = 8
        
        logger.info('----Обновление в БД.')
        async with db as db_query:
            await db_query.execute(f"update address set building=111 where id={id_res}")
        
        logger.info('----Удаление из БД.')
        async with db as db_query:
            await db_query.execute(f"delete from address where id={id_res}")
            
        async with db as db_query:
            await db_query.execute("select * from address")
            data = await db_query.fetchall()
            self.assertEqual(len(data), 5)

    def test_case_1(self):
        logger.info('1. Проверка для SQLiteQuery.')
        self._db_query(self.sqlite)
        
        logger.info('2. Проверка для AsyncSQLiteQuery.')
        asyncio.run(self._db_query_async(self.sqlite_async))
        
        logger.info('3. Проверка для PostgresQuery.')
        self._db_query(self.postgres)
        
        logger.info('4. Проверка для AsyncPostgresQuery.')
        asyncio.run(self._db_query_async(self.postgres_async))


if __name__ == "__main__":
    TestQuery.start()