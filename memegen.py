from wand.image import Image
import random
from search import GoogleImageSearchDownloader
from config import *

def r_path(f):
    return "%s/%s" % (CONFIG_RES_DIR,f)

def d_path(f):
    return "%s/%s" % (CONFIG_DOWNLOAD_DIR, f)

def memegen_computer(meme_search):

    presenter = None

    if random.randrange(0,2) == 0:
        presenter = Image(filename=r_path('datboi.png'))
    else:
        presenter = Image(filename=r_path('sanic.png'))
        presenter.flop()
        presenter.transform(resize="50%")

    computer = Image(filename=r_path('retrocomputer.jpg'))

    image_file = GoogleImageSearchDownloader(meme_search,CONFIG_KEY,CONFIG_CX).execute(CONFIG_DOWNLOAD_DIR)

    meme = Image(filename=d_path(image_file))
    meme.resize(400,350)
    meme.rotate(-5)
    computer.composite(meme,250,130)
    computer.composite(presenter,500,500)
    computer.compression_quality = random.randrange(0,8)
    computer.convert('jpg')
    computer.save(filename='output.jpg')


memegen_computer('vaporwave')