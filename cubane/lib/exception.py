# coding=UTF-8
from __future__ import unicode_literals
from django.template import Context
from django.views.debug import ExceptionReporter
from cubane.lib.template import get_template
import sys


class CustomerFacingExceptionReporter(ExceptionReporter):
    def get_traceback_html(self):
        """
        Return HTML version of debug 500 HTTP error page but using a different
        (simpler) template that is more convenient for customers and end users
        rather than targeting developers.
        """
        t = get_template('cubane/customer_500_template.html')
        c = Context(self.get_traceback_data(), use_l10n=False)
        return t.render(c)


def get_customer_traceback_html(request, is_email=False):
    """
    Return HTML that represents a customer-facing debug template giving
    detailed information about the last exception that occurred.
    """
    exc_info = sys.exc_info()
    reporter = CustomerFacingExceptionReporter(request, is_email=is_email, *exc_info)
    return reporter.get_traceback_html()