
# Описание

Идея библиотеки заключается, чтобы освободить разработчика от написания моделей. Если вам нравятся запросы ORM от django или sqlalchemy, но при этом вам не хочется создавать модели, то данная библиотека может вам понравиться. Также в ней присутствует функция кеширования данных, что может ускорить выдачу результатов. На данный момент кеширование предусмотренно либо на уровне процесса, либо в редисе. Библиотека использует параметризированные запросы для защиты от sql инъекций. Она расчитана на работу в синхронном и асинхронном режиме. 

---
## Установка

```
pip install query-tables
```

---
## Работа с таблицами

Работа библиотеки будет продемонстрирована на этих таблицах:

Таблица `address`.

| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id | INTEGER  | Ключ  |
|  street | TEXT  |  Улица |
|  building |  INTEGER |  Здание |


Таблица `company`.

| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id | INTEGER  | Ключ  |
|  name | TEXT  |  Название |
| ref_address  | INTEGER  | Ссылка на адрес  |
| registration  |  TEXT |  Время в формате ИСО |


Таблица `employees`.

| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id |  INTEGER |  Ключ |
| ref_person  | INTEGER  | Ссылка на персону  |
|  ref_company | INTEGER  | Ссылка на компанию  |
| hired  | INTEGER  |  Время в формате unix epoch |
|  dismissed | INTEGER  |  Время в формате unix epoch |


Таблица `person`.

| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id |  INTEGER | Ключ  |
| login  | TEXT  | Логин  |
| name  |  TEXT |  Имя |
|   ref_address| INTEGER  |  Ссылка на адрес |
| age  |  INTEGER | Возраст  |

Библиотека поддерживает работу с двумя БД: `sqlite` и `postgres` в синхронном и асинхронном режиме.

Работа с `sqlite`. 
```python
from query_tables import Tables
from query_tables.db import SQLiteQuery

sqlite = SQLiteQuery(tests_dir / 'test_tables.db')
table = Tables(sqlite) # кеш отключен по умолчанию
# или так
table = Tables(sqlite, non_expired=True) # включен вечный кеш
# или так
table = Tables(sqlite, cache_ttl=300) # включен временный кеш на 300 сек.
# или так
connect = RedisConnect() # параметры соединения с редисом
redis_cache = RedisCache(connect)
tables = Tables(sqlite, cache=redis_cache)# кеш redis
```
При создание экземпляра `Tables` будут получен доступ ко всем таблицам.

Работа с `postgres` в многопоточном режиме. 
```python
from query_tables import Tables
from query_tables.db import DBConfigPg, PostgresQuery
from query_tables.cache import RedisCache, RedisConnect

postgres = PostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)
table = Tables(postgres) # кеш отключен по умолчанию
# или так
table = Tables(postgres, non_expired=True) # включен вечный кеш
# или так
table = Tables(postgres, cache_ttl=300) # включен временный кеш на 300 сек.
# или так
connect = RedisConnect() # параметры соединения с редисом
redis_cache = RedisCache(connect)
tables = Tables(postgres, cache=redis_cache)# кеш redis

```
При создание экземпляра `Tables` будет получен доступ к таблицам из схемы `public`. При желание вы можете передать другую схему.

Если нужен доступ к ограниченному числу таблиц из БД `postgres`:
```python
table = Tables(postgres, tables=['operators', 'opright'], non_expired=True)
```

Параметры `Tables`:
- `db`: Объект для доступа к БД.
- `prefix_table`: Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
- `tables`: Список подключаемых таблиц. По умолчанию - нет.
- `table_schema`: Схема данных. По умолчанию - `public`.
- `cache_ttl`: Время кеширования данных. По умолчанию 0 секунд - кеширование отключено.
- `non_expired`: Вечный кеш без времени истечения. По умолчанию - выключен.
- `cache_maxsize`: Размер элементов в кеше.
- `cache`: Пользовательская реализация кеша.

Параметры `RedisConnect`:
- `host`: Хост редиса. По умолчанию - `127.0.0.1`
- `user`: Пользователь. По умолчанию - нет.
- `password`: Пароль. По умолчанию - нет.
- `port`: Порт. По умолчанию - 6379.
- `db`: БД. По умолчанию - 0.

Параметры `DBConfigPg`:
- `host`: Хост БД. По умолчанию - `127.0.0.1`
- `database`: Название БД. По умолчанию - нет. 
- `user`: Пользователь. По умолчанию - нет.
- `password`: Пароль. По умолчанию - нет.
- `port`: Порт. По умолчанию - 5432
- `minconn`: Минимальное количество подключений в пуле - 1
- `maxconn`: Максимальное количество подключений в пуле - 10

Когда у вас есть экземпляр `Tables`, доступ к таблицам можно получить так:
```python
table['person']
```

---
## Запросы к таблицам

После того, как вы создали экземпляр `Tables`, вы можете получать доступ к данным из таблиц.

```python
res = table['person'].filter(id=2).get()
print(res)
"""
[{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30}]
"""

res = table['person'].filter(name__like='%%4').get()
print(res)
"""
[{'person.id': 4, 'person.login': 'ytr', 'person.name': 'Anton 4', 'person.ref_address': 2, 'person.age': 35}]
"""

res = table['person'].filter(age__in=[30]).get()
print(res)
"""
[{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30}]
"""

res = table['person'].filter(age__between=(30, 31)).order_by(id='asc').get()
print(res)
"""
[{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31}, 
{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30}]
"""

res = table['person'].filter(age__gte=35).get()
print(res)
"""
[{'person.id': 4, 'person.login': 'ytr', 'person.name': 'Anton 4', 'person.ref_address': 2, 'person.age': 35}]
"""

res = table['company'].filter(registration__between=('2020-01-04', '2020-01-05')).get()
print(res)
"""
[{'company.id': 2, 'company.name': 'Hex', 'company.ref_address': 4, 'company.registration': '2020-01-05'}]
"""

res = table['person'].order_by(id='desc').limit(1).get()
print(res)
"""
[{'person.id': 4, 'person.login': 'ytr', 'person.name': 'Anton 4', 'person.ref_address': 2, 'person.age': 35}]
"""
```

Подготовка параметров и sql запроса происходит отдельно друг от друга. Используется параметризированный запрос для защиты от sql инъекций.
Типы данных, которые выдает результирующая выборка зависит от библиотек и полей в `sqlite` и `postgres`.

Доступные методы для конструирования запроса из таблиы, к примеру `table['person']` в экземпляре `Tables`, а также из`Join` и `LeftJoin`:
- `select`: Для выбора выводимых полей.
- `join`: Объединение таблиц.
- `filter`: Правила фильтрации.
- `group_by`: Группировка.
- `having`: Фильтрация после группировки.
- `order_by`: Сортировка для полей.
- `limit`: Ограничения по количеству.
- `offset`: Смещение.

Данные методы не взаимодействют с БД, они только помогают собрать запрос.

---
## Выборка полей

За это отвечает метод `select`. Он может принимать в себя список полей текущей таблицы, либо экземпляры класса `Field`, либо функции.

Поля в списке должны относятся к таблице `person`.
```python
table['person'].select(['id', 'name', 'name'])
```
Или можно так:
```python
table['person'].select('id', 'name', 'name')
```

При использование класса `Field` поля могут указывать на другие таблицы.
```python
from query_tables.query import Field
table['person'].select(Field('person', 'id'), Field('person', 'name'), Field('person', 'name'))
```

Для отключения полей `address` из результирующей выборки используется метод `.select()`.
В данном случае будет сделана фильтрация по таблице `address`. В результирующем запросе у нас будут данные только по таблице `person`.
```python
table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address' ).filter(street__like='%%ушкина', building=10).select()
)
```

Также `select` принимает функции. Демонстрация функции `Concat`.
```python
from query_tables.query.functions import Concat
from query_tables.query import Field
table['person'].select(Concat(Field('person', 'name'), Field('person', 'age')).as_('simp'))
```

---
## Фильтрация данных

Фильтрация данных доступна из методов `filter` и `having`.
Для изменение метода фильтрации в условие можно добавить к модификатору `filter` и `having` параметр.

Есть следующие виды параметров в методе `filter` и `having`:

| Параметр | Оператор sql | Пример значений |
| :-------- | :------- | :--------
| `ilike` | `ilike` |  `name__ilike='Ant%%'`|
| `notilike` | `not ilike` |  `name__notilike='Ant%%'`|
| `like` | `like` |  `name__ilike='Ant%%'`|
| `notlike` | `not like` |  `name__notlike='Ant%%'`|
| `in` | `in` |  `id__in=[1,2,3,4]`|
| `notin` | `notin` |  `id__notin=[1,2,3,4]`|
| `gt` | `>` |  `age__gt=3`|
| `gte` | `>=` |  `age__gte=3`|
| `lt` | `<` |  `age__lt=3`|
| `lte` | `<=` |  `age__lte=3`|
| `between` | `between` |  `age__between=(5,6)`|
| `notbetween` | `notbetween` |  `age__notbetween=(5,6)`|
| `isnull` | `is null` |  `name__isnull=None`|
| `isnotnull` | `is not null` |  `name__isnotnull=None`|
| `notequ` | `!=` |  `age__notequ=5`|
| `iregex` | `~*` |  `name__iregex='\w+'`|
| `notiregex` | `!~*` |  `name__notiregex='\w+'`|
| `regex` | `~` |  `name__regex='\w+'`|
| `notregex` | `!~` |  `name__notregex='\w+'`|

Пример 1.
```python
res = table['company'].filter(registration__between=('2020-01-04', '2020-01-05')).get()
# res:
[{'company.id': 2, 'company.name': 'Hex', 'company.ref_address': 4, 'company.registration': '2020-01-05'}]
```

Если используется следующие связывания таблиц, то фильтрация для таблицы `address` будет выглядеть так:
```python
table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address' ).filter(street__like='%%ушкина', building=10)
)
```
Если попытаться отфильтровать данные `address` по таблицы `person`, то это выдаст ошибку. 
В таблице `person` не будет полей `street`, `building`. Эту проблему можно обойти, если использовать класс `Field`. 
Эта обертка укажет на какую таблицу ссылается поле.
```python
from query_tables.query import Join, Field
table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address' )
).filter(Field('address', 'street').like('%%ушкина'), Field('address', 'building').equ(10))
```
Параметры в фильтрации будут соединятся с помощью `and`, в том и другом случае.

Если нужно, чтобы параметры соединялись с помощью `or`, то нужно обернуть эти параметры в класс `OR`.
```python
from query_tables.query import Join, Field, OR
table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address' )
).filter(OR(Field('address', 'street').like('%%ушкина'), Field('address', 'building').equ(10)))
```

---
## Связывания таблиц

Для связывания таблиц используется две обертки:
```python
from query_tables.query import Join, LeftJoin
```
- `Join`: Если вам нужно выводит записи, только если они есть в join таблице.
- `LeftJoin`: Если вам нужно вывести записи, даже если их нет в join таблице.

Параметры для `Join`, `LeftJoin`:
- `join_table`: Таблица которая соединяется с другой таблицей.
- `join_field`: Поле join таблицы.
- `ext_field`: Поле внешней таблицы, с которой идет соединение.
- `table_alias`: Псевдоним для таблицы (*когда одна и та же таблицы соединяется больше одного раза*).

Можно соединять таблицы так:
```python
table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address' )
)
```
В этом случае важна последовательность полей `'id', 'ref_address'`. `id` поле из таблицы `address`, а поле `ref_address` из внешней таблице `person`.

Второй вариант соединения таблиц:
```python
from query_tables.query import Join, Field
table['person'].filter(id=2).join(
    Join(table['address'], Field('person', 'ref_address'), Field('address', 'id') )
)
```
Здесь не важна последовательность полей для передачи в `Join` и не важно есть ли у внешней таблице поле.

Сложный пример с глубокими `join` запросами:
```python
from query_tables.query import Join, LeftJoin, AND, OR, Ordering

query = table['person'].filter(id=1, name__like='Ant%%').join(
    Join(table['address'], 'id', 'ref_address', 'perss_addr').filter(OR(AND(street__like='%%ушкина', building=10), building__in=[5,10]))
).join(
    LeftJoin(table['employees'], 'ref_person', 'id', 'empl').select(['id', 'ref_person', 'ref_company', 'hired']).join(
        Join(table['company'], 'id', 'ref_company', 'comp_employee').join(
            Join(table['address'], 'id', 'ref_address', 'compony_addr').filter(AND(street__like='%%эйкер', id=5))
        ).filter(registration__between=('2021-01-02', '2021-04-06'))
    )
).select(['id', 'name', 'age']).order_by(age=Ordering.DESC)
res = query.get()


# res:
[
    {
        'person.id': 1, 
        'person.name': 'Anton 1', 
        'person.age': 31, 
        'perss_addr.id': 1, 
        'perss_addr.street': 'Пушкина', 
        'perss_addr.building': 10, 
        'empl.id': 1, 
        'empl.ref_person': 1, 
        'empl.ref_company': 1, 
        'empl.hired': 1644124507, 
        'empl.name': 'SD', 
        'empl.ref_address': 5, 
        'empl.registration': '2021-03-20', 
        'empl.street': 'Бэйкер', 
        'empl.building': 11
    }
]
```

Библиотека сгенерирует такой запрос:
```sql
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
```

Тот же запрос, только с `join` из таблице `table['person']` при помощи `Field`:
```python
from query_tables.query import Join, LeftJoin, AND, OR, Ordering, Field

query = table['person'].select(
    Field('person', 'id'), Field('person', 'name'), Field('person', 'age')
).join(
    Join(table['address'], Field('address', 'id'), Field('person', 'ref_address')).filter(
        OR(
            AND( Field('address', 'street').like('%%ушкина'), Field('address', 'building').equ(10) ),
            Field('address', 'building').in_([5,10])
        )
    )
).join(
    LeftJoin(
        table['employees'], Field('employees', 'ref_person'), Field('person', 'id')
    ).select(
        Field('employees', 'id'), Field('employees', 'ref_person'), Field('employees', 'ref_company'), Field('employees', 'hired')
    )
).join(
    Join(
        table['company'], Field('company', 'id'), Field('employees', 'ref_company'), 'emp_company'
    ).filter( Field('company', 'registration').between(['2021-01-02', '2021-04-06']) )
).join(
    Join(
        table['address'], Field('emp_company', 'ref_address'), Field('address', 'id'), 'compony_addr'
    ).filter(
        AND( Field('address', 'street').like('%%эйкер'), Field('address', 'id').equ(5) )
    )
).filter(
    Field('person', 'id').equ(1), Field('person', 'name').like('Ant%%')
).order_by(
    Field('person', 'age').desc()
)

res = query.get()

# res:
[
    {
        'person.id': 1, 
        'person.name': 'Anton 1', 
        'person.age': 31, 
        'address.id': 1, 
        'address.street': 'Пушкина', 
        'address.building': 10, 
        'employees.id': 1, 
        'employees.ref_person': 1, 
        'employees.ref_company': 1, 
        'employees.hired': 1644124507, 
        'emp_company.id': 1, 
        'emp_company.name': 'SD', 
        'emp_company.ref_address': 5, 
        'emp_company.registration': '2021-03-20', 
        'compony_addr.id': 5, 
        'compony_addr.street': 'Бэйкер', 
        'compony_addr.building': 11
    }
]
```

Такой код сгенерирует запрос:

```sql
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
```

---
## Группировка записей

Для группировки используется метод `group_by`, а для фильтрации используется `having` метод.
Простой запрос с группировкой и фильтром для одной таблицы: 

```python
query=table['company'].select('name', 'registration').group_by('name', 'registration').having(
        OR(registration__between=('2020-01-02', '2020-01-06'), name__like='%%ex')
    )
```

Сложный запрос с группировкой и фильтром:
```python
from query_tables.query import Join, AND, Field
from query_tables.query.functions import Upper, Max

query = table['employees'].select(
    Upper(Field('company', 'name')).as_('company_name'), Max(Field('person', 'age')).as_('person_age')
).join(
    Join(table['person'], Field('person', 'id'), Field('employees', 'ref_person')).select()
).join(
    Join(table['company'], Field('company', 'id'), Field('employees', 'ref_company')).select()
).filter(
    Field('employees', 'dismissed').is_null()
).group_by(
    Field('company', 'name')
).having(
    AND(Max(Field('person', 'age')).gt(30), Field('company', 'registration').gt('2021-03-2'))
).order_by(
    Field('company', 'name').desc()
)
res=query.get()

# res:
[{'employees.company_name': 'SD', 'employees.person_age': 31}]
```

Сгенерированный запрос:
```sql
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
```

---
## Функции

Все функции находятся в `query_tables.query.functions`. Это не полный перечень.
Но для корректного выполнения запроса с выбранной функцией БД должна ее поддерживать.

Пример использования `Case`:
```python
from query_tables.query import Field
from query_tables.query.functions import Case
table['person'].select(
    (Case()
    .when(Field('person', 'age')).equ(3).then(3)
    .when(Field('person', 'age')).equ(5).then(5)
    .elseif(Field('person', 'age')).as_('simp')
    )
)
```
```sql
select case 
    when person.age = %(person_var_0)s then %(person_var_1)s 
    when person.age = %(person_var_2)s then %(person_var_3)s 
    else person.age end as simp 
from person
```

Пример использования `Coalesce`:
```python
from query_tables.query import Field
from query_tables.query.functions import Coalesce
table['person'].select(
    Coalesce(Field('person', 'name'), 'ant', default='no').as_('simp')
)
```
```sql
select coalesce(person.name, %(person_var_0)s, %(person_var_1)s) as simp from person
```

Пример использования `Concat`:
```python
from query_tables.query import Field
from query_tables.query.functions import Concat
table['person'].select(
    Concat(Field('person', 'name'), ' ', Field('person', 'age')).as_('simp')
)
```
```sql
select concat(person.name, %(person_var_0)s, person.age) as simp from person'
```

---
## Запросы на изменение

Немного про методы изменения данных и их влияния на кеш.

Методы для изменения:
- `insert`: Вставка записей.
- `update`: Обновление. 
- `delete`: Удаление записей.

Когда в `Tables` включена функция кеширования, то данные будут в кеше до тех пор пока не будет выполнен методы для изменения данных. 
В этом случае все запросы, которые были связаны с изменяемой таблицей будут удалены из кеша.

Предположим есть три запроса к БД, которые были созданы, но еще не выполнены. Кеш пуст.
```python
query1 = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')

query2 = table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address')
).join(
    LeftJoin(table['employees'], 'ref_person', 'id').join(
        Join(table['company'], 'id', 'ref_company').join(
            Join(table['address'], 'id', 'ref_address', 'compony_addr')
        ).filter(registration__between=('2020-01-02', '2020-01-06'))
    )
).order_by(age='desc')

query3 = table['person'].filter(id=3).join(
    LeftJoin(table['employees'], 'ref_person', 'id')
)
```
Выполним запросы на получения данных из БД.
```python
res = query1.get()
res = query2.get()
res = query3.get()
```
Теперь данные будут браться из кеша.
```python
res = query1.get()
res = query2.get()
res = query3.get()
```

Изменение данных в БД нужно проводить через методы изменения данных по выбранной таблице. 
В следующем примере запросы на изменения коснутся таблицы `address`.
```python
# вставка записей в БД
table['address'].insert([dict(street='123', building=777)])
# или
table['address'].insert(street='123', building=777)
# обновление записей в БД
table['address'].filter(id=1).update(building=11)
# удаление записей из БД
table['address'].filter(id=1).delete()
```
В этом случае кеш по запросам `query1` и `query2` будут очищены, так как они используют таблицу `address`.
Для вставки записей может использоваться список словарей. Это дает возможность проводить массовую вставку записей за раз.

Получаем снова данные из БД.
```python
res = query1.get()
res = query2.get()
```

Если вам не нужно изменять данные в БД, но вы желаете, чтобы запросы в кеше были очищены, которые используют таблицу `address` , то можно сделать так:
```python
table['address'].delete_cache_table()
```

Получаем снова данные из БД.
```python
res = query1.get()
res = query2.get()
```

---
## Работа с кешем

> Не пытайтесь получить доступ к кешу, если он у вас выключен. Это приведет к ошибке.

Давайте снова выполним запрос.
```python
# сохраняем запрос
query = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
query.get() # получаем данные по запросу
res = query.cache.get() # потом можно взять из кеша
# либо
res = query.get() # если кеш включен
print(res)
""" 
[{'person.id': 3, 'person.login': 'geg', 'person.name': 'Anton 3', 'person.ref_address': 3, 'person.age': 33, 'address.id': 3, 'address.street': 'Гринвич', 'address.building': 12}, 
{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30, 'address.id': 2, 'address.street': 'Наумова', 'address.building': 33}, 
{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31, 'address.id': 1, 'address.street': 'Пушкина', 'address.building': 10}]
"""
```

Теперь ваши данные находятся в кеше.

```python
# Получить список данных по выборке. 
# В фильтре доступно только строгое равенство полей.
res = query.cache.filter({'person.id': 1}).get()
# Обновление данных по условию.
query.cache.filter({'person.id': 1}).update({'person.name': 'Tony 1', 'person.age': 32})
# Вставить новую запись в кеш.
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
# Удалить запись из кеша.
query.cache.filter({'person.id': 6}).delete()
```

Изменение данных через кеш не влечет за собой изменение данных в БД.

Мы знаем, что запись с ИД 9 была изменена сторонней программой. Эту запись можно самостоятельно получить и обновить свой кеш.
```python
query_9 = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(id=9)
res: list = query_9.get()
# Теперь обновим наш кеш из прошлого запроса.
query.cache.filter({'person.id': 9}).update(**res[0])
```

Запрос query_9 будет закеширован. Давай сброси кеш по конкретному запросу.
```python
query_9.delete_cache_query()
```

Для очищение всего кеша используйте:
```python
table.clear_cache()
```

---
## Работа с БД в асинхронном режиме

Конструктор запросов остался без изменений, но запросы к БД будут выглядить по другому, к ним нужно добавить `await`.

Создаем экземпляр `TablesAsync`.
```python
from query_tables import TablesAsync
from query_tables.cache import RedisConnect, AsyncRedisCache
from query_tables.db import (
    AsyncSQLiteQuery, 
    DBConfigPg, 
    AsyncPostgresQuery
)

sqlite_async = AsyncSQLiteQuery(tests_dir / 'test_db.db')

postgres_async = AsyncPostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)

table = TablesAsync(sqlite_async, non_expired=True)
await table.init()
# или так
table = TablesAsync(postgres_async, non_expired=True)
await table.init()
# или так
redis = AsyncRedisCache(RedisConnect())
table = TablesAsync(postgres_async, cache=redis)
await table.init()

```

Получаем данные и проводим изменения в БД.
```python
res1 = await table['person'].filter(id=2).get()
res2 = await table['person'].filter(id=4).join(
    Join(table['employees'], 'ref_person', 'id')
).get()

query = table['person'].filter(id=4).join(
    LeftJoin(table['employees'], 'ref_person', 'id')
)
res3 = await query.get()

await table['person'].insert([dict(
    login='tt',
    name='Ton',
    ref_address=1,
    age=55
)])

await table['person'].filter(id=9).update(login='ant2', age=32)
await table['person'].filter(id=9).delete()
```

---
## Асинхронный режим с удаленным кешем

Принцип доступка к данным из локального и удаленного кеша.

Создаем экземпляр `TablesAsync`.
```python
from query_tables import TablesAsync
from query_tables.cache import RedisConnect, AsyncRedisCache
from query_tables.db import (
    DBConfigPg, 
    AsyncPostgresQuery
)

postgres_async = AsyncPostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)

redis = AsyncRedisCache(RedisConnect())
table = TablesAsync(postgres_async, cache=redis)
await table.init()

```

Запросы на получения и изменения данных в кеше.
```python
# сохраняем запрос
query = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
await query.get() # получаем данные по запросу из БД
res = await query.cache.get() # потом можно взять из кеша
# либо
res = await query.get() # если кеш включен
print(res)
""" 
[{'person.id': 3, 'person.login': 'geg', 'person.name': 'Anton 3', 'person.ref_address': 3, 'person.age': 33, 'address.id': 3, 'address.street': 'Гринвич', 'address.building': 12}, 
{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30, 'address.id': 2, 'address.street': 'Наумова', 'address.building': 33}, 
{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31, 'address.id': 1, 'address.street': 'Пушкина', 'address.building': 10}]
"""

# обновляем запись в кеше по id
await query.cache.filter({'person.id': 1}).update({'person.name': 'Tony 1', 'person.age': 32})

# вставка новой записи в кеш
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

# удаление этой записи из кеша
await query.cache.filter({'person.id': 6}).delete()

# удаление данных по запросу из кеша
await query.delete_cache_query()

# очищение кеша
await table.clear_cache()
```

---
## Выполнение сырых SQL запросов

Это может понадобиться, потому как ваш запрос может быть большой или вы хотели бы получить данные не из кеша.
Для выполнение сырых sql запросов нужно выполнить метод `query` со строкой sql запроса.

```python
from query_tables import Tables
from query_tables.db import DBConfigPg, PostgresQuery
from query_tables.cache import RedisCache, RedisConnect

postgres = PostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)
connect = RedisConnect() # параметры соединения с редисом
redis_cache = RedisCache(connect)
tables = Tables(postgres, cache=redis_cache)# кеш redis

# получение списка кортежей
rows = tables.query('select * from person')
```

Если все же вы хотели бы его закешировать. 
```python
query = 'select * from person'
rows = tables.query(query, cache=True)
```
Это извлекает данные из БД и сразу их кеширует по sql запросу.

В следующий раз получаем данные из кеша:
```python
rows = tables.query(query, cache=True)
```

Предположим вы знаете, что в таблице были изменения, и вы хотели бы снова получить их из БД в кеш.
Для этого нужно установить флаг `delete_cache`. Это удалит старые данные из кеша.

```python
rows = tables.query(query, cache=True, delete_cache=True)
```

Если же нужно просто удалить данные из кеша по запросу. 
```python
rows = tables.query(query, delete_cache=True)
```

В следующий раз получаем данные из БД:
```python
rows = tables.query(query, cache=True)
```

Запрос с параметрами: 
```python
query = 'select * from person where id = %(id)s'
rows = tables.query(query, params={'id': 1})
```

Для асинхронного режима добавляем `await`:
```python
from query_tables import TablesAsync
from query_tables.cache import RedisConnect, AsyncRedisCache
from query_tables.db import (
    DBConfigPg, 
    AsyncPostgresQuery
)

postgres_async = AsyncPostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)

redis = AsyncRedisCache(RedisConnect())
table = TablesAsync(postgres_async, cache=redis)
await table.init()
query = 'select * from person'
rows = await tables.query(query)
```

---
## Внешние ссылки

- [Журнал изменений](https://github.com/AntonGlyzin/query_tables/releases)

- [На проект в Github](https://github.com/AntonGlyzin/query_tables)

- [Pypi](https://pypi.org/project/query-tables/)