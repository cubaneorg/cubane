# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.aggregator.sources.filter import Filter
from cubane.aggregator.sources.twitter import Twitter
from cubane.aggregator.source_base import SourceBase
import time
import itertools


class Source(SourceBase):
    def __init__(self, messages):
        self._messages = messages


    def get_messages(self, since):
        for m in self._messages:
            yield m


class AggregatorFilterTestCase(CubaneTestCase):
    def test_filter_should_pass_valid_message(self):
        messages = [{
            'author': 'Foo',
            'text': 'Bar'
        }]
        self.assertEqual(messages, self._get_filtered_messages(messages))


    def test_filter_suspicious_username(self):
        self.assertEqual([], self._get_filtered_messages([{
            'author': 'foo_bar_',
            'text': 'Bar'
        }]))


    def test_filter_blacklisted_username(self):
        self.assertEqual([], self._get_filtered_messages([{
            'author': 'Foo',
            'text': 'Bar'
        }], username_blacklist=['Foo']))


    def test_filter_bad_word_in_text(self):
        self.assertEqual([], self._get_filtered_messages([{
            'author': 'Foo',
            'text': 'Fuck'
        }]))


    def test_filter_bad_word_in_username(self):
        self.assertEqual([], self._get_filtered_messages([{
            'author': 'Fuck',
            'text': 'Bar'
        }]))


    def test_non_latin_text(self):
        self.assertEqual([], self._get_filtered_messages([{
            'author': 'Foo',
            'text': '你好，世界'
        }]))


    def _get_filtered_messages(self, messages, bad_words=[], username_blacklist=[]):
        f = Filter(Source(messages), bad_words, username_blacklist)
        return list(itertools.islice(f.get_messages(0), 0, 10))