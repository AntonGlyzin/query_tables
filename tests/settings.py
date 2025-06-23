import sys
from pathlib import Path
import logging
import unittest

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