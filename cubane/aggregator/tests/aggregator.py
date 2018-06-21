# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.aggregator.sources.aggregator import Aggregator
from cubane.aggregator.sources.twitter import Twitter
import itertools


class TwitterMock(Twitter):
    RECORDS = [
        {'id': 0, 'created_at': 'Thu Feb 18 07:27:02 +0000 2016', 'text': 'A'},
        {'id': 1, 'created_at': 'Thu Feb 18 07:27:02 +0000 2016', 'text': 'B'},
        {'id': 2, 'created_at': 'Thu Feb 18 07:27:02 +0000 2016', 'text': 'C'}
    ]


    def __init__(self, *args, **kwargs):
        super(TwitterMock, self).__init__(*args, **kwargs)
        self._fetched = False


    def get_raw_messages_request(self, url, timeout=None):
        if not self._fetched:
            self._fetched = True
            return {
                'statuses': self.RECORDS
            }
        else:
            return {'statuses': []}


    def get_tweet(self, tweet_id):
        return self.RECORDS[tweet_id]


class AggregatorTestCase(CubaneTestCase):
    def test_aggregator_should_yield_messages_from_all_sources_equally(self):
        twitter = TwitterMock({
            'consumer_key': '...',
            'consumer_secret': '...',
            'query': 'norfolk OR norfolkbroads'
        })

        # both sources should stop yielding after having yielded 3 messages each
        aggregator = Aggregator([twitter])
        messages = list(itertools.islice(aggregator.get_messages(0), 0, 10))
        text = [m.get('text') for m in messages]
        self.assertEqual(['A', 'B', 'C'], text)
