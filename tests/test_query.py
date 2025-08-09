import os
from settings import logger, BaseTest, tests_dir
from query_tables.query import Query, Join, LeftJoin
from query_tables.exceptions import ErrorConvertDataQuery
import sqlite3
import shutil

class TestQuery(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_query.log'
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.address = ('address', ['id', 'street', 'building'])
        cls.company = ('company', ['id', 'name', 'ref_address', 'registration'])
        cls.employees = ('employees', ['id', 'ref_person', 'ref_company', 'hired', 'dismissed'])
        cls.person = ('person', ['id', 'login', 'name', 'ref_address', 'age'])
        shutil.copy(tests_dir.joinpath('backup', 'test.db'), tests_dir / 'test_query.db')
        cls.conn = sqlite3.connect(tests_dir / 'test_query.db')
        cls.cursor = cls.conn.cursor()
        
    @classmethod
    def tearDownClass(cls):
        try:
            if cls.cursor:
                cls.cursor.close()
            if cls.conn:
                cls.conn.close()
            os.remove(tests_dir / 'test_query.db')
        except Exception:
            logger.info('----Ошибка удаление временной БД.')
    
    def test_case_1(self):
        logger.info('1. Запросы на получение записей.')
        
        logger.info('----обойти такое "экранирование" через Unicode-символы.')
        query = Query(*self.person).filter(name="1\'; DROP TABLE users; --").get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 0)
        
        logger.info('----обойти такое "экранирование" через двойные кавычки.')
        query = Query(*self.person).filter(name='1"; DROP TABLE users; --').get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 0)
        
        logger.info('----обойти такое "экранирование" через HEX-формате.')
        with self.assertRaises(ErrorConvertDataQuery):
            hex_payload = "27204f5220313d313b202d2d".encode()
            query = Query(*self.person).filter(id=hex_payload).get()
            logger.debug(query)
        
        logger.info('----Получение по идентификатору из одной таблице.')
        query = Query(*self.person).filter(id=2).get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Получение несколько записей по диапазону.')
        query = Query(*self.person).filter(age__between=(25, 31)).get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 2)
        
        logger.info('----Получение записей с join таблицей.')
        query = Query(*self.person).filter(age__between=(25, 31)).join(
            Join(Query(*self.address), 'id', 'ref_address')
        ).get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[0]), 8)
        
        logger.info('----Получение записей по текстовой дате.')
        query = Query(*self.company).filter(registration__between=('2021-02-20', '2021-04-20')).get()
        logger.debug(query)
        res = self.cursor.execute(query).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Вложенные join запросы.')
        query = Query(*self.person).filter(id=2).join(
            Join(Query(*self.address), 'id', 'ref_address')
        ).join(
            LeftJoin(Query(*self.employees), 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(Query(*self.company), 'id', 'ref_company').join(
                    Join(Query(*self.address), 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2020-01-02', '2020-01-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age='desc')
        logger.debug(query.get())
        res = self.cursor.execute(query.get()).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Изменение количества выводимых полей.')
        self.assertEqual(len(res[0]), 17)
        
        logger.info('----Мапинг полей в join запросах.')
        mapfields = "address.id, address.street, address.building, employees.id, employees.ref_person, employees.ref_company, employees.hired, company.id, company.name, company.ref_address, company.registration, compony_addr.id, compony_addr.street, compony_addr.building, person.id, person.name, person.age"
        mapfields = mapfields.replace(" ", '').split(',')
        self.assertListEqual(query.map_fields, mapfields)
        
        logger.info('----Мапинг полей в одной таблице.')
        query = Query(*self.person).filter(id=1)
        mapfields = 'person.id, person.login, person.name, person.ref_address, person.age'
        mapfields = mapfields.replace(" ", '').split(',')
        self.assertListEqual(query.map_fields, mapfields)
        
        logger.info('----Left join запрос при отсутсвие записи в таблице.')
        query = Query(*self.person).filter(id=4).join(
            LeftJoin(Query(*self.employees), 'ref_person', 'id')
        )
        logger.debug(query.get())
        res = self.cursor.execute(query.get()).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Поиск по части имени.')
        query = Query(*self.person).filter(name__like='%%4')
        logger.debug(query.get())
        res = self.cursor.execute(query.get()).fetchall()
        self.assertEqual(len(res), 1)
        logger.info("-------------------------------------------------------")
        
    def test_case_2(self):
        logger.info('2. Запросы на изменения.')
        
        logger.info('----Update с фильтрацией.')
        query = Query(*self.person).filter(id=4).update(age=34, name='Tony 4')
        logger.debug(query)
        res = self.cursor.execute(query)
        self.assertEqual(res.rowcount, 1)
        
        logger.info('----Insert одной записи.')
        query = Query(*self.person).insert([
            dict(
                login='fer0',
                name='Anton 5',
                age=36,
                ref_address=1
            )
        ])
        logger.debug(query)
        res = self.cursor.execute(query)
        self.assertEqual(res.lastrowid, 5)
        
        logger.info('----Insert несколько записей.')
        query = Query(*self.person).insert([
            dict(
                login='fer0',
                name='Anton 5',
                age=36,
                ref_address=1
            ),
            dict(
                login='fdgdf',
                name='Anton 6',
                age=37,
                ref_address=2
            )
        ])
        logger.debug(query)
        res = self.cursor.execute(query)
        self.assertEqual(res.lastrowid, 7)
        self.assertEqual(res.rowcount , 2)
        
        logger.info('----Удаление записи.')
        query = Query(*self.person).filter(id=6).delete()
        logger.debug(query)
        res = self.cursor.execute(query)
        self.assertEqual(res.rowcount , 1)
        logger.info("-------------------------------------------------------")
        
if __name__ == "__main__":
    TestQuery.start()