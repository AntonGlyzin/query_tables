import shutil
import os
from settings import logger, BaseTest, tests_dir
from query_tables.db import SQLiteQuery
from query_tables.tables import Tables
from query_tables.query import Join, LeftJoin, AND, OR, Ordering, Field
from query_tables.query.functions import (
    Upper, Max, Concat, Substring, Replace,
    Random, Extract, Char, Interval, Case, Coalesce
)


class TestFunctions(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_functions.log'
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        shutil.copy(tests_dir.joinpath('backup', 'test.db'), tests_dir / 'test_function.db')
        sqlite = SQLiteQuery(tests_dir / 'test_function.db')
        cls.tables = Tables(sqlite) # кеш отключен по умолчанию
        
    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(tests_dir / 'test_function.db')
        except Exception:
            logger.info('----Ошибка удаление временной БД.')
    
    def test_case_1(self):
        query = self.tables['person'].filter(id=2)
        logger.debug(query._query.get())
        len_fields1 = len(query._query.map_fields)
        logger.debug(query._query.map_fields)
        logger.debug(query._query.get())
        logger.debug(query._query.map_fields)
        len_fields2 = len(query._query.map_fields)
        self.assertEqual(len_fields1, len_fields2)
        
        query = self.tables['person'].filter(id=2).join(
            Join(self.tables['address'], Field('address', 'id'), Field('person', 'ref_address') )
        )
        logger.debug(query._query.get())
        len_fields1 = len(query._query.map_fields)
        logger.debug(query._query.map_fields)
        logger.debug(query._query.get())
        logger.debug(query._query.map_fields)
        len_fields2 = len(query._query.map_fields)
        self.assertEqual(len_fields1, len_fields2)
        
        """  
            select upper(company.name) as company_name, max(person.age) as person_age 
            from employees  
            join (

                select *  from person

            ) as person on person.id = employees.ref_person 

            join (

                select *  from company

            ) as company on company.id = employees.ref_company 

            where employees.dismissed is null 
            group by company.name 
            having (max(person.age) > %(employees_max_1)s 
                and company.registration > %(employees_registration_2)s) 
            order by company.name desc
        """
        query = self.tables['employees'].select(
            Upper(Field('company', 'name')).as_('company_name'), Max(Field('person', 'age')).as_('person_age')
        ).join(
            Join(self.tables['person'], Field('person', 'id'), Field('employees', 'ref_person')).select()
        ).join(
            Join(self.tables['company'], Field('company', 'id'), Field('employees', 'ref_company')).select()
        ).filter(
            Field('employees', 'dismissed').is_null()
        ).group_by(
            Field('company', 'name')
        ).having(
            AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))
        ).order_by(
            Field('company', 'name').desc()
        )
        logger.debug(query._query.get())
        res=query.get()
        self.assertEqual(len(res), 1)
        logger.debug(res)
        
        
        """ 
            select person.id, person.name, person.age, perss_addr.id, perss_addr.street, 
            perss_addr.building, empl.id, empl.ref_person, empl.ref_company, empl.hired, 
            empl.name, empl.ref_address, empl.registration, empl.street, empl.building 
            from person  
            join (

                select address.id, address.street, address.building 
                from address  
                where ((address.street like %(perss_addr_street_1)s and address.building = %(perss_addr_building_2)s) 
                or (address.building in (%(perss_addr_building_3)s,%(perss_addr_building_4)s)))

            ) as perss_addr on perss_addr.id = person.ref_address 

            left join (

                select employees.id, employees.ref_person, employees.ref_company, employees.hired, comp_employee.id, 
                comp_employee.name, comp_employee.ref_address, comp_employee.registration, 
                comp_employee.street, comp_employee.building 
                from employees  
                
                join (
                
                    select company.id, company.name, company.ref_address, company.registration, 
                    compony_addr.id, compony_addr.street, compony_addr.building 
                    from company  
                    
                    join (
                    
                        select address.id, address.street, address.building 
                        from address  
                        where (address.street like %(compony_addr_street_1)s and address.id = %(compony_addr_id_2)s)
                    
                    ) as compony_addr on compony_addr.id = company.ref_address 
                    
                    where (company.registration between %(comp_employee_registration_1)s and %(comp_employee_registration_2)s)
                
                ) as comp_employee on comp_employee.id = employees.ref_company

            ) as empl on empl.ref_person = person.id 
            where (person.id = %(person_id_1)s and person.name like %(person_name_2)s)   
            order by person.age desc
        """
        query = self.tables['person'].filter(id=1, name__like='Ant%%').join(
            Join(self.tables['address'], 'id', 'ref_address', 'perss_addr').filter(OR(AND(street__like='%%ушкина', building=10), building__in=[5,10]))
        ).join(
            LeftJoin(self.tables['employees'], 'ref_person', 'id', 'empl').select(['id', 'ref_person', 'ref_company', 'hired']).join(
                Join(self.tables['company'], 'id', 'ref_company', 'comp_employee').join(
                    Join(self.tables['address'], 'id', 'ref_address', 'compony_addr').filter(AND(street__like='%%эйкер', id=5))
                ).filter(registration__between=('2021-01-02', '2021-04-06'))
            )
        ).select(['id', 'name', 'age']).order_by(age=Ordering.DESC)
        logger.debug(query._query.get())
        len_fields1 = len(query._query.map_fields)
        logger.debug(query._query.map_fields)
        logger.debug(query._query.get())
        logger.debug(query._query.map_fields)
        len_fields2 = len(query._query.map_fields)
        self.assertEqual(len_fields1, len_fields2)
        res = query.get()
        logger.debug(res)
        self.assertEqual(len(res[0]), len_fields2)
        self.assertEqual(len(res), 1)
        
        
        """ 
            select person.id, person.name, person.age, address.id, address.street, address.building, 
            employees.id, employees.ref_person, employees.ref_company, employees.hired, emp_company.id, 
            emp_company.name, emp_company.ref_address, emp_company.registration, compony_addr.id, 
            compony_addr.street, compony_addr.building 
            from person  
            join (

                select address.id, address.street, address.building 
                from address  
                where ((address.street like %(address_street_1)s and address.building = %(address_building_2)s) 
                or address.building in (%(address_building_3)s,%(address_building_4)s))

            ) as address on address.id = person.ref_address 

            left join (

                select employees.id, employees.ref_person, employees.ref_company, employees.hired 
                from employees

            ) as employees on employees.ref_person = person.id 

            join (

                select company.id, company.name, company.ref_address, company.registration 
                from company  
                where company.registration between %(emp_company_registration_1)s and %(emp_company_registration_2)s

            ) as emp_company on emp_company.id = employees.ref_company 

            join (

                select address.id, address.street, address.building 
                from address  
                where (address.street like %(compony_addr_street_1)s and address.id = %(compony_addr_id_2)s)

            ) as compony_addr on compony_addr.id = emp_company.ref_address 

            where person.id = %(person_id_1)s and person.name like %(person_name_2)s   
            order by person.age desc
        """
        query = self.tables['person'].select(
            Field('person', 'id'), Field('person', 'name'), Field('person', 'age')
        ).join(
            Join(self.tables['address'], Field('address', 'id'), Field('person', 'ref_address')).filter(
                OR(
                    AND( Field('address', 'street').like('%%ушкина'), Field('address', 'building').equ(10) ),
                    Field('address', 'building').in_([5,10])
                )
            )
        ).join(
            LeftJoin(
                self.tables['employees'], Field('employees', 'ref_person'), Field('person', 'id')
            ).select(
                Field('employees', 'id'), Field('employees', 'ref_person'), Field('employees', 'ref_company'), Field('employees', 'hired')
            )
        ).join(
            Join(
                self.tables['company'], Field('company', 'id'), Field('employees', 'ref_company'), 'emp_company'
            ).filter( Field('company', 'registration').between(['2021-01-02', '2021-04-06']) )
        ).join(
            Join(
                self.tables['address'], Field('emp_company', 'ref_address'), Field('address', 'id'), 'compony_addr'
            ).filter(
                AND( Field('address', 'street').like('%%эйкер'), Field('address', 'id').equ(5) )
            )
        ).filter(
            Field('person', 'id').equ(1), Field('person', 'name').like('Ant%%')
        ).order_by(
            Field('person', 'age').desc()
        )
        logger.debug(query._query.get())
        len_fields1 = len(query._query.map_fields)
        logger.debug(query._query.map_fields)
        logger.debug(query._query.get())
        logger.debug(query._query.map_fields)
        len_fields2 = len(query._query.map_fields)
        self.assertEqual(len_fields1, len_fields2)
        res = query.get()
        logger.debug(res)
        self.assertEqual(len(res[0]), len_fields2)
        self.assertEqual(len(res), 1)
    
    def test_case_2(self):
        query = self.tables['person'].select(
            Concat(Field('person', 'name'), ' ', Field('person', 'age')).as_('simp')
        )
        self.assertEqual(query._query.get(), 'select concat(person.name, %(person_var_0)s, person.age) as simp from person')
        self.assertDictEqual(query._query.params, {'person_var_0': ' '})
        
        query = self.tables['person'].select(
            Substring(Field('person', 'name'), 1, 5).as_('simp')
        )
        self.assertEqual(query._query.get(), 'select substring(person.name, 1, 5) as simp from person')
        self.assertDictEqual(query._query.params, {})
        
        query = self.tables['person'].select(
            Replace(Field('person', 'name'), 'ton', 'ant').as_('simp')
        )
        self.assertEqual(query._query.get(), 'select replace(person.name, %(person_var_0)s, %(person_var_1)s) as simp from person')
        self.assertDictEqual(query._query.params, {'person_var_0': 'ton', 'person_var_1': 'ant'})
        
        query = self.tables['person'].select(
            Random().as_('simp')
        )
        self.assertEqual(query._query.get(), 'select random() as simp from person')
        self.assertDictEqual(query._query.params, {})
        
        query = self.tables['person'].select(
            Extract(Field('person', 'age'), 'day').as_('simp')
        )
        self.assertEqual(query._query.get(), 'select extract(day from person.age) as simp from person')
        self.assertDictEqual(query._query.params, {})
        
        query = self.tables['person'].select(
            Char(Field('person', 'age')).as_('simp')
        )
        self.assertEqual(query._query.get(), 'select to_char(person.age, %(person_var_0)s) as simp from person')
        self.assertDictEqual(query._query.params, {'person_var_0': 'DD-MM-YYYY HH24:MI:SS'})
        
        query = self.tables['person'].select(
            Interval(Field('person', 'age'), 4, 'day', '+').as_('simp')
        )
        self.assertEqual(query._query.get(), "select (person.age + interval '4 day') as simp from person")
        self.assertDictEqual(query._query.params, {})
        
        query = self.tables['person'].select(
            (Case()
            .when(Field('person', 'age')).equ(3).then('hello 3')
            .when(Field('person', 'age')).equ(5).then('hello 5')
            .elseif(Field('person', 'age')).as_('simp')
            )
        )
        self.assertEqual(query._query.get(), "select case when person.age = %(person_var_0)s then %(person_var_1)s when person.age = %(person_var_2)s then %(person_var_3)s else person.age end as simp from person")
        self.assertDictEqual(query._query.params, {'person_var_0': 3, 'person_var_1': 'hello 3', 'person_var_2': 5, 'person_var_3': 'hello 5'})
        
        query = self.tables['person'].select(
            Coalesce(Field('person', 'name'), 'ant', default='no').as_('simp')
        )
        self.assertEqual(query._query.get(), 'select coalesce(person.name, %(person_var_0)s, %(person_var_1)s) as simp from person')
        self.assertDictEqual(query._query.params, {'person_var_0': 'ant', 'person_var_1': 'no'})

if __name__ == "__main__":
    TestFunctions.start()