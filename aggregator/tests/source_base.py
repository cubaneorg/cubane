# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.aggregator.source_base import SourceBase


class TestSource(SourceBase):
    pass


class AggregatorSourceTestCase(CubaneTestCase):
    """
    cubane.aggregator.source_base.SourceBase()
    """
    @property
    def since(self):
        return 7


    def get_zero_raw_messages(self, since=None):
        return []


    def get_raw_messages(self, since=None):
        return [{'created_date': 10}, {'created_date': 5}]


    def normalize(self, data):
        data['normalized'] = True
        return data


    def test_should_not_implement_get_raw_messages(self):
        s = TestSource()
        with self.assertRaises(NotImplementedError):
            s.get_raw_messages()


    def test_should_not_implement_normalize(self):
        s = TestSource()
        with self.assertRaises(NotImplementedError):
            s.normalize()


    def test_should_not_yield_any_data_if_length_of_raw_messages_is_zero(self):
        TestSource.get_raw_messages = self.get_zero_raw_messages
        s = TestSource()
        self.assertEqual(0, len(list(s.get_messages(self.since))))


    def test_should_yield_normalized_data_since(self):
        TestSource.get_raw_messages = self.get_raw_messages
        TestSource.normalize = self.normalize
        s = TestSource()

        for m in s.get_messages(self.since):
            self.assertEqual(True, m['normalized'])
            self.assertEqual(10, m['created_date'])
