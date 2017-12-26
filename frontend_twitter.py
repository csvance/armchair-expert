import re
from multiprocessing import Queue, Event
from time import sleep
from typing import List, Optional
import tweepy

from frontend_common import FrontendWorker, FrontendScheduler, FrontendReplyGenerator, Frontend
from twitter_config import SCREEN_NAME, TwitterApiCredentials


class TwitterReplyGenerator(FrontendReplyGenerator):
    def generate(self, message: str):
        reply = FrontendReplyGenerator.generate(self, message)

        if reply is None:
            return None

        # TODO: Validate URLs before sending to twitter instead of discarding them
        # Remove URL from tweets
        reply = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', reply)
        reply = reply.strip()
        if len(reply) > 0:
            return reply
        else:
            return None


class TwitterReplyListener(tweepy.StreamListener):
    def __init__(self, frontend_worker: 'TwitterWorker', credentials: TwitterApiCredentials, retweet_replies_to_ids):
        tweepy.StreamListener.__init__(self)
        self._worker = frontend_worker
        auth = tweepy.OAuthHandler(credentials.consumer_key, credentials.consumer_secret)
        auth.set_access_token(credentials.access_token, credentials.access_token_secret)
        self._api = tweepy.API(auth)
        self._retweet_replies_to_ids = retweet_replies_to_ids

    def on_direct_message(self, status):
        direct_message = status.direct_message
        if direct_message['sender']['screen_name'] == SCREEN_NAME:
            return
        print("Direct Message(%s): %s" % (direct_message['sender']['screen_name'], direct_message['text']))
        self._worker.send(direct_message['text'])
        reply = self._worker.recv()
        if reply is not None:
            print("Direct Message Reply: %s" % reply)
            try:
                self._api.send_direct_message(user_id=direct_message['sender']['id'], text=reply)
            except tweepy.error.TweepError as e:
                print("Error sending DM: %s" % e.reason)

    # Reply to any mentions of the bot
    def on_status(self, status):
        if status.author.screen_name != SCREEN_NAME:
            self._worker.send(status.text)
            print("Mention(%s): %s" % (status.author.screen_name, status.text))
            reply = self._worker.recv()
            if reply is not None:
                reply = ("@%s %s" % (status.author.screen_name, reply))[:280]
                print("Mention Reply: %s" % reply)
                try:
                    reply_status = self._api.update_status(reply, status.id)
                    if status.author.id in self._retweet_replies_to_ids:
                        self._api.retweet(reply_status.id)
                except tweepy.error.TweepError as e:
                    print("Error replying to mention: %s" % e.reason)

    def on_error(self, status):
        print(status)


class TwitterWorker(FrontendWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, shutdown_event: Event,
                 credentials: TwitterApiCredentials):
        FrontendWorker.__init__(self, name='TwitterWorker', read_queue=read_queue, write_queue=write_queue,
                                shutdown_event=shutdown_event)
        self._credentials = credentials
        self._user_stream = None
        self._api = None

    def _start_user_stream(self, retweet_replies_to_ids: List):
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

    def run(self):

        # Load API instance
        auth = self._auth()
        self._api = tweepy.API(auth)

        retweet_replies_to_ids = []
        for page in tweepy.Cursor(self._api.friends_ids, screen_name=SCREEN_NAME).pages():
            retweet_replies_to_ids.extend(page)

        # Start user stream handler
        self._start_user_stream(retweet_replies_to_ids)

        while True:
            sleep(0.2)

            if self._shutdown_event.is_set():
                self._stop_user_stream()
                return


class TwitterScheduler(FrontendScheduler):
    def __init__(self, shutdown_event: Event, credentials: TwitterApiCredentials):
        FrontendScheduler.__init__(self, shutdown_event)
        self._worker = TwitterWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                     shutdown_event=shutdown_event, credentials=credentials)


class TwitterFrontend(Frontend):
    def __init__(self, reply_generator: TwitterReplyGenerator, frontend_events: Event,
                 credentials: TwitterApiCredentials):
        Frontend.__init__(self, reply_generator=reply_generator, frontends_event=frontend_events)
        self._scheduler = TwitterScheduler(self._shutdown_event, credentials)
