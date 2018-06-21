# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.auth.models import User, AnonymousUser
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from cubane.tests.base import CubaneTestCase
from cubane.decorators import *
from cubane.backend.accounts.models import ProxyUser
from cubane.views import ModelView
from cubane.cms.views import SettingsView
from cubane.testapp.models import TestModel
from cubane.testapp.models import TestModelWithPermissionsDefined
from mock import MagicMock


class TestWithPermissionDefinedView(ModelView):
    model = TestModelWithPermissionsDefined


class DecoratorTestCaseBase(CubaneTestCase):
    def _create_perm(self, model, perm_name, user):
        content_type = ContentType.objects.get_for_model(model)
        permission = Permission.objects.create(content_type=content_type, codename=perm_name)
        user.user_permissions.add(permission)
        return permission


    def _create_request(self, view=None, is_staff=True, is_anonymous=False, is_superuser=None):
        if is_superuser is None:
            is_superuser = is_staff

        factory = RequestFactory()
        request = factory.get('/')

        if is_anonymous:
            request.user = AnonymousUser()
        else:
            request.user = User(is_staff=is_staff, is_superuser=is_superuser)

        if view:
            request.view_instance = view

        return request


    def _assertRedirectToLoginResponse(self, response, view_handler, login_url='cubane.backend.login'):
        self.assertEqual(302, response.status_code)
        self.assertEqual(reverse(login_url), response.get('Location'))
        self.assertFalse(view_handler.called)


class DecoratorsRedirectLoginTestCase(DecoratorTestCaseBase):
    def test_redirect_login_redirects_to_correct_url(self):
        self.factory = RequestFactory()
        request = self.factory.get('/')
        redirect = redirect_login(request)
        self.assertEqual('/admin/login/', redirect._headers.get('location')[1])
        self.assertEqual(302, redirect.status_code)


class DecoratorsUserHasPermissionTestCase(DecoratorTestCaseBase):
    def test_should_return_false_for_regular_user(self):
        user = User()
        self.assertFalse(user_has_permission(user, TestModel))


    def test_should_return_true_for_superuser_always(self):
        user = User(is_staff=True, is_superuser=True)
        self.assertTrue(user_has_permission(user, TestModel))
        self.assertTrue(user_has_permission(user, ProxyUser))


    def test_should_return_true_for_admin_user_for_testmodel(self):
        user = User(is_staff=True)
        self.assertTrue(user_has_permission(user, TestModel))
        self.assertFalse(user_has_permission(user, ProxyUser))


    def test_should_return_false_for_verb_not_allowed_by_model(self):
        user = User(is_staff=True)
        self.assertFalse(user_has_permission(user, TestModelWithPermissionsDefined, 'edit'))


    @override_settings(CUBANE_BACKEND_PERMISSIONS=True)
    def test_should_return_false_if_model_defines_perm_that_user_does_not_have(self):
        user = User.objects.create_user('test', 'test@innershed.com', 'password')
        user.is_staff = True
        user.save()
        self.assertEqual(user_has_permission(user, TestModel, 'edit'), False, 'Admin User should not have permission')


    @override_settings(CUBANE_BACKEND_PERMISSIONS=True)
    def test_should_return_true_if_model_defines_perm_that_user_has(self):
        user = User.objects.create_user('test', 'test@innershed.com', 'password')
        user.is_staff = True
        user.save()
        self._create_perm(TestModel, 'edit_testmodel', user)
        self.assertTrue(user_has_permission(user, TestModel, 'edit'))


    @override_settings(CUBANE_BACKEND_PERMISSIONS=True)
    def test_should_return_true_if_proxy_model_defines_perm_that_user_has(self):
        user = User.objects.create_user('test', 'test@innershed.com', 'password')
        user.is_staff = True
        user.save()
        self._create_perm(ProxyUser, 'edit_user', user)
        self.assertTrue(user_has_permission(user, ProxyUser, 'edit'))


class DecoratorsPermissionRequiredTestCase(DecoratorTestCaseBase):
    def test_should_redirect_to_login_screen_if_permission_is_not_met(self):
        view_handler = MagicMock()
        request = self._create_request(SettingsView(), False)
        response = permission_required()(view_handler)(request)
        self._assertRedirectToLoginResponse(response, view_handler)


    def test_should_redirect_to_custom_login_screen_if_permission_is_not_met(self):
        login_url = 'test_non_standard_cms_page'
        view_handler = MagicMock()
        request = self._create_request(SettingsView(), False)
        response = permission_required(login_url=login_url)(view_handler)(request)
        self._assertRedirectToLoginResponse(response, view_handler, login_url)


    def test_should_redirect_to_login_screen_if_verb_not_allowed_by_model(self):
        view_handler = MagicMock()
        request = self._create_request(TestWithPermissionDefinedView(), True)
        response = permission_required(verb='edit')(view_handler)(request)
        self._assertRedirectToLoginResponse(response, view_handler)


    def test_should_execute_view_handler_if_permission_is_met(self):
        view_handler = MagicMock()
        view_handler.return_value = 'Foo'
        request = self._create_request(SettingsView(), True)
        response = permission_required()(view_handler)(request)

        self.assertEqual('Foo', response)
        view_handler.assert_called_with(request)


class DecoratorsBackendLoginRequiredTestCase(DecoratorTestCaseBase):
    def test_should_redirect_to_login_screen_if_user_not_authenticated(self):
        view_handler = MagicMock()
        request = self._create_request(view=None, is_anonymous=True)
        response = backend_login_required()(view_handler)(request)
        self._assertRedirectToLoginResponse(response, view_handler)



    def test_should_redirect_to_login_screen_if_non_staff_user(self):
        view_handler = MagicMock()
        request = self._create_request(view=None, is_staff=False)
        response = backend_login_required()(view_handler)(request)
        self._assertRedirectToLoginResponse(response, view_handler)


    def test_should_execute_view_handler_if_permission_is_met(self):
        view_handler = MagicMock()
        view_handler.return_value = 'Foo'
        request = self._create_request(view=None, is_staff=True)
        response = backend_login_required()(view_handler)(request)

        self.assertEqual('Foo', response)
        view_handler.assert_called_with(request)


class DecoratorsIdentityTestCase(DecoratorTestCaseBase):
    def test_should_execute_decorated_view_handler(self):
        self.assertEqual('Foo', identity('Foo'))


class DecoratorsTemplateTestCase(DecoratorTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(DecoratorsTemplateTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        cls.view_handler = MagicMock()


    def test_should_render_template_with_content(self):
        self.view_handler.return_value = {
            'bar': 'Bar'
        }
        response = template('testapp/template.html')(self.view_handler)(self.request)
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/html; charset=utf-8', response['Content-Type'])
        self.assertEqual('Foo Bar', response.content)


    def test_should_return_http_response_as_returned_by_view_handler(self):
        self.view_handler.return_value = HttpResponse('Direct Response')
        response = template('testapp/template.html')(self.view_handler)(self.request)
        self.assertEqual('Direct Response', response.content)


    def test_should_return_object_as_returned_by_view_handler_if_not_http_response_nor_dict(self):
        self.view_handler.return_value = 'Direct Response'
        response = template('testapp/template.html')(self.view_handler)(self.request)
        self.assertEqual('Direct Response', response)


    def test_should_take_response_object_from_dict_if_provided(self):
        self.view_handler.return_value = {
            'bar': 'Bar',
            'response': HttpResponse(content_type='application/pdf')
        }
        response = template('testapp/template.html')(self.view_handler)(self.request)
        self.assertEqual('Foo Bar', response.content)
        self.assertEqual('application/pdf', response['Content-Type'])


    def test_should_take_template_from_dict_if_provided(self):
        self.view_handler.return_value = {
            'bar': 'Bar',
            'template': 'testapp/test.html'
        }
        response = template()(self.view_handler)(self.request)
        self.assertEqual('Test', response.content)


    def test_should_raise_exception_if_no_template_name_is_given(self):
        self.view_handler.return_value = {
            'bar': 'Bar'
        }

        with self.assertRaisesRegexp(ValueError, 'No Template given'):
            template()(self.view_handler)(self.request)


    def test_should_take_dict_context_returned_from_view_handler(self):
        context = {
            'bar': 'Bar'
        }
        self.view_handler.return_value = context
        response = template('testapp/template.html')(self.view_handler)(self.request)
        self.assertEqual('Foo Bar', response.content)