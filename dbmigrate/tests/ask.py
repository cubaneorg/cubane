# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.utils import override_settings
from cubane.dbmigrate.ask import ask
from cubane.dbmigrate.ask import ask_confirm
from cubane.dbmigrate.ask import ask_rename_table
from cubane.dbmigrate.ask import ask_rename_field
from cubane.testapp.models import TestModel
import mock


class DBMigrateAskTestCase(CubaneTestCase):
    @mock.patch('sys.stdin')
    def test_ask_should_not_accept_invalid_choice(self, stdin):
        self.last_input = None
        def input():
            if self.last_input == None:
                self.last_input = 'x'
            else:
                self.last_input = '2'
            return self.last_input
        stdin.readline = input
        self.assertEqual((2, 'b'), ask('Test?', ['a', 'b']))


    @mock.patch('sys.stdin')
    def test_ask_should_accept_numeric_choice(self, stdin):
        stdin.readline.return_value = '1'
        self.assertEqual((1, 'a'), ask('Test?', ['a', 'b']))


    @mock.patch('sys.stdin')
    def test_ask_should_accept_label_choice(self, stdin):
        stdin.readline.return_value = 'b'
        self.assertEqual((2, 'b'), ask('Test?', ['a', 'b']))


    @mock.patch('sys.stdin')
    def test_ask_should_accept_first_choice_by_default(self, stdin):
        stdin.readline.return_value = ''
        self.assertEqual((1, 'a'), ask('Test?', ['a', 'b']))


    @override_settings(TEST=False)
    @mock.patch('sys.stdin')
    @mock.patch('sys.stdout')
    def test_ask_should_print_choices_when_not_under_test(self, stdin, stdout):
        stdin.readline.return_value = ''
        stdout.write.return_value = ''
        self.assertEqual((1, 'a'), ask('Test?', ['a', 'b']))


    def test_ask_should_return_first_choice_in_non_interactive_mode(self):
        self.assertEqual((1, 'a'), ask('Test?', ['a', 'b'], interactive=False))


class DBMigrateAskConfirmTestCase(CubaneTestCase):
    @mock.patch('sys.stdin')
    def test_ask_confirm_should_accept_yes(self, stdin):
        stdin.readline.return_value = 'yes'
        self.assertTrue(ask_confirm('Test?'))


    @mock.patch('sys.stdin')
    def test_ask_confirm_should_accept_no(self, stdin):
        stdin.readline.return_value = 'no'
        self.assertFalse(ask_confirm('Test?'))


    @mock.patch('sys.stdin')
    def test_ask_confirm_default_choice_should_return_false(self, stdin):
        stdin.readline.return_value = ''
        self.assertFalse(ask_confirm('Test?'))


    def test_ask_confirm_should_return_true_in_non_interactive_mode(self):
        self.assertTrue(ask_confirm('Test?', interactive=False))


class DBMigrateAskRenameTableTestCase(CubaneTestCase):
    @mock.patch('cubane.dbmigrate.ask.ask')
    def test_first_option_should_be_no_option(self, ask):
        ask_rename_table(TestModel, ['a', 'b'])
        self.assertEqual([mock.call("Was the table 'testapp_testmodel' renamed?", ['no, was added.', 'a', 'b'], 'no', interactive=True)], ask.call_args_list)


class DBMigrateAskRenameFieldTestCase(CubaneTestCase):
    @mock.patch('cubane.dbmigrate.ask.ask')
    def test_first_option_should_be_no_option(self, ask):
        field = TestModel._meta.get_field('title')
        ask_rename_field(TestModel, field, ['a', 'b'])
        self.assertEqual([mock.call("Was the field 'testapp_testmodel.title' renamed?", ['no, was added.', 'a', 'b'], 'no', interactive=True)], ask.call_args_list)