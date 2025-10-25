from typing import Optional, Dict, Tuple
from query_tables.query.base_query import BaseQuery


class Ordering(object):
    ASC = 'asc'
    DESC = 'desc'


class Condition(object):
    
    RELATION = ''
    
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.query: Optional[BaseQuery] = None
    
    def _set_query(self, query: BaseQuery) -> 'Condition':
        """Устанавливает запрос.

        Args:
            query (BaseQuery): Экземпляр запроса.
        """        
        self.query = query
        return self
    
    def _parse(self) -> Tuple[Dict, str]:
        """Условие для выборки.

        Returns:
            Tuple[Dict, str]: Параметры и sql.
        """        
        if self.kwargs:
            return self._get_filter()
        conds = []
        params = {}
        for cond in self.args:
            cond._set_query(self.query)
            param, sql = cond._parse()
            params.update(param)
            conds.append(sql)
        return params, '({})'.format(f' {self.RELATION} '.join(conds))
    
    def _get_filter(self) -> Tuple[Dict, str]:
        """Выдает параметры и часть sql запрос для фильтра."""
        return self.query._get_filter(self.RELATION, **self.kwargs)


class OR(Condition):
    
    RELATION = 'or'


class AND(Condition):
    
    RELATION = 'and'