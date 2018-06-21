# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.aggregator.sources.aggregator import Aggregator
from cubane.aggregator.sources.twitter import Twitter
import time
import itertools


class AggregatorTwitterTestCase(CubaneTestCase):
    def test_should_deliver_unified_messages(self):
        self.assertEqual(
            [
                {
                    'entities': {},
                    'profile_picture': None,
                    'link': 'https://twitter.com/statuses/700219960891727872',
                    'source': 'twitter',
                    'author': 'cnjgold',
                    'text': 'RT @DoglostUK: MAX + RUBY Black + Liver Cocker Spaniels MISSING https://t.co/218SCixyHh + https://t.co/f7pG9jtsxK #Tattersett #Syderstone #\u2026',
                    'media': None,
                    'created_date': '1455780422.0',
                    'id': 700219960891727872
                }, {
                    'entities': {},
                    'profile_picture': None,
                    'link': 'https://twitter.com/statuses/700219863332159489',
                    'source': 'twitter',
                    'author': 'stelothegod',
                    'text': 'She must not know about Dunedin or Holly Cove or south Norfolk but its all good lol https://t.co/hZnaC5vru1',
                    'media': None,
                    'created_date': '1455780399.0',
                    'id': 700219863332159489
                }, {
                    'entities': {},
                    'profile_picture': None,
                    'link': 'https://twitter.com/statuses/700219840183853056',
                    'source': 'twitter',
                    'author': 'Grosvenorgrass',
                    'text': 'Teams in #sahamtoney and #norwich. We offer a full installation service throughout #Norfolk #Suffolk. https://t.co/p3Yo8xcieK',
                    'media': None,
                    'created_date': '1455780394.0',
                    'id': 700219840183853056
                }
            ],
            self._get_twitter_messages([
                {
                    'created_at': 'Thu Feb 18 07:27:02 +0000 2016',
                    'entities': {   },
                    'id': 700219960891727872,
                    'text': 'RT @DoglostUK: MAX + RUBY Black + Liver Cocker Spaniels MISSING https://t.co/218SCixyHh + https://t.co/f7pG9jtsxK #Tattersett #Syderstone #\u2026',
                    'user': {'screen_name': 'cnjgold'}
                }, {
                    'created_at': 'Thu Feb 18 07:26:39 +0000 2016',
                    'entities': {   },
                    'id': 700219863332159489,
                    'text': 'She must not know about Dunedin or Holly Cove or south Norfolk but its all good lol https://t.co/hZnaC5vru1',
                    'user': { 'screen_name': 'stelothegod'}
                }, {
                    'created_at': 'Thu Feb 18 07:26:34 +0000 2016',
                    'entities': {   },
                    'id': 700219840183853056,
                    'text': 'Teams in #sahamtoney and #norwich. We offer a full installation service throughout #Norfolk #Suffolk. https://t.co/p3Yo8xcieK',
                    'user': { 'screen_name': 'Grosvenorgrass'}
                }
            ])
        )


    def test_author_and_profile_picture_should_be_none_without_user(self):
        self.assertEqual(
            [{
                'entities': {},
                'profile_picture': None,
                'link': 'https://twitter.com/statuses/700219960891727872',
                'source': 'twitter',
                'author': None,
                'text': 'Foo',
                'media': None,
                'created_date': '1455780422.0',
                'id': 700219960891727872
            }],
            self._get_twitter_messages([{
                    'created_at': 'Thu Feb 18 07:27:02 +0000 2016',
                    'entities': {},
                    'id': 700219960891727872,
                    'text': 'Foo',
                    'user': None
            }])
        )


    def test_should_return_empty_list_of_messages_if_no_credentials_are_given(self):
        self.assertEqual([], Twitter({}).get_raw_messages())
        self.assertEqual([], Twitter({'consumer_key': '...'}).get_raw_messages())
        self.assertEqual([], Twitter({'consumer_secret': '...'}).get_raw_messages())
        self.assertEqual([], Twitter({'query': '...'}).get_raw_messages())


    def test_should_inject_max_id_into_payload(self):
        test = self
        test.captured_url = None
        class TwitterMock(Twitter):
            def get_raw_messages_request(self, url, timeout=None):
                test.captured_url = url
                return {
                    'statuses': []
                }

        twitter = TwitterMock({'consumer_key': '...', 'consumer_secret': '...', 'query': 'norfolk'})
        twitter.max_id = 987
        twitter.get_raw_messages()
        self.assertIn('max_id=987', test.captured_url)


    def test_should_return_empty_list_if_no_new_message_available(self):
        class TwitterMock(Twitter):
            TWEET = { 'id': 1234 }
            def get_raw_messages_request(self, url, timeout=None):
                return {
                    'statuses': [self.TWEET]
                }

            def get_tweet(self, tweet_id):
                return self.TWEET


        twitter = TwitterMock({'consumer_key': '...', 'consumer_secret': '...', 'query': 'norfolk'})
        twitter.max_id = 1234
        self.assertEqual([{'id': 1234}], twitter.get_raw_messages())
        self.assertEqual(1234, twitter.previous_max_id)
        self.assertEqual([], twitter.get_raw_messages())


    def test_error_fetching_data_should_yield_empty_result(self):
        class TwitterMock(Twitter):
            def get_raw_messages_request(self, url, timeout=None):
                raise ValueError()

        twitter = TwitterMock({'consumer_key': '...', 'consumer_secret': '...', 'query': 'norfolk'})
        self.assertEqual([], twitter.get_raw_messages())


    @CubaneTestCase.complex()
    def test_should_fetch_endpoint(self):
        twitter = Twitter({
            'consumer_key': 'key',
            'consumer_secret': 'secret'
        })
        d = twitter.get_raw_messages_request('http://httpbin.org/get')
        self.assertEqual('key', d.get('args').get('oauth_consumer_key'))


    def _get_twitter_messages(self, raw_messages):
        class TwitterMock(Twitter):
            def get_raw_messages_request(self, url, timeout=None):
                return {
                    'statuses': raw_messages
                }


            def get_tweet(self, tweet_id):
                for m in raw_messages:
                    if m.get('id') == tweet_id:
                        return m


        twitter = TwitterMock({
            'consumer_key': '...',
            'consumer_secret': '...',
            'query': 'norfolk OR norfolkbroads'
        })

        aggregator = Aggregator([twitter])
        return list(itertools.islice(aggregator.get_messages(0), 0, len(raw_messages)))
