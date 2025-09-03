from settings import logger, BaseTest
from query_tables.translate import Translate

class TestTranslate(BaseTest):
    
    @classmethod
    def filename_test(cls):
        return 'test_translete.log'
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
    
    def test_case_1(self):
        logger.info('1. Проверка класса локализации.')
        Translate._get_local = lambda s: ['en', '']
        t1 = Translate().func_gettext()
        self.assertEqual(t1('Произошла ошибка соединения с Redis: {}'), 'Redis connection error occurred: {}')
        self.assertEqual(t1('Текст которого нет.'), 'Текст которого нет.')
        
        Translate.instance = None
        Translate._get_local = lambda s: ['ru_RU', '']
        t2 = Translate().func_gettext()
        self.assertEqual(t2('Произошла ошибка соединения с Redis: {}'), 'Произошла ошибка соединения с Redis: {}')
        self.assertEqual(t2('Текст которого нет.'), 'Текст которого нет.')
        logger.info("-------------------------------------------------------")


if __name__ == "__main__":
    TestTranslate.start()