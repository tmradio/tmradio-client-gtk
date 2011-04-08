# vim: set fileencoding=utf-8:

import feedparser
import sys
import threading
import time
import traceback
import urllib
import urllib2

import tmradio.log

BLOG_FEED = 'http://www.tmradio.net/blog/index.xml'
PODCAST_FEED = 'http://www.tmradio.net/podcast/index.xml'

def fetch(url):
    """Returns contents of a web resource."""
    try:
        res = urllib2.urlopen(urllib2.Request(url))
        if res is None:
            tmradio.log.error('Could not fetch %s' % url)
            return None
        return res.read()
    except Exception, e:
        tmradio.log.error('Could not fetch %s: %s' % (url, e))


class TwitterClientThread(threading.Thread):
    delay = 60 # min delay between updates, in seconds
    sleep_time = 0.1 # so low to minimize delays between quit request and thread shutdown

    def __init__(self, config):
        threading.Thread.__init__(self)
        self.config = config
        self.request_time = 0
        self.response_time = 0
        self.have_news = False
        self.shutting_down = False

        # Here we store all records.  Sometimes they vanish, this is a work-around.
        self.records = {}

    def run(self):
        tmradio.log.debug('%s started.' % self.__class__.__name__)
        while not self.shutting_down:
            if self.request_time > self.response_time:
                urls = self.get_url()
                if type(urls) != tuple and type(urls) != list:
                    urls = [urls]
                for url in urls:
                    tmradio.log.debug('Refreshing feed: ' + url)
                    try:
                        count = 0
                        for item in feedparser.parse(fetch(url))['items']:
                            self.records[item['link']] = self.prepare_feed_item(item)
                            count += 1
                        tmradio.log.debug('Found %u items in %s' % (count, url))
                        self.response_time = time.time() + self.delay
                        self.have_news = True
                    except Exception, e:
                        tmradio.log.error(u'Error updating feed: %s\n%s' % (e, traceback.format_exc(e)))
            time.sleep(self.sleep_time)
        tmradio.log.debug('%s over.' % self.__class__.__name__)

    def prepare_feed_item(self, item):
        item['timestamp'] = time.mktime(item['updated_parsed'])
        return item

    def update(self):
        """Requests an update."""
        self.request_time = time.time()

    def get_records(self, only_if_ready=True):
        """Returns all records sorted by date."""
        if only_if_ready and not self.have_news:
            return None
        self.have_news = False
        return sorted(self.records.values(), key=lambda item: self.get_item_date(item))

    def get_item_date(self, item):
        return item['updated_parsed']

    def get_url(self):
        return ('http://search.twitter.com/search.atom?q=' + urllib.quote(self.config.get_twitter_search()), BLOG_FEED)


class PodcastClientThread(TwitterClientThread):
    delay = 600 # 10 minutes between updates

    def get_url(self):
        return PODCAST_FEED


def Twitter(config):
    return TwitterClientThread(config)

def Podcast(config):
    return PodcastClientThread(config)
