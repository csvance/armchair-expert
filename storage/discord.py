import datetime
from typing import List, Tuple

from discord import Message

from sqlalchemy import Column, Integer, DateTime, BigInteger, BLOB
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from config.discord import DISCORD_TRAINING_DB_PATH
from common.discord import DiscordHelper
from storage.storage_common import TrainingDataManager

Base = declarative_base()


class DiscordMessage(Base):
    __tablename__ = "discordmessage"
    id = Column(Integer, index=True, primary_key=True)
    server_id = Column(BigInteger, nullable=True, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    trained = Column(Integer, nullable=False, default=0)
    text = Column(BLOB, nullable=False)

    def __repr__(self):
        return self.text.decode()


engine = create_engine('sqlite:///%s' % DISCORD_TRAINING_DB_PATH)
Base.metadata.create_all(engine)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)


class DiscordTrainingDataManager(TrainingDataManager):
    def __init__(self):
        TrainingDataManager.__init__(self, DiscordMessage)
        self._session = Session()

    def store(self, data: Message):
        message = data

        filtered_content = DiscordHelper.filter_content(message)

        server_id = int(message.server.id) if message.server is not None else None

        message = DiscordMessage(server_id=server_id, channel_id=int(message.channel.id),
                                 user_id=int(message.author.id), timestamp=message.timestamp,
                                 text=filtered_content.encode())
        self._session.add(message)
        self._session.commit()
