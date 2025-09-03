import gettext
import locale
from pathlib import Path


class Translate(object):
    
    instance = None
    
    def __new__(cls):
        if cls.instance:
            return cls.instance
        cls.instance = super().__new__(cls)
        return cls.instance
    
    def __init__(self):
        self.lang = None
        sys_lang = self._get_local()
        if sys_lang[0] != 'ru_RU':
            path = Path(__file__).parent / 'locale'
            self.lang = gettext.translation(
                    'query_tables', localedir=str(path), languages=['en']
                )
    
    def func_gettext(self):
        if self.lang:
            return self._gettext
        else:
            return lambda s: s
    
    def _gettext(self, msg: str):
        try:
            return self.lang.gettext(msg)
        except Exception:
            return msg
    
    @classmethod
    def _get_local(cls):
        return locale.getdefaultlocale()


_ = Translate().func_gettext()