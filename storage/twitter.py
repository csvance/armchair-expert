import datetime
from typing import List, Tuple

import tweepy
from sqlalchemy import Column, Integer, DateTime, BigInteger, String, BLOB
from sqlalchemy import func
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
    status_id = Column(BigInteger, nullable=False, index=True, unique=True)
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
        TrainingDataManager.__init__(self, Tweet)
        self._session = Session()

    def store(self, data: Status):
        status = data

        tweet = self._session.query(Tweet).filter(Tweet.status_id == status.id).first()
        if tweet is None:
            tweet = Tweet(status_id=status.id, user_id=status.user.id, in_reply_to_user_id=status.in_reply_to_user_id,
                          in_reply_to_status_id=status.in_reply_to_status_id, retweeted=int(status.retweeted),
                          timestamp=status.created_at, text=status.text.encode())
            self._session.add(tweet)
            self._session.commit()


class TwitterScraper(object):
    def __init__(self, credentials: TwitterApiCredentials, screen_name: str):
        self._credentials = credentials
        self.screen_name = screen_name
        self.session = Session()

        row = self.session.query(func.max(Tweet.status_id)).first()
        if row is not None:
            since_id = row[0] if row[0] is not None else 0
        else:
            since_id = 0

        self._latest_tweet_processed_id = since_id

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

    def scrape(self, wait_on_rate_limit=True, learn_retweets=False):

        auth = self._auth()
        api = tweepy.API(auth, wait_on_rate_limit=wait_on_rate_limit)

        if self.scraper_status.since_id == 0:
            tweets = tweepy.Cursor(api.user_timeline, screen_name=self.screen_name, count=100,
                                   lang="en").items()
        else:
            tweets = tweepy.Cursor(api.user_timeline, screen_name=self.screen_name, count=100,
                                   lang="en", since_id=self.scraper_status.since_id).items()

        for tweet in tweets:
            tweet_row = self.session.query(Tweet).filter(Tweet.status_id == tweet.id).first()
            if tweet_row is None:
                if not tweet.retweeted or (tweet.retweeted and learn_retweets):
                    tweet_row = Tweet(status_id=tweet.id, user_id=tweet.author.id,
                                      in_reply_to_status_id=tweet.in_reply_to_status_id,
                                      in_reply_to_user_id=tweet.in_reply_to_user_id, retweeted=tweet.retweeted,
                                      timestamp=tweet.created_at, text=tweet.text.encode())
                    self.session.add(tweet_row)

                # Store the highest ID so we can set it to since_id later
                if self._latest_tweet_processed_id is None or tweet.id > self._latest_tweet_processed_id:
                    self._latest_tweet_processed_id = tweet.id

                # Normally it would be asinine to commit every insert, but we are rate limited by twitter anyway
                self.session.commit()

        # Complete scraper progress
        self.scraper_status.since_id = self._latest_tweet_processed_id
        self.session.commit()
