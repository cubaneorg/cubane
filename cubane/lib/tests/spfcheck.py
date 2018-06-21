# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.spfcheck import SPFCheck


class LibSPFCheckEmptyResultsTestCase(CubaneTestCase):
    def test_new_instance_should_have_no_test_results(self):
        self.assertEqual(0, len(SPFCheck().results))


    def test_instance_with_no_checks_should_fail_spf_check(self):
        self.assertFalse(SPFCheck().test_pass)


    def test_instance_with_no_checks_should_render_empty_html_results(self):
        self.assertEqual('', SPFCheck().html_results)


class LibSPFCheckTestCase(CubaneTestCase):
    def setUp(self):
        self.spf = SPFCheck()


    def test_check_spf_should_pass_for_valid_ipv4_with_spf_resord_present(self):
        self.assertEqual(
            ('176.58.117.208', 'pass', 250, 'sender SPF authorized'),
            self.spf.check('176.58.117.208', 'hello@cubane.org')
        )
        self.assertTrue(self.spf.test_pass)


    def test_check_spf_should_fail_for_valid_ipv4_with_spf_resord_present(self):
        self.assertEqual(
            ('1.2.3.4', 'softfail', 250, 'domain owner discourages use of this host'),
            self.spf.check('1.2.3.4', 'foo@gmail.com')
        )
        self.assertFalse(self.spf.test_pass)


    def test_check_spf_should_pass_for_valid_ipv6_with_spf_record_present(self):
        self.assertEqual(
            ('2001:4860:4000:aaaa:bbbb:cccc:dddd:eeee', 'pass', 250, 'sender SPF authorized'),
            self.spf.check('2001:4860:4000:aaaa:bbbb:cccc:dddd:eeee', 'foo@gmail.com')
        )
        self.assertTrue(self.spf.test_pass)


    def test_check_spf_should_fail_for_valid_ipv6_with_spf_record_present(self):
        self.assertEqual(
            ('1234:1234:1234:aaaa:bbbb:cccc:dddd:eeee', 'softfail', 250, 'domain owner discourages use of this host'),
            self.spf.check('1234:1234:1234:aaaa:bbbb:cccc:dddd:eeee', 'foo@gmail.com')
        )
        self.assertFalse(self.spf.test_pass)


    def test_check_local_ips_should_fail(self):
        self.spf.check_local_ips('foo@gmail.com')
        self.assertFalse(self.spf.test_pass)


class LibSPFCheckShouldAccummulateChecksTestCase(CubaneTestCase):
    def test_should_accummulate_tests(self):
        spf = SPFCheck()
        spf.check('176.58.117.208', 'hello@cubane.org')
        spf.check('1.2.3.4', 'foo@gmail.com')
        self.assertEqual(2, len(spf.results))

        html = spf.html_results
        self.assertIn('sender SPF authorized', html)
        self.assertIn('domain owner discourages use of this host', html)