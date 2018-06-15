# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase, CubaneManualTransactionTestCase
from cubane.dbmigrate import auto_migrate
from cubane.testapp.models import TestFTSPart
from cubane.lib.fts import fts_query
from cubane.lib.fts import sanitize_search_term


@CubaneTestCase.complex()
class LibFTSTestCase(CubaneManualTransactionTestCase):
    """
    Testing full text index would require postgresql as the database,
    so this is currently hard to test and we do not want to sacrifice
    testing performance just for the FTS module.
    """
    @classmethod
    def setUpClass(cls):
        super(LibFTSTestCase, cls).setUpClass()
        # run dbmigrate once for the first setup, so that we get full FTS
        # indices on the database level (postgresql).
        auto_migrate(interactive=False, load_fixtures=False)


    def setUp(self):
        self._create_part('123', 'Test')


    def tearDown(self):
        TestFTSPart.objects.all().delete()


    def test_fts_query_matching(self):
        parts = fts_query(TestFTSPart.objects.all(), 'fts_index', 'Test')
        self.assertEqual(parts.count(), 1)


    def test_fts_query_matching_alt_attr(self):
        parts = fts_query(TestFTSPart.objects.all(), 'fts_index', '123', alt_attr='partno')
        self.assertEqual(parts.count(), 1)


    def test_fts_query_not_matching(self):
        parts = fts_query(TestFTSPart.objects.all(), 'fts_index', 'Does Not Exist')
        self.assertEqual(parts.count(), 0)


    def test_fts_query_should_ignore_brackets(self):
        parts = fts_query(TestFTSPart.objects.all(), 'fts_index', '(Test)')
        self.assertEqual(parts.count(), 1)


    def _create_part(self, partno, name):
        p = TestFTSPart()
        p.partno = partno
        p.name = name
        p.save()
        return p


class LibFTSSanitizeTestCase(CubaneTestCase):
    def test_should_remove_invalid_characters(self):
        self.assertEqual('', sanitize_search_term('!@£$%^&*()+=`~<>?:"\'|\[]{}§±'))


    def test_should_remove_not_allowed_unicode_characters(self):
        self.assertEqual('', sanitize_search_term('\u0027'))


    def test_should_remove_utf8_non_latin_text(self):
        self.assertEqual('', sanitize_search_term('안녕하세요'))


    def test_should_handle_empty_term(self):
        self.assertEqual('', sanitize_search_term(''))


    def test_should_trim_words(self):
        self.assertEqual('foo:* & bar:*', sanitize_search_term(' foo  bar  '))