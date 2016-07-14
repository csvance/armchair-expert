from googleapiclient.discovery import build
import urllib3
import shutil
import random


class GoogleImages(object):
    def __init__(self, search, key, cx):
        self.query = search
        self.key = key
        self.cx = cx

    def execute(self, directory, rand=False, random_count=10):
        service = build("customsearch", "v1",
                        developerKey=self.key)

        num = 1 if not random else random_count

        res = service.cse().list(
            q=self.query,
            cx=self.cx,
            num=num,
            searchType="image",
            safe='off'
        ).execute()

        http = urllib3.PoolManager()

        index = random.randrange(0, random_count) if rand and len(res['items']) >= random_count else 0

        item = res['items'][index]
        filename = item['link'].split("/")[-1]
        with http.request('GET', item['link'], preload_content=False) as r, open("%s/%s" % (directory, filename),
                                                                                 'wb') as out_file:
            if r.status != 200:
                return None
            shutil.copyfileobj(r, out_file)

        return "%s/%s" % (directory, filename)
