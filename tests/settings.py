import sys
from pathlib import Path
import logging
import unittest
import psycopg2

path = Path(__file__)
tests_dir = path.parent
sys.path.insert(0, str(tests_dir.parent))


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('aiosqlite').setLevel(logging.INFO)

# Логгер в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Логгер в файл
file_handler = logging.FileHandler(tests_dir / 'unit_tests.log', mode='w', encoding='utf8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Параметры подключения к серверу PostgreQL
DB_NAME = 'query_tables'
USERNAME = 'postgres' # Обычно postgres
PASSWORD = 'postgres'
HOST = 'localhost'
PORT = '5432'

#python -m unittest discover -s ./tests
class BaseTest(unittest.TestCase):
    
    @classmethod
    def filename_test(cls):
        return ''
    
    @classmethod
    def start(cls, log: bool = False):
        if not log:
            unittest.main()
        else:
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromTestCase(cls)
            with open(tests_dir / cls.filename_test(), 'w') as f:
                runner = unittest.TextTestRunner(stream=f, verbosity=2)
                runner.run(suite)
    
    @classmethod
    def setUpClass(cls):
        logger.info('======================================================================')
        logger.info(f'Выполнение тестов для {cls.__name__}.')
        logger.info('======================================================================')
        
    @classmethod
    def tearDownClass(cls):
        ...
        
    def setUp(self):
        "Подготовка перед каждым тестовым методом."
        ...
    
    def tearDown(self):
        "Очистка после каждого тестового метода."
        ...
    
    @classmethod
    def _create_db_ifnotexist_postgres(cls):
        
        try:
            conn = psycopg2.connect(
                dbname='postgres',  # По умолчанию используем базу данных postgres
                user=USERNAME,
                password=PASSWORD,
                host=HOST,
                port=PORT
            )
            conn.autocommit = True
            cur = conn.cursor()
            check_query = f"""
                SELECT EXISTS (
                    SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = '{DB_NAME.lower()}');
            """
            cur.execute(check_query)
            exists = cur.fetchone()[0]
            if not exists:
                logger.info(f"База данных {DB_NAME} не существует. Создаем...")
                create_query = f"CREATE DATABASE {DB_NAME};"
                cur.execute(create_query)
                logger.info("Создание базы данных успешно.")
        except Exception as e:
            logger.info(f"Произошла ошибка: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()