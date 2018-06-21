# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.ip import get_local_ips
import spf


class SPFCheck(object):
    PASS       = 'pass'
    FAIL       = 'fail'
    NEUTRAL    = 'neutral'
    SOFTFAIL   = 'softfail'
    PERM_ERROR = 'permerror'
    TEMP_ERROR = 'temperror'


    def __init__(self):
        self.results = []


    def check(self, ip, sender):
        """
        Perform an SPF check for the given IP address against the given sender email address.
        """
        status, code, msg = spf.check(ip, sender, None)
        result = (ip, status, code, msg)
        self.results.append(result)
        return result


    def check_local_ips(self, sender):
        """
        Perform an SPF check for the local IPv4 and IPv6 addresses. IPv6 is obmitted,
        if the local machine does not have an IPv6 address that is routed to the internet.
        """
        for ip in get_local_ips():
            self.check(ip, sender)


    def test(self, result):
        """
        Returns True, if all collected SPF test results matches the given result.
        """
        if len(self.results) > 0:
            return all(map(lambda r: r == result, [r[1] for r in self.results]))
        else:
            return False


    @property
    def test_pass(self):
        """
        Return True, if all results are passing.
        """
        return self.test(SPFCheck.PASS)


    @property
    def html_results(self):
        """
        Return the result of the SPF check (html).
        """
        html = ''

        if len(self.results) > 0:
            html += '<table>'
            html += (
                '<tr>' +
                    '<th>IP</th>' +
                    '<th>Result</th>' +
                    '<th>Status</th>' +
                    '<th>Message</th>' +
                '</tr>'
            )

            for ip, status, code, msg in self.results:
                html += (
                    '<tr>' +
                        '<td>%s</td>' % ip +
                        '<td>%s</td>' % status +
                        '<td>%s</td>' % code +
                        '<td>%s</td>' % msg +
                    '</tr>'
                )

            html += '</table>'

        return html
