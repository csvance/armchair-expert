from storage.twitter import TwitterScraper
from config.twitter import TWITTER_CREDENTIALS, TWITTER_LEARN_FROM_USER

scraper = TwitterScraper(TWITTER_CREDENTIALS, TWITTER_LEARN_FROM_USER)
scraper.scrape()
