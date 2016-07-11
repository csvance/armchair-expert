from wand.image import Image
import random
from search import GoogleImages
from config import *

def r_path(f):
    return "%s/%s" % (CONFIG_RES_DIR,f)

def d_path(f):
    return "%s/%s" % (CONFIG_DOWNLOAD_DIR, f)


class MemeScene(object):
    def __init__(self,background="background.png",resource="resource.png"):
        self.background = background
        self.resource = resource


class ComputerMemeScene(MemeScene):
    BACKGROUND = 'retrocomputer.jpg'

    def __init__(self,background=None,presenter=None,resource=None):
        super().__init__(background=r_path(ComputerMemeScene.BACKGROUND),resource=resource)

    def _select_presenter(self):
        #Select a presenter at random
        presenter = None

        if random.randrange(0, 2) == 0:
            presenter = Image(filename=r_path('datboi.png'))
        else:
            presenter = Image(filename=r_path('sanic.png'))
            presenter.flop()
            presenter.transform(resize="50%")

        return presenter

    def generate(self):

        presenter = self._select_presenter()

        computer = Image(filename=self.background)

        image_file = self.resource

        meme = Image(filename=image_file)
        meme.resize(400, 350)
        meme.rotate(-5)
        computer.composite(meme, 250, 130)
        computer.composite(presenter, 500, 500)
        computer.compression_quality = random.randrange(0, 8)
        computer.convert('jpg')
        computer.save(filename='output.jpg')

resource = GoogleImages('sanic', CONFIG_KEY, CONFIG_CX).execute(CONFIG_DOWNLOAD_DIR)
ComputerMemeScene(resource=resource).generate()

