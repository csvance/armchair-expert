import datetime
from typing import List

from discord import Message as DiscordMessage
from sqlalchemy import Column, Integer, DateTime, BigInteger, BLOB
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from config.discord import DISCORD_TRAINING_DB_PATH
from connectors.discord import DiscordClient
from storage.storage_common import TrainingDataManager

Base = declarative_base()


class Message(Base):
    __tablename__ = "message"
    id = Column(Integer, index=True, primary_key=True)
    server_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
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
        self._session = Session()

    def new_training_data(self) -> List[Message]:
        return self._session.query(Message).filter(Message.trained == 0).all()

    def mark_trained(self, data: List):
        for tweet in data:
            tweet.trained = 1
        self._session.commit()

    def untrain_all(self):
        for message in self._session.query(Message).filter(Message.trained == 1).all():
            message.trained = 0
        self._session.commit()

    def store(self, data: DiscordMessage):
        message = data

        filtered_content = DiscordClient.filter_content(message)
        message = Message(server_id=int(message.server.id), channel_id=int(message.channel.id),
                          user_id=int(message.author.id), timestamp=message.timestamp,
                          text=filtered_content.content.encode())
        self._session.add(message)
