from googleapiclient.discovery import build
import urllib3
import shutil


class GoogleImages(object):
    def __init__(self,search,key,cx):
        self.query = search
        self.key = key
        self.cx = cx

    def execute(self,directory):
        service = build("customsearch", "v1",
                        developerKey=self.key)

        res = service.cse().list(
            q=self.query,
            cx=self.cx,
            num=1,
            searchType="image",
            safe='off'
        ).execute()

        http = urllib3.PoolManager()
        for item in res['items']:
            filename = item['link'].split("/")[-1]

            with http.request('GET', item['link'], preload_content=False) as r, open("%s/%s" % (directory,filename), 'wb') as out_file:
                shutil.copyfileobj(r, out_file)
            break

        return "%s/%s" % (directory,filename)