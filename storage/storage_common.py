from typing import List, Tuple
from sqlalchemy import desc, asc


class TrainingDataManager(object):
    def __init__(self, table_type):
        self._table_type = table_type
        self._session = None

    def new_training_data(self) -> List[Tuple[bytes]]:
        return self._session.query(self._table_type.text).filter(self._table_type.trained == 0).all()

    def all_training_data(self, limit: int = None, order_by: str = None, order='desc') -> List[Tuple[bytes]]:
        query = self._session.query(self._table_type.text)
        if order_by and order == 'desc':
            query = query.order_by(desc(order_by))
        elif order_by and order == 'asc':
            query = query.order_by(asc(order_by))
        if limit:
            query = query.limit(limit)
        return query.all()

    def mark_trained(self):
        self._session.execute('UPDATE ' + self._table_type.__tablename__ + ' SET TRAINED = 1')
        self._session.commit()

    def mark_untrained(self):
        self._session.execute('UPDATE ' + self._table_type.__tablename__ + ' SET TRAINED = 0')
        self._session.commit()

    def commit(self):
        self._session.commit()

    def store(self, data):
        pass

