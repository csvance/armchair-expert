from typing import List, Tuple


class TrainingDataManager(object):
    def __init__(self, table_type):
        self._table_type = table_type
        self._session = None

    def new_training_data(self) -> List[Tuple[bytes]]:
        return self._session.query(self._table_type.text).filter(self._table_type.trained == 0).all()

    def all_training_data(self, limit: int = None) -> List[Tuple[bytes]]:
        if limit is None:
            return self._session.query(self._table_type.text).all()
        else:
            return self._session.query(self._table_type.text).limit(limit).all()

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

