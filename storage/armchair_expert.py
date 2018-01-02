from typing import Tuple, List

from sqlalchemy import Column, Integer
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from config.armchair_expert import STATISTICS_DB_PATH

Base = declarative_base()


class InputTextStat(Base):
    __tablename__ = "inputtextstat"
    id = Column(Integer, index=True, primary_key=True)
    length = Column(Integer, unique=True, nullable=False)
    count = Column(Integer, nullable=False)

    def __repr__(self):
        return "Input Text Length(%d): %d" % (self.length, self.count)


engine = create_engine('sqlite:///%s' % STATISTICS_DB_PATH)
Base.metadata.create_all(engine)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)


class InputTextStatManager(object):
    def __init__(self):
        self._session = Session()
        self._rows = {}
        rows = self._session.query(InputTextStat).all()
        for row in rows:
            self._rows[row.length] = row

    def log_length(self, length: int):
        if length not in self._rows:
            sentence_stat = InputTextStat(length=length, count=1)
            self._rows[length] = sentence_stat
            self._session.add(sentence_stat)
        else:
            self._rows[length].count += 1

    def commit(self):
        self._session.commit()

    def reset(self):
        self._session.execute("DELETE FROM inputtextstat")
        self.commit()
        self._rows = {}

    def probabilities(self) -> Tuple[List, List]:

        sigma = 0
        for key in self._rows:
            sigma += self._rows[key].count

        choices = []
        p_values = []

        for key in self._rows:
            choices.append(self._rows[key].length)
            p_values.append(self._rows[key].count / sigma)

        return choices, p_values
