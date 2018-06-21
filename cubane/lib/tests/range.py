# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.range import get_ranges_for_min_max


class GetRangesForMinMaxTestCase(CubaneTestCase):
    """
    cubane.lib.range.get_ranges_for_min_max()
    """
    def test_get_ranges_for_min_max_should_return_list(self):
        range_choices = get_ranges_for_min_max(
            (20.99,1032),
            6,
            [1000,500,250,100,50,10]
        )
        self.assertEqual(range_choices[0][0] <= 20.99, True, 'The lowest range should be lower or equal to the min number given.')
        self.assertEqual(range_choices[-1][-1] >= 1032, True, 'The highest range should be higher or equal to the max number given.')
        self.assertIsInstance(range_choices, list, 'must be list')
