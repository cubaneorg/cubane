# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.utils import override_settings
from cubane.lib import verbose
import StringIO


class LibVerboseOutTestCase(CubaneTestCase):
    def setUp(self):
        self.output = StringIO.StringIO()


    @override_settings(TEST=True)
    def test_should_not_print_if_under_test(self):
        verbose.out('hello world', channel=self.output)
        self.assertEqual('', self.output.getvalue())


    @override_settings(TEST=False)
    def test_should_not_print_if_not_verbose(self):
        verbose.out('hello world', verbose=False, channel=self.output)
        self.assertEqual('', self.output.getvalue())


    @override_settings(TEST=False)
    def test_should_print_if_verbose_and_not_under_test(self):
        verbose.out('hello world', verbose=True, channel=self.output)
        self.assertEqual('hello world\n', self.output.getvalue())


    @override_settings(TEST=False)
    def test_should_print_if_verbose_and_not_under_test_without_newline(self):
        verbose.out('hello world', newline=False, verbose=True, channel=self.output)
        self.assertEqual('hello world', self.output.getvalue())


class LibVerboseConditionalTestCase(CubaneTestCase):
    def setUp(self):
        self.output = StringIO.StringIO()


    @override_settings(TEST=True)
    def test_should_not_execute_if_under_test(self):
        verbose.conditional(self._print)
        self.assertEqual('', self.output.getvalue())


    @override_settings(TEST=False)
    def test_should_not_execute_if_not_verbose(self):
        verbose.conditional(self._print, verbose=False)
        self.assertEqual('', self.output.getvalue())


    @override_settings(TEST=False)
    def test_should_execute_if_verbose_and_not_under_test(self):
        verbose.conditional(self._print, verbose=True)
        self.assertEqual('hello world\n', self.output.getvalue())


    def _print(self):
        self.output.write('hello world\n')