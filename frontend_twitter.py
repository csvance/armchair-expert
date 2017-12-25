from multiprocessing import Queue, Event

import tweepy
import re
from frontend_common import FrontendWorker, FrontendScheduler, FrontendReplyGenerator, Frontend
from twitter_config import ALWAYS_REPLY_USER, SCREEN_NAME, TwitterApiCredentials, ALWAYS_REPLY_DATETIME_FILE
from time import sleep
import datetime
import dateutil.parser


class TwitterReplyGenerator(FrontendReplyGenerator):
    def generate(self, message: str):
        reply = FrontendReplyGenerator.generate(self, message)

        # TODO: Validate URLs before sending to twitter instead of discarding them
        # Remove URL from tweets
        reply = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', reply)
        reply = reply.strip()
        if len(reply) > 0:
            return reply
        else:
            return None


class TwitterReplyListener(tweepy.StreamListener):
    def __init__(self, frontend_worker: 'TwitterWorker', credentials: TwitterApiCredentials):
        tweepy.StreamListener.__init__(self)
        self._worker = frontend_worker
        auth = tweepy.OAuthHandler(credentials.consumer_key, credentials.consumer_secret)
        auth.set_access_token(credentials.access_token, credentials.access_token_secret)
        self._api = tweepy.API(auth)

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
            print("Mention(%s): %s" % (status.author.screen_name,status.text))
            reply = self._worker.recv()
            if reply is not None:
                reply = ("@%s %s" % (status.author.screen_name, reply))[:280]
                print("Mention Reply: %s" % reply)
                try:
                    self._api.update_status(reply, status.id)
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
        self._reply_stream = None
        self._api = None

    def run(self):
        auth = tweepy.OAuthHandler(self._credentials.consumer_key, self._credentials.consumer_secret)
        auth.set_access_token(self._credentials.access_token, self._credentials.access_token_secret)
        self._reply_stream = tweepy.Stream(auth, TwitterReplyListener(self, self._credentials))
        self._api = tweepy.API(auth)
        users = self._api.lookup_users(screen_names=[ALWAYS_REPLY_USER])
        always_reply_id = users[0].id_str

        self._reply_stream.userstream(async=True)

        sleep_time = 0.1
        counter = 300.

        try:
            last_tweet_created_datetime = dateutil.parser.parse(open(ALWAYS_REPLY_DATETIME_FILE, 'r').read())
        except FileNotFoundError:
            last_tweet_created_datetime = datetime.datetime.now()

        while True:
            sleep(sleep_time)
            counter += sleep_time

            if self._shutdown_event.is_set():
                self._reply_stream.disconnect()
                # TODO: Fix replace this with SQLite based system where multiple users can be followed and tracked
                open(ALWAYS_REPLY_DATETIME_FILE, 'w').write(last_tweet_created_datetime.isoformat())
                return

            if counter >= 300.:
                statuses = self._api.user_timeline(id=always_reply_id, count=5)
                for status in statuses:
                    if status.created_at <= last_tweet_created_datetime:
                        continue
                    if status.retweeted:
                        continue

                    print("New Tweet: %s" % status.text)

                    if status.author.screen_name != SCREEN_NAME:
                        self.send(status.text)
                        reply = self.recv()
                        if reply is not None:
                            reply = ("@%s %s" % (status.author.screen_name, reply))[:280]
                            print("Replying: %s" % reply)
                            reply_status = self._api.update_status(reply, status.id)
                            try:
                                self._api.retweet(reply_status.id)
                            except tweepy.error.TweepError as e:
                                print("Error replying to tweet: %s" % e.reason)

                    last_tweet_created_datetime = status.created_at
                counter = 0.


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
