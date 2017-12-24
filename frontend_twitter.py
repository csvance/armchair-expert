from frontend_common import FrontendWorker, FrontendScheduler, FrontendReplyGenerator, Frontend
from multiprocessing import Queue, Event


class TwitterApiCredentials(object):
    def __init__(self, consumer_key: str, consumer_secret, access_token: str, access_token_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret


class TwitterReplyGenerator(FrontendReplyGenerator):
    def generate(self, message: str):
        return self.generate(message)


class TwitterWorker(FrontendWorker):
    def __init__(self, read_queue: Queue, write_queue : Queue, credentials: TwitterApiCredentials):
        FrontendWorker.__init__(self, name='TwitterWorker', read_queue=read_queue, write_queue=write_queue)
        self._credentials = credentials

    def run(self):
        pass


class TwitterScheduler(FrontendScheduler):
    def __init__(self, credentials: TwitterApiCredentials):
        FrontendScheduler.__init__(self)
        self._worker = TwitterWorker(read_queue=self._write_queue, write_queue=self._read_queue, credentials=credentials)


class TwitterFrontend(Frontend):
    def __init__(self, reply_generator: TwitterReplyGenerator, event: Event, credentials: TwitterApiCredentials):
        Frontend.__init__(self, reply_generator=reply_generator, event=event)
        self._scheduler = TwitterScheduler(credentials)
