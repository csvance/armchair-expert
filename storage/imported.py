from typing import List, Tuple

from sqlalchemy import Column, Integer, BLOB
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from config.armchair_expert import IMPORT_TRAINING_DB_PATH
from storage.storage_common import TrainingDataManager

Base = declarative_base()


class ImportedMessage(Base):
    __tablename__ = "importedmessage"
    id = Column(Integer, index=True, primary_key=True)
    trained = Column(Integer, nullable=False, default=0)
    text = Column(BLOB, nullable=False)


engine = create_engine('sqlite:///%s' % IMPORT_TRAINING_DB_PATH)
Base.metadata.create_all(engine)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)


class ImportTrainingDataManager(TrainingDataManager):
    def __init__(self):
        TrainingDataManager.__init__(self, ImportedMessage)
        self._session = Session()

    def store(self, data: str):
        message = data
        imported_message = ImportedMessage(text=message.encode())
        self._session.add(imported_message)
