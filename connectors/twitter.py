import logging
import re
from datetime import datetime
from multiprocessing import Queue, Event
from threading import Thread
from time import sleep
from typing import List
from typing import Optional

import tweepy
from spacy.tokens import Doc

from config.twitter import *
from connectors.connector_common import ConnectorWorker, ConnectorScheduler, ConnectorReplyGenerator, Connector, ConnectorRecvMessage
from storage.twitter import TwitterTrainingDataManager, TwitterScraper


class TwitterReplyGenerator(ConnectorReplyGenerator):
    def generate(self, message: str, doc: Doc = None) -> Optional[str]:
        reply = ConnectorReplyGenerator.generate(self, message, doc)

        if reply is None:
            return None

        # TODO: Validate URLs before sending to twitter instead of discarding them
        if TWITTER_REMOVE_URL:
            # Remove URLs
            reply = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', reply)
            reply = reply.strip()

        if len(reply) > 0:
            return reply
        else:
            return None


class TwitterReplyListener(tweepy.StreamListener):
    def __init__(self, frontend_worker: 'TwitterWorker', credentials: TwitterApiCredentials,
                 retweet_replies_to_ids: List[int]):
        tweepy.StreamListener.__init__(self)
        self._worker = frontend_worker
        auth = tweepy.OAuthHandler(credentials.consumer_key, credentials.consumer_secret)
        auth.set_access_token(credentials.access_token, credentials.access_token_secret)
        self._api = tweepy.API(auth)
        self._retweet_replies_to_ids = retweet_replies_to_ids
        self._logger = logging.getLogger(self.__class__.__name__)

    def on_direct_message(self, status):
        direct_message = status.direct_message
        if direct_message['sender']['screen_name'] == TWITTER_SCREEN_NAME:
            return
        self._logger.debug("Direct Message(%s): %s" % (direct_message['sender']['screen_name'], direct_message['text']))

        learn = False
        if TWITTER_LEARN_TIMELINE:
            TwitterTrainingDataManager().store(status)
            learn = True

        # real-time learning
        if learn:
            self._worker.send(ConnectorRecvMessage(direct_message['text'], learn=True, reply=False))
            self._worker.recv()

        self._worker.send(ConnectorRecvMessage(direct_message['text']))
        reply = self._worker.recv()
        if reply is not None:
            self._logger.debug("Direct Message Reply: %s" % reply)
            try:
                self._api.send_direct_message(user_id=direct_message['sender']['id'], text=reply)
            except tweepy.error.TweepError as e:
                self._logger.error("Error sending DM: %s" % e.reason)


    def on_status(self, status):
        # Don't process messages from ourselves
        if status.author.screen_name == TWITTER_SCREEN_NAME:
            return

        learn = False
        if TWITTER_LEARN_TIMELINE:
            TwitterTrainingDataManager().store(status)
            learn = True

        # real-time learning
        if learn:
            self._worker.send(ConnectorRecvMessage(status.text, learn=True, reply=False))
            self._worker.recv()

        if (TWITTER_REPLY_MENTIONS and status.in_reply_to_screen_name == TWITTER_SCREEN_NAME) \
                or TWITTER_REPLY_TIMELINE:
            self._worker.send(ConnectorRecvMessage(status.text))
            self._logger.debug("Mention(%s): %s" % (status.author.screen_name, status.text))
            reply = self._worker.recv()
            if reply is not None:
                reply = ("@%s %s" % (status.author.screen_name, reply))[:280]
                self._logger.debug("Mention Reply: %s" % reply)
                try:
                    reply_status = self._api.update_status(reply, status.id)
                    if status.author.id in self._retweet_replies_to_ids:
                        self._api.retweet(reply_status.id)
                except tweepy.error.TweepError as e:
                    self._logger.error("Error replying to mention: %s" % e.reason)


    def on_error(self, status):
        print(status)


class TwitterWorker(ConnectorWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, shutdown_event: Event,
                 credentials: TwitterApiCredentials):
        ConnectorWorker.__init__(self, name='TwitterWorker', read_queue=read_queue, write_queue=write_queue,
                                 shutdown_event=shutdown_event)
        self._credentials = credentials
        self._user_stream = None
        self._api = None
        self._scraper = None
        self._scraper_thread = None
        self._logger = None

    def _start_user_stream(self, retweet_replies_to_ids: List[int]):
        auth = self._auth()
        # Setup reply stream for handling mentions and DM
        self._user_stream = tweepy.Stream(auth, TwitterReplyListener(self, self._credentials, retweet_replies_to_ids))
        self._user_stream.userstream(async=True)

    def _stop_user_stream(self):
        self._user_stream.disconnect()

    def _auth(self):
        auth = tweepy.OAuthHandler(self._credentials.consumer_key, self._credentials.consumer_secret)
        auth.set_access_token(self._credentials.access_token, self._credentials.access_token_secret)

        return auth

    def _scraper_thread_main(self):

        # Load Scraper
        self._scraper = TwitterScraper(self._credentials, TWITTER_LEARN_FROM_USER)
        # Initial Scrape
        self._scraper.scrape(learn_retweets=TWITTER_LEARN_FROM_USER_RETWEETS)

        last_scrape = datetime.now()
        while True:
            sleep(1)
            if (datetime.now() - last_scrape).total_seconds() >= TWITTER_SCRAPE_FREQUENCY:
                self._logger.info("Running scraper.")
                self._scraper.scrape(learn_retweets=TWITTER_LEARN_FROM_USER_RETWEETS)
                self._logger.info("Scraper done.")
                last_scrape = datetime.now()

    def run(self):

        self._logger = logging.getLogger(self.__class__.__name__)

        # Load API instance
        auth = self._auth()
        self._api = tweepy.API(auth)

        # Get user id's which we will always reply to
        retweet_replies_to_ids = []
        for page in tweepy.Cursor(self._api.friends_ids, screen_name=TWITTER_SCREEN_NAME).pages():
            retweet_replies_to_ids.extend(page)

        # Start user stream handler
        self._start_user_stream(retweet_replies_to_ids)

        if TWITTER_LEARN_FROM_USER is not None:
            # Run scraper thread
            self._scraper_thread = Thread(target=self._scraper_thread_main)
            self._scraper_thread.start()

        while True:
            sleep(0.2)

            if self._shutdown_event.is_set():
                self._logger.info("Got shutdown signal.")
                self._stop_user_stream()
                return


class TwitterScheduler(ConnectorScheduler):
    def __init__(self, shutdown_event: Event, credentials: TwitterApiCredentials):
        ConnectorScheduler.__init__(self, shutdown_event)
        self._worker = TwitterWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                     shutdown_event=shutdown_event, credentials=credentials)


class TwitterFrontend(Connector):
    def __init__(self, reply_generator: TwitterReplyGenerator, connectors_event: Event,
                 credentials: TwitterApiCredentials):
        Connector.__init__(self, reply_generator=reply_generator, connectors_event=connectors_event)
        self._scheduler = TwitterScheduler(self._shutdown_event, credentials)
