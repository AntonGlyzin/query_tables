
# Описание

Идея библиотеки заключается, чтобы освободить разработчика от написания моделей. Если вам нравятся запросы ORM от django или sqlalchemy, но при этом вам не хочется создавать модели, то данная библиотека может вам понравиться. Также в ней присутствует функция кеширования данных, что может ускорить выдачу результатов. На данный момент кеширование предусмотренно либо на уровне процесса, либо в редисе. Библиотека расчитана на работу в синхронном и асинхронном режиме.

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

Библиотека поддерживает работу с двумя БД: `sqlite` и `postgres`.

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

Когда создается экземпляр `Tables` с использованием кеша на основе `redis` или другого удаленного кеша, то в этот момент структуры таблиц сохраняются в кеш. При повторном создание экземпляра `Tables` все таблицы будут взяты из кеша. Это может понадобиться, если вы работаете с веб-сервером. 

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

from query_tables.query import Join, LeftJoin

res = table['person'].join(
    Join(table['address'], 'id', 'ref_address')
).filter(age__between=(25, 31)).get()
print(res)
"""
[{'person.id': 1, 'person.login': 'ant', 'person.name': 'Anton 1', 'person.ref_address': 1, 'person.age': 31, 'address.id': 1, 'address.street': 'Пушкина', 'address.building': 10}, 
{'person.id': 2, 'person.login': 'mix', 'person.name': 'Anton 2', 'person.ref_address': 2, 'person.age': 30, 'address.id': 2, 'address.street': 'Наумова', 'address.building': 33}]
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


Доступные методы для конструирования запроса SQL из таблицы `table['person']`, а также из`Join` и `LeftJoin`. Данные методы не взаимодействют с БД, они только помогают собрать запрос:
- `select`: Для выбора выводимых полей.
- `join`: Объединение таблиц.
- `filter`: Правила фильтрации.
- `order_by`: Сортировка для полей.
- `limit`: Ограничения по количеству.

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
- `table_alias`: Псевдоним для таблицы (*когда 
    одна и та же таблицы соединяется больше одного раза*).

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

Но что если вы измените данные в таблице? Если это сделать вручную из БД, то данные у нас остануться не актуальными. Изменение данных в БД нужно проводить через методы изменения данных по выбранной таблице.

```python
# вставка записей в БД
table['address'].insert([dict(
    street='123',
    building=777
)])
# обновление записей в БД
table['address'].filter(id=1).update(building=11)
# удаление записей из БД
table['address'].filter(id=1).delete()
```
В этом случае кеш запросов `query1` и `query2` будут очищены, так как они используют таблицу, в которой произошли изменения.
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

Теперь ваши данные находятся в кеше. Но что если вам нужно получить или изменить эти данные с учетов фильтрации кеша?

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

Конструктор запросов остался без изменений. Но запросы к БД будут выглядить по другому, к ним нужно добавить `await`.

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
Принцип доступка к данным из локального кеша, который находится в памяти процесса, не изменился. Но получение доступка к удаленному кешу был изменен.

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
## Выполнение сырых SQL запросов.

Возможно ваш запрос большой или вы хотели бы получить данные не из кеша.
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

Если все же вы хотели бы его закешировать. Получаем данные из БД и сразу их кешируем по sql запросу.
```python
query = 'select * from person'
rows = tables.query(query, cache=True)
```

В следующий раз получаем данные из кеша:
```python
rows = tables.query(query, cache=True)
```

Предположим вы знаете, что в таблице были изменены данные, и вы хотели бы снова получить их из БД в кеш:

```python
rows = tables.query(query, cache=True, is_new_data=True)
```
Будет обновлен кеш по запросу и получены новые данные.

Для асинхронного режима:
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