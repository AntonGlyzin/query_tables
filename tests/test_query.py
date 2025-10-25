import os
from settings import logger, BaseTest, tests_dir
from query_tables.query import Query, Join, LeftJoin, AND, OR
import shutil
from query_tables.db import SQLiteQuery

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
        cls.sqlite = SQLiteQuery(tests_dir / 'test_query.db')
        cls.sqlite.set_placeholder_pattern(r'%\((\w+)\)s', '%({})s')
        cls.sqlite.connect()
        
    @classmethod
    def tearDownClass(cls):
        try:
            cls.sqlite.close()
            os.remove(tests_dir / 'test_query.db')
        except Exception:
            logger.info('----Ошибка удаление временной БД.')
    
    def test_case_1(self):
        logger.info('1. Запросы на получение записей.')
        
        logger.info('----обойти такое "экранирование" через Unicode-символы.')
        query = Query(*self.person).filter(name="1\'; DROP TABLE users; --")
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params).fetchall()
        self.assertEqual(len(res), 0)
        
        logger.info('----обойти такое "экранирование" через двойные кавычки.')
        query = Query(*self.person).filter(name='1"; DROP TABLE users; --')
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params).fetchall()
        self.assertEqual(len(res), 0)
        
        logger.info('----Получение по идентификатору из одной таблице.')
        query = Query(*self.person).filter(id=2)
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Получение несколько записей по диапазону.')
        query = Query(*self.person).filter(age__between=(25, 31))
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql,  query.params).fetchall()
        self.assertEqual(len(res), 2)
        
        logger.info('----Получение записей с join таблицей.')
        query = Query(*self.person).filter(age__between=(25, 31)).join(
            Join(Query(*self.address), 'id', 'ref_address')
        )
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql,  query.params).fetchall()
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[0]), 8)
        
        logger.info('----Получение записей по текстовой дате.')
        query = Query(*self.company).filter(registration__between=('2021-02-20', '2021-04-20'))
        sql = query.get()
        logger.debug(sql)
        
        res = self.sqlite.execute(sql,  query.params).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Вложенные join запросы.')
        query = Query(*self.person).filter(id=1).join(
            Join(Query(*self.address), 'id', 'ref_address')
        ).join(
            LeftJoin(Query(*self.employees), 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(Query(*self.company), 'id', 'ref_company').join(
                    Join(Query(*self.address), 'id', 'ref_address', 'compony_addr')
                ).filter(registration__between=('2021-02-02', '2021-04-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age='desc')
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params).fetchall()
        self.assertEqual(len(res), 1)
        
        query = Query(*self.person).filter(id=1, name__like='Ant%%').join(
            Join(Query(*self.address), 'id', 'ref_address').filter(OR(AND(street__like='%%ушкина', building=10), AND(building__in=[5,10])))
        ).join(
            LeftJoin(Query(*self.employees), 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(Query(*self.company), 'id', 'ref_company').join(
                    Join(Query(*self.address), 'id', 'ref_address', 'compony_addr').filter(AND(street__like='%%эйкер', id=5))
                ).filter(registration__between=('2021-01-02', '2021-04-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age='desc')
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Изменение количества выводимых полей.')
        self.assertEqual(len(res[0]), 17)
        
        logger.info('----Мапинг полей в join запросах.')
        mapfields = "person.id, person.name, person.age, address.id, address.street, address.building, employees.id, employees.ref_person, employees.ref_company, employees.hired, company.id, company.name, company.ref_address, company.registration, compony_addr.id, compony_addr.street, compony_addr.building"
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
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql,  query.params).fetchall()
        self.assertEqual(len(res), 1)
        
        logger.info('----Поиск по части имени.')
        query = Query(*self.person).filter(name__like='%%4')
        sql = query.get()
        logger.debug(sql)
        res = self.sqlite.execute(sql,  query.params).fetchall()
        self.assertEqual(len(res), 1)
        logger.info("-------------------------------------------------------")
        
    def test_case_2(self):
        logger.info('2. Запросы на изменения.')
        
        logger.info('----Update с фильтрацией.')
        query = Query(*self.person).filter(id=4)
        sql = query.update(age=34, name='Tony 4')
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params)
        self.assertEqual(res.cursor.rowcount, 1)
        
        logger.info('----Insert одной записи.')
        query = Query(*self.person)
        sql=query.insert([
            dict(
                login='fer0',
                name='Anton 5',
                age=36,
                ref_address=1
            )
        ])
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params)
        self.assertEqual(res.cursor.lastrowid, 5)
        
        logger.info('----Insert несколько записей.')
        query = Query(*self.person)
        sql=query.insert([
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
        logger.debug(sql)
        res = self.sqlite.execute(sql, query.params)
        self.assertEqual(res.cursor.lastrowid, 7)
        self.assertEqual(res.cursor.rowcount , 2)
        
        logger.info('----Удаление записи.')
        query = Query(*self.person).filter(id=6).delete()
        logger.debug(query)
        res = self.sqlite.execute(query, dict(person_id=6))
        self.assertEqual(res.cursor.rowcount , 1)
        logger.info("-------------------------------------------------------")
        
if __name__ == "__main__":
    TestQuery.start()