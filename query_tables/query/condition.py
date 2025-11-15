from typing import Optional
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
    
    def _get(self) -> str:
        """Условие для выборки.

        Returns:
            Tuple[Dict, str]: Параметры и sql.
        """
        conds = [
            cond._set_query(self.query)._get()
            for cond in self.args
        ]
        if self.kwargs:
            res = self._get_filter()
            if not conds:
                return res
            conds.append(res)
        return '({})'.format(f' {self.RELATION} '.join(conds))
    
    def _get_filter(self) -> str:
        """Выдает параметры и часть sql запрос для фильтра."""
        return self.query._get_filter(self.RELATION, **self.kwargs)


class OR(Condition):
    
    RELATION = 'or'


class AND(Condition):
    
    RELATION = 'and'