import datetime
from typing import List

import tweepy
from sqlalchemy import Column, Integer, DateTime, BigInteger, String, BLOB
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from tweepy import Status

from config.twitter import TWITTER_TRAINING_DB_PATH, TwitterApiCredentials
from storage.storage_common import TrainingDataManager

Base = declarative_base()


class ScraperStatus(Base):
    __tablename__ = "scraperstatus"
    id = Column(Integer, index=True, primary_key=True)
    screen_name = Column(String, nullable=False)
    since_id = Column(BigInteger, nullable=False)


class Tweet(Base):
    __tablename__ = "tweet"
    id = Column(Integer, index=True, primary_key=True)
    tweet_id = Column(BigInteger, nullable=False, index=True, unique=True)
    user_id = Column(BigInteger, nullable=False)
    in_reply_to_status_id = Column(BigInteger)
    in_reply_to_user_id = Column(BigInteger)
    retweeted = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    trained = Column(Integer, nullable=False, default=0)
    text = Column(BLOB, nullable=False)

    def __repr__(self):
        return self.text.decode()


engine = create_engine('sqlite:///%s' % TWITTER_TRAINING_DB_PATH)
Base.metadata.create_all(engine)
session_factory = sessionmaker()
session_factory.configure(bind=engine)
Session = scoped_session(session_factory)


class TwitterTrainingDataManager(TrainingDataManager):
    def __init__(self):
        self._session = Session()

    def new_training_data(self) -> List[Tweet]:
        return self._session.query(Tweet).filter(Tweet.trained == 0).all()

    def mark_trained(self, data: List):
        for tweet in data:
            tweet.trained = 1
        self._session.commit()

    def untrain_all(self):
        for tweet in self._session.query(Tweet).filter(Tweet.trained == 1).all():
            tweet.trained = 0
        self._session.commit()

    def store(self, data: Status):
        status = data

        tweet = Tweet(tweet_id=status.id, user_id=status.user.id, in_reply_to_user_id=status.in_reply_to_user_id,
                      in_reply_to_status_id=status.in_reply_to_status_id, retweeted=int(status.retweeted),
                      timestamp=status.created_at, text=status.text.encode())
        self._session.add(tweet)
        self._session.commit()


class TwitterScraper(object):
    def __init__(self, credentials: TwitterApiCredentials, screen_name: str, since_id: int = None):
        self._credentials = credentials
        self.screen_name = screen_name
        self.session = Session()

        self.scraper_status = self.session.query(ScraperStatus).filter(
            ScraperStatus.screen_name == self.screen_name).first()
        if self.scraper_status is None:
            self.scraper_status = ScraperStatus(screen_name=screen_name, since_id=since_id)
            self.session.add(self.scraper_status)
            self.session.commit()

    def _auth(self):
        auth = tweepy.OAuthHandler(self._credentials.consumer_key, self._credentials.consumer_secret)
        auth.set_access_token(self._credentials.access_token, self._credentials.access_token_secret)

        return auth

    def scrape(self):

        auth = self._auth()
        api = tweepy.API(auth, wait_on_rate_limit=True)
        latest_tweet_id = self.scraper_status.since_id

        for tweet in tweepy.Cursor(api.user_timeline, screen_name=self.screen_name, count=100,
                                   lang="en", since_id=self.scraper_status.since_id).items():
            tweet_row = self.session.query(Tweet).filter(Tweet.tweet_id == tweet.id).first()
            if tweet_row is None:
                tweet_row = Tweet(tweet_id=tweet.id, user_id=tweet.author.id,
                                  in_reply_to_status_id=tweet.in_reply_to_status_id,
                                  in_reply_to_user_id=tweet.in_reply_to_user_id, retweeted=tweet.retweeted,
                                  timestamp=tweet.created_at, text=tweet.text.encode())
                self.session.add(tweet_row)

                # Normally it would be asinine to commit every insert, but we are rate limited by twitter anyway
                self.session.commit()

                if tweet_row.tweet_id > latest_tweet_id:
                    latest_tweet_id = tweet_row.tweet_id

        # Update scraper progress
        self.scraper_status.since_id = latest_tweet_id
        self.session.commit()
