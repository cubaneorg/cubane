# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.test import RequestFactory
from django.test.utils import override_settings
from django.core.urlresolvers import RegexURLPattern
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login
from django.contrib.sessions.models import Session
from cubane.forms import BaseLoginForm
from cubane.backend.forms import BackendLoginForm
from cubane.backend.forms import BackendPasswordResetForm
from cubane.tests.base import CubaneTestCase, CubaneManualTransactionTestCase
from cubane.backend.views import Backend, BackendSection, BackendView, RelatedModelCollection
from cubane.backend.models import UserProfile
from cubane.backend.accounts.views import AccountBackendSection, AccountBackendSubSection
from cubane.cms.views import ContentBackendSection
from cubane.cms.models import Page
from cubane.media.views import MediaBackendSection, ImageBackendSection
from cubane.media.models import Media
from cubane.views import View
from cubane.lib.libjson import to_json, decode_json
from cubane.testapp.models import TestModel, TestPageMedia, TestPageWithMedia
from cubane.testapp.api import TestApiView
import datetime
from mock.mock import Mock, patch


class TestView(View):
    def user_has_permission(self, user, view=None):
        return True


class TestBackendSection(BackendSection):
    pass


class RelatedModelCollectionTestCase(CubaneTestCase):
    def tearDown(self):
        [x.delete() for x in TestPageMedia.objects.all()]
        [p.delete() for p in TestPageWithMedia.objects.all()]
        [m.delete() for m in Media.objects.all()]


    def test_should_load_page_media_in_seq(self):
        p = TestPageWithMedia.objects.create(title='A')
        m1 = Media.objects.create(caption='M1')
        m2 = Media.objects.create(caption='M2')
        TestPageMedia.objects.create(from_page=p, to_media=m1, seq=2)
        TestPageMedia.objects.create(from_page=p, to_media=m2, seq=1)

        self.assertEqual(
            [m2, m1],
            RelatedModelCollection.load(p, TestPageMedia)
        )


    def test_should_save_page_media_in_seq(self):
        p = TestPageWithMedia.objects.create(title='A')
        m1 = Media.objects.create(caption='M1')
        m2 = Media.objects.create(caption='M2')
        request = self.make_request('get', '/')
        RelatedModelCollection.save(request, p, [m2, m1], TestPageMedia)
        assignments = list(TestPageMedia.objects.all().order_by('seq'))
        self.assertEqual([1, 2], [x.seq for x in assignments])
        self.assertEqual([m2, m1], [x.to_media for x in assignments])


class BackendViewsBackendSectionTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendViewsBackendSectionTestCase, cls).setUpClass()
        cls.backend = Backend()


    def test_get_url_should_return_url_from_attached_view(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        subsection = section.get_section_by_class(AccountBackendSubSection)
        self.assertEqual('/admin/accounts/', subsection.url)


    def test_get_url_should_return_url_from_subsections(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        self.assertEqual('/admin/accounts/', section.url)


    def test_get_url_should_return_empty_when_no_view_nor_subsections_attached(self):
        section = BackendSection()
        self.assertEqual('', section.url)


    def test_get_urls_should_return_all_urls_from_all_views(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        self.assertEqual(26, len(section.get_urls(self.backend)))


    def test_has_multiple_sub_sections_should_return_false_if_there_is_only_one_sub_section(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        self.assertFalse(section.has_multiple_sub_sections)


    def test_has_multiple_sub_sections_should_return_true_for_multiple_sub_sections(self):
        section = self.backend.get_section_by_class(ContentBackendSection)
        self.assertTrue(section.has_multiple_sub_sections)


    def test_get_first_visible_to_user_should_NOT_consider_section_with_view(self):
        section = BackendSection()
        self.assertIsNone(section.get_first_visible_to_user(User()))


    def test_get_first_visible_to_user_should_consider_section_with_view_but_ignore_if_not_navigatable(self):
        section = BackendSection()
        section.navigatable = False
        section.view = TestView()
        self.assertIsNone(section.get_first_visible_to_user(User()))


    def test_get_first_visible_to_user_should_consider_section_with_view_that_is_navigatable(self):
        section = BackendSection()
        section.view = TestView()
        self.assertIsNotNone(section.get_first_visible_to_user(User()))


    def test_get_first_visible_to_user_should_consider_sub_sections(self):
        section = BackendSection()
        self.assertIsNone(section.get_first_visible_to_user(User()))
        section.sections = [BackendSection()]
        section.sections[0].view = TestView()
        self.assertIsNotNone(section.get_first_visible_to_user(User()))


    def test_grouped_sections_should_return_empty_list_for_section_without_subsections(self):
        section = BackendSection()
        self.assertEqual([], section.grouped_sections())


    def test_grouped_sections_should_return_sub_sections(self):
        section = self.backend.get_section_by_class(MediaBackendSection)
        titles = [g.get('section').title for g in section.grouped_sections()]
        self.assertEqual(['Images', 'Documents', 'Folders'], titles)


    def test_grouped_sections_should_return_grouped_sub_sections(self):
        section = self.backend.get_section_by_class(ContentBackendSection)
        titles = []
        for g in section.grouped_sections():
            if g.get('grouped'):
                titles.append([s.title for s in g.get('sections')])
        self.assertEqual([['Test Grouped Models A', 'Test Grouped Models B']], titles)


    def test_get_url_for_model_should_consider_view(self):
        section = self.backend.get_section_by_class(ContentBackendSection)
        subsection = None
        for s in section.sections:
            if s.view.model == TestModel:
                subsection = s
        self.assertIsNotNone(subsection)
        self.assertEqual('/admin/test-models/', subsection.get_url_for_model(TestModel))


    def test_get_url_for_model_should_consider_subsections(self):
        section = self.backend.get_section_by_class(ContentBackendSection)
        self.assertEqual('/admin/test-models/', section.get_url_for_model(TestModel))


    def test_get_section_by_class_should_return_section_by_given_class(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        self.assertIsInstance(section.get_section_by_class(AccountBackendSubSection), AccountBackendSubSection)


    def test_get_section_by_class_should_return_none_if_no_class_matches(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        self.assertIsNone(section.get_section_by_class(TestBackendSection))


class BackendViewsBackendViewTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendViewsBackendViewTestCase, cls).setUpClass()
        cls.backend = Backend()


    @classmethod
    def tearDownClass(cls):
        cls.backend = None
        super(BackendViewsBackendViewTestCase, cls).tearDownClass()


    def test_site_property_should_return_backend(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertEqual(self.backend, backend_view.site)


    def test_url_property_should_return_backend_url(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertEqual('/admin/', backend_view.url)


    def test_default_map_location_json_should_return_default_map_location_from_settings(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertEqual(to_json(settings.DEFAULT_MAP_LOCATION), backend_view.default_map_location_json)


    def test_sections_property_should_return_backend_sections(self):
        backend = Backend()
        backend_view = BackendView(backend, backend.sections, None, None)
        self.assertEqual(backend._sections, backend_view.sections)
        backend._sections = []
        self.assertEqual([], backend_view.sections)


    def test_has_sub_sections_should_return_true_if_backend_has_sections(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertTrue(backend_view.has_sub_sections)


    def test_has_sub_sections_should_return_false_if_backend_has_no_sections(self):
        backend = Backend()
        for s in backend.sections:
            s.sections = []
        backend_view = BackendView(backend, backend.sections, None, None)
        self.assertFalse(backend_view.has_sub_sections)


    def test_current_section_should_return_current_section_none(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertIsNone(backend_view.current_section)


    def test_current_section_should_return_current_section(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        backend_view = BackendView(self.backend, self.backend.sections, section, None)
        self.assertEqual(section, backend_view.current_section)


    def test_current_sub_section_should_return_current_section_none(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertIsNone(backend_view.current_sub_section)


    def test_current_sub_section_should_return_current_section(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        subsection = section.get_section_by_class(AccountBackendSubSection)
        backend_view = BackendView(self.backend, self.backend.sections, section, subsection)
        self.assertEqual(subsection, backend_view.current_sub_section)


    def test_title_should_return_title_of_current_sub_section(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        subsection = section.get_section_by_class(AccountBackendSubSection)
        backend_view = BackendView(self.backend, self.backend.sections, section, subsection)
        self.assertEqual(subsection.title, backend_view.title)


    def test_title_should_return_title_of_current_section_if_no_sub_section_is_available(self):
        section = self.backend.get_section_by_class(AccountBackendSection)
        backend_view = BackendView(self.backend, self.backend.sections, section, None)
        self.assertEqual(section.title, backend_view.title)


    def test_get_url_for_model_should_return_backend_url_for_given_model(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertEqual('/admin/test-models/', backend_view.get_url_for_model(TestModel))


    def test_get_url_for_model_should_return_none_if_model_not_found(self):
        backend_view = BackendView(self.backend, self.backend.sections, None, None)
        self.assertIsNone(backend_view.get_url_for_model(User))


class BackendViewsBackendTestCase(CubaneManualTransactionTestCase):
    @override_settings(INSTALLED_APPS=['cubane.testapp.api'])
    def test_collect_should_install_apis(self):
        backend = Backend()
        self.assertEqual(1, len(backend.apis))
        self.assertIsInstance(backend.apis[0], TestApiView)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_get_section_by_class_should_return_section_by_given_class(self):
        backend = Backend()
        section = backend.get_section_by_class(MediaBackendSection)
        self.assertIsInstance(section, MediaBackendSection)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_get_section_by_class_should_return_none_if_not_found(self):
        backend = Backend()
        section = backend.get_section_by_class(AccountBackendSection)
        self.assertIsNone(section)


    @override_settings(INSTALLED_APPS=[])
    def test_has_sub_sections_should_return_false_if_there_is_no_section_to_begin_with(self):
        backend = Backend()
        self.assertFalse(backend.has_sub_sections)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_has_sub_sections_should_return_false_if_there_is_no_subsection(self):
        backend = Backend()
        for s in backend.sections:
            s.sections = []
        self.assertFalse(backend.has_sub_sections)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_has_sub_sections_should_return_true_if_there_is_at_least_one_subsection(self):
        backend = Backend()
        self.assertTrue(backend.has_sub_sections)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_dispatchable_url_with_none_staff_user_should_return_redirect_response(self):
        response = self._assert_dispatchable_url('test', User(is_staff=False))
        self.assertIsInstance(response, HttpResponseRedirect)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_dispatchable_url_with_anonymous_user_should_return_redirect_response(self):
        response = self._assert_dispatchable_url('test', AnonymousUser())
        self.assertIsInstance(response, HttpResponseRedirect)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_dispatchable_url_with_anonymous_user_accessing_public_url_should_succeed(self):
        for name in Backend.PUBLIC_URL_NAMES:
            response = self._assert_dispatchable_url(name, AnonymousUser())
            self.assertIsInstance(response, HttpResponse)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_dispatchable_url_with_valid_staff_user_should_return_http_response_without_cache_and_expires_header(self):
        response = self._assert_dispatchable_url('test', User(is_staff=True))
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual('no-cache, no-store, max-age=0, must-revalidate', response['Cache-Control'])
        self.assertEqual('Fri, 01 Jan 2010 00:00:00 GMT', response['Expires'])
        self.assertEqual('Foo', response.content)


    def _assert_dispatchable_url(self, name, user):
        backend = Backend()
        section = backend.get_section_by_class(MediaBackendSection)
        subsection = section.get_section_by_class(ImageBackendSection)

        def callback(self):
            return HttpResponse('Foo')

        regexUrl = RegexURLPattern(r'/', callback, name=name)
        backend.dispatchable_url(regexUrl, section, subsection)

        factory = RequestFactory()
        request = factory.get('/')
        request.user = user
        return regexUrl.callback(request)


    @override_settings(INSTALLED_APPS=['cubane.media'])
    def test_index_should_redirect_to_first_visible_section(self):
        backend = Backend()
        admin = User(username='admin', is_staff=True, is_superuser=True)
        response = self.run_view_handler(backend, admin, 'index', 'get', '/admin/')
        self.assertIsRedirect(response, '/admin/images/')


    @override_settings(INSTALLED_APPS=[])
    def test_index_should_render_dashboard_if_no_section_is_available(self):
        backend = Backend()
        admin = User(username='admin', is_staff=True)
        response = self.run_view_handler(backend, admin, 'index', 'get', '/admin/')
        self.assertEqual({}, response)


class BackendViewsLoginBaseTestCase(CubaneTestCase):
    def _assert_login(self, handler_name, url, username, password, is_staff, delete_user=True):
        backend = Backend()
        user = User(username='test', is_staff=is_staff)
        user.set_password('password')
        user.save()

        response = self.run_view_handler(backend, None, handler_name, 'post', url, {
            'username': username,
            'password': password
        })

        if delete_user:
            user.delete()

        return response


@CubaneTestCase.complex()
class BackendViewsLoginTestCase(BackendViewsLoginBaseTestCase):
    def test_login_page_should_present_login_form(self):
        backend = Backend()
        response = self.run_view_handler(backend, None, 'login', 'get', '/admin/login/')
        self.assertIsInstance(response.get('form'), BackendLoginForm)


    def test_login_with_incorrect_username_should_fail(self):
        response = self._assert_login('login', '/admin/login/', 'user-does-not-exist', 'password', is_staff=True)
        self.assertFormError(response.get('form'), BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_login_with_incorrect_password_should_fail(self):
        response = self._assert_login('login', '/admin/login/', 'test', 'password-does-not-match', is_staff=True)
        self.assertFormError(response.get('form'), BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_login_with_non_staff_account_should_fail(self):
        response = self._assert_login('login', '/admin/login/', 'test', 'password', is_staff=False)
        self.assertFormError(response.get('form'), BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


@CubaneTestCase.complex()
class BackendViewsLogoutTestCase(CubaneTestCase):
    def test_logout_without_session_should_redirect_to_login_page(self):
        backend = Backend()
        response = self.run_view_handler(backend, AnonymousUser(), 'logout', 'get', '/admin/logout')
        self.assertIsRedirect(response, reverse('cubane.backend.login'))


    def test_logout_with_session_should_terminate_session_and_redirect_to_login_page(self):
        backend = Backend()

        user = User(username='test', is_staff=True)
        user.set_password('password')
        user.save()

        request, response = self.run_view_handler_request(backend, user, 'logout', 'get', '/admin/logout')
        self.assertTrue(user.is_authenticated())
        self.assertIsRedirect(response, reverse('cubane.backend.login'))

        self.logout(request)
        user.delete()


# TODO: We do not actually have a functional password forgotten workflow yet
@CubaneTestCase.complex()
class BackendViewsPasswordForgottenTestCase(CubaneTestCase):
    def test_password_forgotten_should_present_page(self):
        backend = Backend()
        self.assertRaises(Http404, self.run_view_handler, backend, None, 'password_forgotten', 'get', '/admin/password-forgotten/')


@CubaneTestCase.complex()
class BackendViewsPasswordResetTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendViewsPasswordResetTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('admin', password='password')
        cls.user.is_staff=True
        cls.user.save()
        cls.profile = UserProfile.objects.create(user=cls.user, reset=True)

    @classmethod
    def tearDownClass(cls):
        cls.profile.delete()
        cls.user.delete()
        super(BackendViewsPasswordResetTestCase, cls).tearDownClass()


    def test_without_reset_flag_should_redirect_to_dashboard(self):
        try:
            self.profile.reset = False
            self.profile.save()

            response = self._run_view_handler()
            self.assertIsRedirect(response, reverse('cubane.backend.index'))
        finally:
            self.profile.reset = True
            self.profile.save()


    def test_should_present_form_error_if_password_is_missing(self):
        response = self._run_view_handler({
            'password_confirm': 'password'
        })
        self.assertFormFieldError(response.get('form'), 'password', BackendPasswordResetForm.ERROR_REQUIRED)


    def test_should_present_form_error_if_password_confirm_is_missing(self):
        response = self._run_view_handler({
            'password': 'password'
        })
        self.assertFormFieldError(response.get('form'), 'password_confirm', BackendPasswordResetForm.ERROR_REQUIRED)


    def test_should_present_form_error_if_passwords_do_not_match(self):
        response = self._run_view_handler({
            'password': 'password',
            'password_confirm': 'does-not-match'
        })
        self.assertFormFieldError(response.get('form'), 'password_confirm', BackendPasswordResetForm.ERROR_PASSWORDS_DO_NOT_MATCH)


    def test_should_present_form_error_if_new_password_matches_current_password(self):
        response = self._run_view_handler({
            'password': 'password',
            'password_confirm': 'password'
        })
        self.assertFormFieldError(response.get('form'), 'password', BackendPasswordResetForm.ERROR_PASSWORD_IN_USE)


    def test_should_success_and_redirect_to_dashboard_if_new_password_is_provided(self):
        response = self._run_view_handler({
            'password': 'new-password',
            'password_confirm': 'new-password'
        })
        self.assertIsRedirect(response, reverse('cubane.backend.index'))
        self.assertUserPassword(self.user, 'new-password')


    def _run_view_handler(self, data={}):
        backend = Backend()
        return self.run_view_handler(backend, self.user, 'password_reset', 'post', '/admin/password-reset/', data=data)


@CubaneTestCase.complex()
class BackendViewsHeartbeatTestCase(CubaneTestCase):
    def test_heartbeat_should_deny_GET(self):
        backend = Backend()
        request = self.get_view_handler_request(backend, None, 'hearbeat', 'get', '/admin/hearbeat/')
        response = backend.run_handler(request, 'heartbeat')
        self.assertEqual(405, response.status_code)


    def test_not_matching_session_should_responde_with_error(self):
        backend = Backend()
        request = self.get_view_handler_request(backend, None, 'hearbeat', 'post', '/admin/hearbeat/')
        response = backend.run_handler(request, 'heartbeat')
        json = decode_json(response.content)
        self.assertEqual({'message': 'Reload. no session available.', 'result': 'error', 'taskInfo': None}, json)


    def test_matching_current_session_should_responde_with_success(self):
        user = User(username='test', is_staff=True)
        user.set_password('password')
        user.save()

        backend = Backend()
        request = self.get_view_handler_request(backend, user, 'hearbeat', 'post', '/admin/hearbeat/')

        # log user in
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        self.assertTrue(user.is_authenticated())

        # create session object and patch request
        session_key = '123456789123456789123456789123456789'
        session = Session.objects.create(
            session_key=session_key,
            session_data=Session.objects.encode({'_auth_user_id': user.id}),
            expire_date=datetime.datetime.now() + datetime.timedelta(days=1)
        )
        request.session._session_key = session_key

        # run request and verify that we get successful responde
        response = backend.run_handler(request, 'heartbeat')
        json = decode_json(response.content)
        self.assertEqual({'result': 'Success', 'taskInfo': None}, json)
