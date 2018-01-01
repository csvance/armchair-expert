from typing import List, Tuple


class TrainingDataManager(object):
    def __init__(self, table_type):
        self._table_type = table_type
        self._session = None

    def new_training_data(self) -> List[Tuple[bytes]]:
        return self._session.query(self._table_type.text).filter(self._table_type.trained == 0).all()

    def all_training_data(self) -> List[Tuple[bytes]]:
        return self._session.query(self._table_type.text).all()

    def mark_trained(self):
        self._session.execute('UPDATE ' + self._table_type.__tablename__ + ' SET TRAINED = 1')

    def mark_untrained(self):
        self._session.execute('UPDATE ' + self._table_type.__tablename__ + ' SET TRAINED = 0')

    def store(self, data):
        pass
