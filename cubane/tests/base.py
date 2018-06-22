# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.http import HttpResponseRedirect
from django.core import mail
from django.db import connection
from django.utils.safestring import SafeText
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.cache import SessionStore
from cubane.backend.models import UserProfile
from cubane.backend.views import Backend
from cubane.backend.changelog import ChangeLogManager
import unittest
import os
import re


class CubaneTestCase(TestCase):
    """
    Default base class for all cubane test cases.
    """
    def __init__(self, *args, **kwargs):
        super(CubaneTestCase, self).__init__(*args, **kwargs)
        self.maxDiff = None


    @classmethod
    def complex(reason='Full Test Suite Required'):
        """
        Decorator for marking a test case or test method to only run under the full
        test suite. This is usually used for anything that is network bound or
        too heavy in terms of computational complexity or database workload.
        """
        return unittest.skipIf(not settings.TEST_FULL, reason)


    def assertEqual(self, a, b, msg=None):
        """
        unittest.TestCase.assertEqual does not show diff when comparing
        django's SafeText with unicode.
        """
        if isinstance(a, SafeText):
            a = unicode(a)

        if isinstance(b, SafeText):
            b = unicode(b)

        try:
            super(CubaneTestCase, self).assertEqual(a, b, msg)
        except AssertionError, e:
            raise AssertionError('%s\n\n%s\n--- != ---\n%s\n' % (
                e.message,
                unicode(a)[:5000] if a is not None else None,
                unicode(b)[:5000] if b is not None else None
            ))


    def assertFileContent(self, filename, content, alternative_content=None):
        """
        Assert that the given file exists, is readable and contains the given content.
        """
        with file(filename) as f:
            actual_content = f.read()

            if alternative_content is None:
                self.assertEqual(content, actual_content)
            else:
                self.assertTrue(
                    content             == actual_content or
                    alternative_content == actual_content
                )


    def get_latest_email(self):
        """
        Assert that there is at least one email that was send and return the
        latest email send.
        """
        self.assertTrue(len(mail.outbox) > 0, 'no email send.')
        return mail.outbox[-1]


    def _createAssert(self, name, func):
        """
        Creates a new assert function if it is not defined already.
        """
        if not hasattr(self, name):
            setattr(self, name, func)


    def get_testapp_path(self):
        """
        Return the base path of the testapp application as part of cubane
        that is used for unit testing.
        """
        import cubane.testapp as testapp
        return os.path.dirname(testapp.__file__)


    def get_testapp_media_path(self):
        """
        Return the base path of the media asset folder for the testapp.
        """
        return os.path.join(self.get_testapp_path(), 'media')


    def get_testapp_static_path(self):
        """
        Return the base path of the static asset folder for the testapp.
        """
        return os.path.join(self.get_testapp_path(), 'static', 'cubane', 'testapp')


    def get_test_image_path(self, filename):
        """
        Return the full path to the given test file within the testapp.
        """
        base_path = self.get_testapp_path()
        return os.path.join(base_path, 'static', 'cubane', 'testapp', 'img', 'test_images', filename)


    def reset_db_seq(self, model_list):
        """
        Reset databasse sequences.
        """
        # get reset sequence sql
        from django.db import connection, connections, DEFAULT_DB_ALIAS
        from django.core.management.color import no_style
        c = connections[DEFAULT_DB_ALIAS]
        sql = '\n'.join(c.ops.sequence_reset_sql(no_style(), model_list))

        # execute
        cursor = connection.cursor()
        cursor.execute(sql)


    def assertUserPassword(self, user, password):
        """
        Assert that the given user can be authenticated by using the given
        password (cleartext).
        """
        auth_user = authenticate(username=user.username, password=password)
        self.assertIsNotNone(auth_user)
        self.assertEqual(user.pk, auth_user.pk)


    def assertIsRedirect(self, response, location):
        """
        Assert that the given response is a redirect response and points to
        the given location.
        """
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(location, response['Location'])


    def assertMessage(self, request, msg):
        """
        Assert that the request contains the given message.
        """
        for m in request._messages._queued_messages:
            if msg in m.message:
                return
        self.assertTrue(False, 'Expected message not found: %s. Available messages: %s' % (msg, ', '.join([m.message for m in request._messages._queued_messages])))


    def assertFormFieldError(self, form, fieldname, msg):
        """
        Assert that the given form contains the given message.
        """
        errors = form.errors.get(fieldname)
        self.assertIsNotNone(errors)
        for errmsg in errors:
            if msg in errmsg:
                return
        self.assertTrue(False, 'Expected form message not found: %s. Available messages: %s' % (msg, ', '.join([msg for msg in errors])))


    def assertFormError(self, form, msg):
        self.assertFormFieldError(form, '__all__', msg)


    def matchesAttributes(self, match, attrs):
        """
        Return True, if the given match contains all given attributes.
        """
        matches = False
        for k, v in attrs.items():
            if v == True:
                if k not in match:
                    return False
            else:
                if ('%s="%s"' % (k, v)) not in match:
                    return False

        return True


    def assertMarkup(self, markup, tag, attrs, content=None):
        """
        Assert that the given markup contains the given tag with the given
        attributes.
        """
        # verify that at least one tag exists for which all attributes are set
        if content is None:
            for m in re.findall(r'<%s(.*?)>' % tag, markup):
                if self.matchesAttributes(m, attrs):
                    return
        else:
            for m, m_content in re.findall(r'<%s(.*?)>(.*?)</%s>' % (tag, tag), markup):
                if self.matchesAttributes(m, attrs) and content in m_content:
                    return

        self.assertTrue(False, 'tag \'%s\' with attributes \'%s\' not found within markup \'%s\' or content does not match.' % (
            tag,
            ', '.join(attrs),
            markup
        ))


    def assertNoneOrEmpty(self, v):
        """
        Assert that the given value v is either None or empty.
        """
        self.assertTrue(v in [None, ''])


    def get_user_profile(self, user):
        if user and not isinstance(user, AnonymousUser):
            try:
                return UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                user_profile = UserProfile()
                user_profile.user = user
        else:
            user_profile = None

        return user_profile


    def run_view_handler(self, view, user, handler_name, method, url, data={}):
        _, response = self.run_view_handler_request(view, user, handler_name, method, url, data)
        return response


    def get_view_handler_request(self, view, user, handler_name, method, url, data={}, ajax=False):
        factory = RequestFactory()
        f = getattr(factory, method)

        # create request with session store
        request = f(url, data)
        request.session = SessionStore()
        request.META['HTTP_HOST'] = '127.0.0.1'
        request._messages = FallbackStorage(request)

        # user
        if user and user.id:
            self.login(request, user)

        # ajax
        if ajax:
            request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        # user, profile and backend
        request.user = user
        request.user_profile = self.get_user_profile(request.user)
        request.backend = Backend()

        # changelog
        request.changelog = ChangeLogManager(request)

        return request


    def make_request(self, method, url, data={}, ajax=False, user=None):
        """
        Create a mock request object that supports messaging and session
        handling.
        """
        factory = RequestFactory()
        f = getattr(factory, method)

        request = f(url, data)
        request.session = SessionStore()
        request.META['HTTP_HOST'] = '127.0.0.1'
        request._messages = FallbackStorage(request)

        # ajax
        if ajax:
            request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        # user
        if user:
            request.user = user
            request.user_profile = self.get_user_profile(request.user)

        # changelog
        request.changelog = ChangeLogManager(request)

        return request


    def run_view_handler_request(self, view, user, handler_name, method, url, data={}, ajax=False, args=[], kwargs={}):
        """
        Execute the view handler with the given name by using a request of given
        method, given url and given data.
        """
        request = self.get_view_handler_request(view, user, handler_name, method, url, data, ajax)
        return (request, view.run_handler(request, handler_name, *args, **kwargs))


    def login(self, request, user):
        """
        Login the given user account.
        """
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        return user


    def logout(self, request):
        """
        Logout of the current session.
        """
        auth_logout(request)


    def call_command(self, command, args=[], options={}):
        """
        Run the management command with the given name.
        """
        command.handle(*args, **options)


    def patch_filter_visibility(self, model):
        """
        Patch given model's filter_visibility method.
        """
        def filter_visibility(cls, objects, visibility_filter_args={}):
            return objects.filter(title='Foo')
        _filter_visibility = model.filter_visibility
        model.filter_visibility = classmethod(filter_visibility)
        return _filter_visibility


    def restore_filter_visibility(self, model, f):
        """
        Restore given model's filter_visibility method with the given
        method implementation f.
        """
        model.filter_visibility = f


class CubaneManualTransactionTestCase(CubaneTestCase):
    """
    Disable regular transaction behaviour, since a test derived from this test
    case requires manual transaction management.
    """
    @classmethod
    def _enter_atomics(cls):
        return {}


    @classmethod
    def _rollback_atomics(cls, atomics):
        pass


    @classmethod
    def setUpClass(cls):
        super(CubaneManualTransactionTestCase, cls).setUpClass()
        connection.set_autocommit(False)