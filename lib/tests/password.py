# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.password import *
import random


class LibPasswordTestCaseBase(CubaneTestCase):
    def setUp(self):
        # make sure we are always generating the same sequence of
        # random numbers to have repeatable password generation
        random.seed(0)


class LibPasswordGibberishTestCase(LibPasswordTestCaseBase):
    def test_should_generate_random_word_list_based_on_default_population(self):
        self.assertEqual(['vah', 'suft'], gibberish(2))
        self.assertEqual(['skuz', 'brung', 'fipt'], gibberish(3))


    def test_should_return_empty_list_for_zero_sampling(self):
        self.assertEqual([], gibberish(0))


    def test_should_accept_population_argument(self):
        self.assertEqual(['c', 'b'], gibberish(2, ['a', 'b', 'c']))


    def test_should_raise_exception_if_sample_larger_than_population(self):
        with self.assertRaisesRegexp(ValueError, 'sample larger than population'):
            gibberish(3, ['a', 'b'])


class LibPasswordGetPronounceablePasswordTestCase(LibPasswordTestCaseBase):
    WORD_PASSWORDS  = ['', 'vah', 'suftskuz', 'brungfiptskent', 'rozstingamjav']
    DIGIT_PASSWORDS = ['', '8', '75', '420', '2589']


    def test_should_return_random_password_with_two_words_and_2_digit_number_by_default(self):
        self.assertEqual('vahsuft42', get_pronounceable_password())


    def test_should_return_random_password_with_given_amount_of_words(self):
        self.assertEqual(
            self.WORD_PASSWORDS,
            [get_pronounceable_password(i, 0) for i in range(0, len(self.WORD_PASSWORDS))]
        )


    def test_should_return_random_password_with_given_amount_of_digits(self):
        self.assertEqual(
            self.DIGIT_PASSWORDS,
            [get_pronounceable_password(0, i) for i in range(0, len(self.DIGIT_PASSWORDS))]
        )