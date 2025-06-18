
# Запросы в объектном стиле без моделей с поддержкой кеша данных.

Идея библиотеки заключается, чтобы освободить разработчика от написания моделей. Если вам нравятся запросы ORM от django или sqlalchemy, но при этом вам не хочется создваться модели, то данная библиотека может вам понравиться. Также в ней присутствует функция кеширования данных, что может ускорить выдачу результатов. На данный момент кеширование предусмотренно на уровне процесса. Библиотека расчитана на работу в синхронном и асинхронном режиме.

1. [Работа с таблицами](#работа-с-таблицами)
2. [Запросы к таблицам](#запросы-к-таблицам)
3. [Работа с кешем](#работа-с-кешем)
4. [Работа в асинхронном режиме](#работа-в-асинхронном-режиме)

## Работа с таблицами.

Представим у нас есть 4 таблицы:

Таблица `address`
| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id | INTEGER  | Ключ  |
|  street | TEXT  |  Улица |
|  building |  INTEGER |  Здание |


Таблица `company`
| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id | INTEGER  | Ключ  |
|  name | TEXT  |  Название |
| ref_address  | INTEGER  | Ссылка на адрес  |
| registration  |  TEXT |  Время в формате ИСО |


Таблица `employees`
| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id |  INTEGER |  Ключ |
| ref_person  | INTEGER  | Ссылка на персону  |
|  ref_company | INTEGER  | Ссылка на компанию  |
| hired  | INTEGER  |  Время в формате unix epoch |
|  dismissed | INTEGER  |  Время в формате unix epoch |


Таблица `person`
| Поле  |  Тип | Описание  |
| ------------ | ------------ | ------------ |
|  id |  INTEGER | Ключ  |
| login  | TEXT  | Логин  |
| name  |  TEXT |  Имя |
|   ref_address| INTEGER  |  Ссылка на адрес |
| age  |  INTEGER | Возраст  |

На данный момент библиотека поддерживает работу с двумя БД: `sqlite` и `postgres`.

Начать работу с `sqlite`. При создание экземпляра `Tables` будут получен доступ ко всем таблицам.
```python
from query_tables import Tables
from query_tables.db import SQLiteQuery

sqlite = SQLiteQuery(tests_dir / 'test_tables.db')
table = Tables(sqlite) # кеш отключен по умолчанию
# или так
table = Tables(sqlite, non_expired=True) # включен вечный кеш
# или так
table = Tables(sqlite, cache_ttl=300) # включен временный кеш на 300 сек.
```


Начать работу с `postgres` в многопоточном режиме. При создание экземпляра `Tables` будут получен доступ к таблицам из схемы `public`. При желание вы можете передать другую схему.
```python
from query_tables import Tables
from query_tables.db import DBConfigPg, PostgresQuery

postgres = PostgresQuery(
    DBConfigPg('localhost', 'test', 'postgres', 'postgres')
)
table = Tables(postgres) # кеш отключен по умолчанию
# или так
table = Tables(postgres, non_expired=True) # включен вечный кеш
# или так
table = Tables(postgres, cache_ttl=300) # включен временный кеш на 300 сек.

```

Если нужен доступ к ограниченному числу таблиц из БД `postgres`:
```python
table = Tables(postgres, tables=['operators', 'opright'], non_expired=True)
```

Параметры `Tables`:
- `db`: Объект для доступа к БД.
- `prefix_table`: Префикс таблиц которые нужно загрузить. По умолчанию - пустая строка.
- `tables`: Список подключаемых таблиц. По умолчанию - нет.
- `table_schema`: Схема данных. По умолчанию - 'public'.
- `cache_ttl`: Время кеширования данных. По умолчанию 0 секунд - кеширование отключено.
- `non_expired`: Вечный кеш без времени истечения. По умолчанию - выключен.
- `cache_maxsize`: Размер элементов в кеше.
- `cls_cache`: Пользовательская реализация кеша.
- `cls_query`: Пользовательская реализация запросов.

Когда у вас есть экземпляр `Tables`, то доступ к таблицам получается так:
```python
table['person']
```
        
## Запросы к таблицам.

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
[{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31}, {'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30}]
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

from query_tables.query import Join, LeftJoin

res = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(25, 31)).get()
print(res)
"""
[{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31, 'address.id': 1, 'address.street': 'Пушкина', 'address.building': 10}, {'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30, 'address.id': 2, 'address.street': 'Наумова', 'address.building': 33}]
"""

res = table['person'].filter(id=2).join(
    Join(table['address'], 'id', 'ref_address')
).join(
    LeftJoin(table['employees'], 'ref_person', 'id').select(['id', 'ref_person', 'ref_company', 'hired']).join(
        Join(table['company'], 'id', 'ref_company').join(
            Join(table['address'], 'id', 'ref_address', 'compony_addr')
        ).filter(registration__between=('2020-01-02', '2020-01-06'))
    )
).select(['id', 'name', 'age']).order_by(age='desc').get()
print(res)
"""
[{'address.id': 2, 'address.street': 'Наумова', 'address.building': 33, 'employees.id': 2, 'employees.ref_person': 2, 'employees.ref_company': 2, 'employees.hired': 1612588507, 'company.id': 2, 'company.name': 'Hex', 'company.ref_address': 4, 'company.registration': '2020-01-05', 'compony_addr.id': 4, 'compony_addr.street': 'Приморская', 'compony_addr.building': 8, 'person.id': 2, 'person.name': 'Anton 2', 'person.age': 30}]
"""
```

Для изменения метода фильтрации в условие можно добавить модификатор к параметру.

Есть следующие виды модификаторов для параметров в методе `filter`:

| Модификатор | Оператор sql | Пример значений |
| :-------- | :------- | :--------
| `ilike` | `ilike` |  `name__ilike='Ant%%'`|
| `like` | `like` |  `name__ilike='Ant%%'`|
| `in` | `in` |  `id__in=[1,2,3,4]`|
| `gt` | `>` |  `age__gt=3`|
| `gte` | `>=` |  `age__gte=3`|
| `lt` | `<` |  `age__lt=3`|
| `lte` | `<=` |  `age__lte=3`|
| `between` | `between` |  `age__between=(5,6)`|
| `isnull` | `is null` |  `name__isnull=None`|
| `isnotnull` | `is not null` |  `name__isnotnull=None`|
| `notequ` | `!=` |  `age__notequ=5`|

Для связывания таблиц используется две обертки:
```python
from query_tables.query import Join, LeftJoin
```
- `Join` - если вы уверены, что запись в join таблице должна быть, а если нет, то не выводить записи.
- `LeftJoin` - если нет записей в привязанной таблице, нужно вывести те записи, которые есть во внешней таблице.

Параметры для `Join`, `LeftJoin`:
- `join_table`: Таблица для join к другой таблице.
- `join_field`: Поле join таблицы.
- `ext_field`: Поле внешней таблицы.
- `table_alias`: Псевдоним для таблицы. Нужен когда 
    одна и таже таблицы соединяется больше одного раза.

Если ваш экземпляр `Tables` будет кешировать данные, то здесь нужно учитывать, когда и в какой момент нужно очищать кеш.
Предположим есть три запроса к БД, которые были созданы, но еще не выполнены. Пока данных нет, кеш пуст.
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
Выполним запросы. Получение данных из БД.
```python
res = query1.get()
res = query2.get()
res = query3.get()
```
Теперь в следующий раз, когда вы захотите получить данные, они будут браться из кеша.
```python
res = query1.get()
res = query2.get()
res = query3.get()
```

Но что если вы измените данные в таблице? Если это сделать вручную из БД, то данные у нас остануться не актуальными. Изменение данных в БД нужно проводить через экземпляр `Tables`.

```python
table['address'].insert([dict(
    street='123',
    building=777
)])
# или так
table['address'].filter(id=1).update(building=11)
# или так
table['address'].filter(id=1).delete()
```
В этом случае запросы `query1` и `query2` будут очищены, так как они используют таблицу, в которой произошли изменения.

Также заметьте, что для вставки записей в БД мы используем список словарей. Это значит, что можно вставлять больше одной записи в БД за раз.

Получаем снова данные из БД.
```python
res = query1.get()
res = query2.get()
```

Если вам не нужно изменять данные в БД, но вы желаете, чтобы запросы в кеше, которые используют таблицу `address` были очищены, то можно сделать так:
```python
table['address'].delete_cache_table()
```

Получаем снова данные из БД.
```python
res = query1.get()
res = query2.get()
```

## Работа с кешем.

Не пытайтесь получить доступ к кешу, если он у вас выключен. Это приведет к ошибке.

Давайте снова выполним запрос.
```python
query = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(30, 33), name__like='Anton%%').order_by(id='desc')
query.get() # получаем данные, но не сохраняем в переменную
res = query.cache.get() # берем их из кеша
print(res)
""" 
[{'person.id': 3, 'person.login': 'geg', 'person.name': 'Anton 3', 'person.ref_address': 3, 'person.age': 33, 'address.id': 3, 'address.street': 'Гринвич', 'address.building': 12}, {'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30, 'address.id': 2, 'address.street': 'Наумова', 'address.building': 33}, {'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31, 'address.id': 1, 'address.street': 'Пушкина', 'address.building': 10}]
"""
```

Теперь ваши данные находятся в кеше. Но что если вам нужно изменить эти данные?

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

Изменение данных через кеш не влечет за собой изменение данных в БД. В данном случае вы сами должны получить из БД данные и изменить их в кеше, чтобы не сбрасывать кеш.

Мы знаем, что запись с ИД 9 была изменена. Давайте ее получим: 
```python
query_9 = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(id=9)
res: list = query_9.get()
# Теперь обновим наш кеш из прошлого запроса.
query.cache.filter({'person.id': 9}).update(**res[0])
```

Но теперь запрос query_9 будет закеширован. Давай сброси кеш по конкретному запросу.
```python
query_9.delete_cache_query()
```

Для очищение всего кеша в экземпляре используйте:
```python
table.clear_cache()
```

## Работа в асинхронном режиме.

Принцип доступка к данным из кеша(по умолчанию) не изменился. Также без изменений остался конструктор запросов. Но запросы к БД будут выглядить по другому, к ним нужно добавить await.
Создаем экземпляр `TablesAsync`
```python
from query_tables import TablesAsync
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

table = TablesAsync(postgres_async, non_expired=True)
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

[![Python Software Foundation](https://raw.githubusercontent.com/psf/requests/main/ext/psf.png)](https://www.python.org/psf)