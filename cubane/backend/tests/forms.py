# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.contrib.auth.models import User
from cubane.forms import BaseLoginForm
from cubane.tests.base import CubaneTestCase
from cubane.backend.forms import BackendLoginForm
from cubane.backend.forms import BackendPasswordResetForm
from cubane.backend.forms import BrowseSelect
from cubane.backend.forms import BrowseSelectThumbnail
from cubane.backend.forms import BrowseField
from cubane.backend.forms import BrowseChoiceField
from cubane.backend.forms import BrowseTreeField
from cubane.backend.forms import GalleryField
from cubane.backend.forms import ModelCollectionField
from cubane.backend.forms import ModelSelectMultiple
from cubane.media.models import Media
from cubane.cms.models import Page
from cubane.testapp.models import Enquiry, TestTreeNode
from cubane.testapp.forms import TestGalleryFieldForm, TestModelCollectionFieldForm


class BackendLoginFormTestCase(CubaneTestCase):
    def test_username_should_be_required(self):
        form = BackendLoginForm({'password': 'password'})
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'username', BackendLoginForm.ERROR_REQUIRED)


    def test_password_should_be_required(self):
        form = BackendLoginForm({'username': 'does-not-exist'})
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(form, 'password', BackendLoginForm.ERROR_REQUIRED)


    def test_login_should_fail_with_unknown_user(self):
        form = BackendLoginForm({'username': 'does-not-exist', 'password': 'password'})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)


    def test_login_should_fail_with_incorrect_password(self):
        user = self._create_user('test', 'password', is_staff=True)
        form = BackendLoginForm({'username': 'test', 'password': 'incorrect-password'})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)
        user.delete()


    def test_login_should_fail_with_non_staff_privileges(self):
        user = self._create_user('test', 'password', is_staff=False)
        form = BackendLoginForm({'username': 'test', 'password': 'password'})
        self.assertFalse(form.is_valid())
        self.assertFormError(form, BaseLoginForm.ERROR_INVALID_USERNAME_OR_PASSWORD)
        user.delete()


    def test_staff_account_with_correct_credentials_should_succeed(self):
        user = self._create_user('test', 'password', is_staff=True)
        form = BackendLoginForm({'username': 'test', 'password': 'password'})
        form._request = False
        self.assertTrue(form.is_valid())
        user.delete()


    def _create_user(self, username, password, is_staff):
        user = User(username=username, is_staff=is_staff)
        user.set_password(password)
        user.save()
        return user


class BackendPasswordResetFormTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(BackendPasswordResetFormTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('admin2', password='password')


    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        super(BackendPasswordResetFormTestCase, cls).tearDownClass()


    def setUp(self):
        self.request = self.make_request('post', '/', user=self.user)


    def test_password_should_be_required(self):
        form = BackendPasswordResetForm({'password_confirm': 'password'})
        form.configure(self.request)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(
            form,
            'password',
            BackendPasswordResetForm.ERROR_REQUIRED
        )


    def test_password_confirm_should_be_required(self):
        form = BackendPasswordResetForm({'password': 'password'})
        form.configure(self.request)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(
            form,
            'password_confirm',
            BackendPasswordResetForm.ERROR_REQUIRED
        )


    def test_password_should_match_password_confirmation(self):
        form = BackendPasswordResetForm({\
            'password': 'password',
            'password_confirm': 'does-not-match'
        })
        form.configure(self.request)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(
            form,
            'password_confirm',
            BackendPasswordResetForm.ERROR_PASSWORDS_DO_NOT_MATCH
        )


    def test_should_not_accept_current_password_as_new_password(self):
        form = BackendPasswordResetForm({\
            'password': 'password',
            'password_confirm': 'password'
        })
        form.configure(self.request)
        self.assertFalse(form.is_valid())
        self.assertFormFieldError(
            form,
            'password',
            BackendPasswordResetForm.ERROR_PASSWORD_IN_USE
        )


    def test_should_succeed_if_a_new_password_has_been_choosen_and_confirmed(self):
        form = BackendPasswordResetForm({\
            'password': 'new-password',
            'password_confirm': 'new-password'
        })
        form.configure(self.request)
        self.assertTrue(form.is_valid())


class BrowseSelectTestCase(CubaneTestCase):
    def setUp(self):
        self.choices = (
            ('1','test 1'),
            ('2','test 2'),
            ('3','test 3'),
        )

    def test_should_render_browse_select(self):
        field = BrowseSelect(choices=self.choices)
        html = field.render('fieldname', '2')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'option', {'value': '1'}, 'test 1')
        self.assertMarkup(html, 'option', {'value': '2', 'selected': True}, 'test 2')
        self.assertMarkup(html, 'option', {'value': '3'}, 'test 3')


    def test_should_render_browse_select_and_browse_button(self):
        field = BrowseSelect(choices=self.choices, attrs={'browse': 'Browse', 'name': 'Model'})
        html = field.render('fieldname', '3')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'option', {'value': '1'}, 'test 1')
        self.assertMarkup(html, 'option', {'value': '2'}, 'test 2')
        self.assertMarkup(html, 'option', {'value': '3', 'selected': True}, 'test 3')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-button'})
        self.assertMarkup(html, 'span', {
            'class': 'btn',
            'data-browse-url': 'Browse',
            'data-model-name': 'Model'
        })


    def test_should_render_browse_select_and_create_button(self):
        field = BrowseSelect(choices=self.choices, attrs={'create': 'Create', 'name': 'Model'})
        html = field.render('fieldname', '1')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'option', {'value': '1', 'selected': True}, 'test 1')
        self.assertMarkup(html, 'option', {'value': '2'}, 'test 2')
        self.assertMarkup(html, 'option', {'value': '3'}, 'test 3')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-add-button'})
        self.assertMarkup(html, 'span', {
            'class': 'btn',
            'data-create-url': 'Create',
            'data-model-name': 'Model'
        })


    def test_should_render_browse_select_and_all_buttons(self):
        field = BrowseSelect(choices=self.choices, attrs={'name': 'MyModel', 'create': 'MyCreate', 'browse': 'MyBrowse'})
        html = field.render('myfieldname', '2')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'myfieldname'})
        self.assertMarkup(html, 'option', {'value': '1'}, 'test 1')
        self.assertMarkup(html, 'option', {'value': '2', 'selected': True}, 'test 2')
        self.assertMarkup(html, 'option', {'value': '3'}, 'test 3')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-button'})
        self.assertMarkup(html, 'span', {
            'class': 'btn',
            'data-browse-url': 'MyBrowse',
            'data-model-name': 'MyModel'
        })
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-add-button'})
        self.assertMarkup(html, 'span', {
            'class': 'btn',
            'data-create-url': 'MyCreate',
            'data-model-name': 'MyModel'
        })


class BrowseSelectThumbnailTestCase(CubaneTestCase):
    def setUp(self):
        self.choices = (
            ('1','test 1'),
            ('2','test 2'),
            ('3','test 3'),
        )


    def test_should_render_thumbnail_for_browse_select(self):
        field = BrowseSelectThumbnail(choices=self.choices)

        self.assertEqual(
            '<div class="cubane-backend-browse-thumbnail" data-pk="None" data-browse-url="" data-create-url="" data-edit-url="" data-model-name=""><div role="button" class="cubane-backend-browse-thumbnail-remove" title="Remove Image"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg></div><a href="" class="cubane-backend-browse-thumbnail-enlarge cubane-lightbox" title="Enlarge Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-enlarge"/></svg></a><div role="button" class="cubane-backend-browse-thumbnail-edit" title="Edit Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-edit"/></svg></div><div role="button" class="cubane-backend-browse-thumbnail-upload" title="Upload New Image"><svg viewBox="0 0 64 64"><use xlink:href="#icon-upload"/></svg></div><input type="hidden" name="fieldname" id="" value="1"/><div role="button" class="cubane-backend-browse-thumbnail-image" title="Choose Image"></div></div>',
            field.render('fieldname', '1')
        )


    def test_should_render_thumbnail_for_browse_select_with_id(self):
        field = BrowseSelectThumbnail(choices=self.choices)

        self.assertEqual(
            '<div class="cubane-backend-browse-thumbnail" data-pk="None" data-browse-url="" data-create-url="" data-edit-url="" data-model-name=""><div role="button" class="cubane-backend-browse-thumbnail-remove" title="Remove Image"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg></div><a href="" class="cubane-backend-browse-thumbnail-enlarge cubane-lightbox" title="Enlarge Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-enlarge"/></svg></a><div role="button" class="cubane-backend-browse-thumbnail-edit" title="Edit Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-edit"/></svg></div><div role="button" class="cubane-backend-browse-thumbnail-upload" title="Upload New Image"><svg viewBox="0 0 64 64"><use xlink:href="#icon-upload"/></svg></div><input type="hidden" name="fieldname" id="myid" value="2"/><div role="button" class="cubane-backend-browse-thumbnail-image" title="Choose Image"></div></div>',
            field.render('fieldname', '2', attrs={'id': 'myid'})
        )


    def test_should_render_thumbnail_for_browse_select_with_none_value_as_empty_string(self):
        field = BrowseSelectThumbnail(choices=self.choices)

        self.assertEqual(
            '<div class="cubane-backend-browse-thumbnail" data-pk="None" data-browse-url="" data-create-url="" data-edit-url="" data-model-name=""><div role="button" class="cubane-backend-browse-thumbnail-remove" title="Remove Image"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg></div><a href="" class="cubane-backend-browse-thumbnail-enlarge cubane-lightbox" title="Enlarge Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-enlarge"/></svg></a><div role="button" class="cubane-backend-browse-thumbnail-edit" title="Edit Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-edit"/></svg></div><div role="button" class="cubane-backend-browse-thumbnail-upload" title="Upload New Image"><svg viewBox="0 0 64 64"><use xlink:href="#icon-upload"/></svg></div><input type="hidden" name="fieldname" id="myid" value=""/><div role="button" class="cubane-backend-browse-thumbnail-image" title="Choose Image"></div></div>',
            field.render('fieldname', None, attrs={'id': 'myid'})
        )


    def test_should_render_thumbnail_for_browse_select_with_data_name_and_browse(self):
        field = BrowseSelectThumbnail(choices=self.choices, attrs={'data_name': 'MyDataName', 'browse': 'MyBrowse'})

        self.assertEqual(
            '<div class="cubane-backend-browse-thumbnail" data-pk="None" data-browse-url="MyBrowse" data-create-url="" data-edit-url="" data-model-name="MyDataName"><div role="button" class="cubane-backend-browse-thumbnail-remove" title="Remove Image"><svg viewBox="0 0 9.5 12"><use xlink:href="#icon-delete"/></svg></div><a href="" class="cubane-backend-browse-thumbnail-enlarge cubane-lightbox" title="Enlarge Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-enlarge"/></svg></a><div role="button" class="cubane-backend-browse-thumbnail-edit" title="Edit Image"><svg viewBox="0 0 13.5 13.3"><use xlink:href="#icon-edit"/></svg></div><div role="button" class="cubane-backend-browse-thumbnail-upload" title="Upload New Image"><svg viewBox="0 0 64 64"><use xlink:href="#icon-upload"/></svg></div><input type="hidden" name="fieldname" id="myid" value="3"/><div role="button" class="cubane-backend-browse-thumbnail-image" title="Choose Image"></div></div>',
            field.render('fieldname', '3', attrs={'id': 'myid'})
        )


    def test_should_render_thumbnail_for_browse_with_image(self):
        image = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)
        field = BrowseSelectThumbnail(choices=self.choices)

        self.assertIn(
            'class="cubane-backend-browse-thumbnail',
            field.render('fieldname', image.pk)
        )


class BackendBrowseFieldTestCase(CubaneTestCase):
    def test_should_render_correct_markup(self):
        field = BrowseField(queryset=Enquiry.objects.all(), name='Name', browse='browse', create='create')
        html = field.widget.render('fieldname', 'fieldvalue')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'option', {'value': ''}, '---------')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-button'})
        self.assertMarkup(html, 'span', {'class': 'btn', 'data-browse-url': 'browse', 'data-model-name': 'Name'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-add-button'})
        self.assertMarkup(html, 'span', {'class': 'btn', 'data-create-url': 'create', 'data-model-name': 'Name'})


class BackendBrowseChoiceFieldTestCase(CubaneTestCase):
    def test_should_render_correct_markup(self):
        field = BrowseChoiceField(choices=(), name='Name', browse='browse', create='create')
        html = field.widget.render('fieldname', 'fieldvalue')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-button'})
        self.assertMarkup(html, 'span', {'class': 'btn', 'data-browse-url': 'browse', 'data-model-name': 'Name'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-add-button'})
        self.assertMarkup(html, 'span', {'class': 'btn', 'data-create-url': 'create', 'data-model-name': 'Name'})


class BackendBrowseTreeFieldTestCase(CubaneTestCase):
    def test_should_render_correct_markup(self):
        a = TestTreeNode.objects.create(title='a', seq=1)
        a1 = TestTreeNode.objects.create(title='a.1', parent=a, seq=1)
        a2 = TestTreeNode.objects.create(title='a.2x', parent=a, seq=2)
        b = TestTreeNode.objects.create(title='b', seq=2)

        field = BrowseTreeField(model=TestTreeNode)
        html = field.widget.render('fieldname', 'fieldvalue')
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse clearfix'})
        self.assertMarkup(html, 'div', {'class': 'cubane-backend-browse-select'})
        self.assertMarkup(html, 'select', {'name': 'fieldname'})
        self.assertMarkup(html, 'option', {'value': ''}, '---------')
        self.assertMarkup(html, 'option', {'value': '1'}, 'a')
        self.assertMarkup(html, 'option', {'value': '2'}, '&nbsp;&nbsp;a.1')
        self.assertMarkup(html, 'option', {'value': '3'}, '&nbsp;&nbsp;a.2x')
        self.assertMarkup(html, 'option', {'value': '4'}, 'b')

        b.delete()
        a2.delete()
        a1.delete()
        a.delete()


class ModelSelectMultipleTestCase(CubaneTestCase):
    def setUp(self):
        self.image = Media.objects.create(caption='My Picture', filename='a.jpg', is_image=True, width=512, height=512)
        self.queryset = Media.objects.all()


    def test_should_render_model_select_multiple(self):
        html = ModelSelectMultiple(attrs={'queryset': self.queryset}).render('fieldname', [])

        self.assertEqual(
            '<div class="cubane-collection-items" data-name="fieldname" data-url="" data-alt-url="" data-title="Collection" data-model-title="" data-alt-model-title="" data-sortable="True" data-allow-duplicates="True" data-max-items="None">\n' +
            '<div class="cubane-collection-items-header">\n' +
            '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> Add...</a>\n' +
            '\n' +
            '</div>\n' +
            '<div class="cubane-collection-items-container cubane-listing-grid-items ui-sortable">\n' +
            '</div></div>',
            html
        )


    def test_should_render_model_select_multiple_with_all_attributes(self):
        attrs  = {
            'queryset': self.queryset,
            'url': 'myurl',
            'title': 'mytitle',
            'model_title': 'mymodeltitle'
        }
        html = ModelSelectMultiple(attrs=attrs).render('fieldname', [])

        self.assertEqual(
            '<div class="cubane-collection-items" data-name="fieldname" data-url="myurl" data-alt-url="" data-title="mytitle" data-model-title="mymodeltitle" data-alt-model-title="" data-sortable="True" data-allow-duplicates="True" data-max-items="None">\n' +
            '<div class="cubane-collection-items-header">\n' +
            '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> Add...</a>\n' +
            '\n' +
            '</div>\n' +
            '<div class="cubane-collection-items-container cubane-listing-grid-items ui-sortable">\n' +
            '</div></div>',
            html
        )


    def test_should_render_model_select_multiple_with_sortable_class(self):
        attrs = {
            'queryset': self.queryset,
            'sortable': True
        }

        html = ModelSelectMultiple(attrs=attrs).render('fieldname', [])

        self.assertEqual(
            '<div class="cubane-collection-items" data-name="fieldname" data-url="" data-alt-url="" data-title="Collection" data-model-title="" data-alt-model-title="" data-sortable="True" data-allow-duplicates="True" data-max-items="None">\n' +
            '<div class="cubane-collection-items-header">\n' +
            '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> Add...</a>\n' +
            '\n' +
            '</div>\n' +
            '<div class="cubane-collection-items-container cubane-listing-grid-items ui-sortable">\n' +
            '</div></div>',
            html
        )


    def test_should_render_model_select_multiple_as_listing_list(self):
        attrs = {
            'queryset': self.queryset,
            'viewmode': ModelCollectionField.VIEWMODE_LIST
        }

        html = ModelSelectMultiple(attrs=attrs).render('fieldname', [])

        self.assertEqual(
            '<div class="cubane-collection-items" data-name="fieldname" data-url="" data-alt-url="" data-title="Collection" data-model-title="" data-alt-model-title="" data-sortable="True" data-allow-duplicates="True" data-max-items="None">\n' +
            '<div class="cubane-collection-items-header">\n' +
            '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> Add...</a>\n' +
            '\n' +
            '</div>\n' +
            '<div class="cubane-collection-items-container cubane-listing-list ui-sortable">\n' +
            '</div></div>',
            html
        )


    def test_should_render_model_select_multiple_with_none_value(self):
        html = ModelSelectMultiple(attrs={'queryset': self.queryset}).render('fieldname', None)

        self.assertEqual(
            '<div class="cubane-collection-items" data-name="fieldname" data-url="" data-alt-url="" data-title="Collection" data-model-title="" data-alt-model-title="" data-sortable="True" data-allow-duplicates="True" data-max-items="None">\n' +
            '<div class="cubane-collection-items-header">\n' +
            '<a class="add-collection-items btn btn-primary" href="#add-collection-items"><i class="icon icon-plus"></i> Add...</a>\n' +
            '\n' +
            '</div>\n' +
            '<div class="cubane-collection-items-container cubane-listing-grid-items ui-sortable">\n' +
            '</div></div>',
            html
        )


    def test_should_render_model_select_multiple_with_one_item(self):
        html = ModelSelectMultiple(attrs={'queryset': self.queryset}).render('fieldname', [self.image.pk])
        self.assertIn('<div class="cubane-collection-items" data-name="fieldname"', html)
        self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="My Picture" data-id="%s">' % self.image.pk, html)
        self.assertIn('data-background-image data-shape="original" data-path="/0/%d/a.jpg"' % self.image.pk, html)


class BackendGalleryFieldTestCase(CubaneTestCase):
    def test_should_render_correct_markup(self):
        m1 = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)
        m2 = Media.objects.create(caption='B Picture', filename='b.jpg', is_image=True, width=512, height=512)
        try:
            field = GalleryField(queryset=Media.objects.all())
            markup = field.widget.render('fieldname', [m1.pk, m2.pk, 999])
            self.assertIn('class="cubane-collection-items"', markup)
            self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="A Picture" data-id="%d">' % m1.pk, markup)
            self.assertIn('data-background-image data-shape="original" data-path="/0/%d/a.jpg"' % m1.pk, markup)
            self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="B Picture" data-id="%d">' % m2.pk, markup)
            self.assertIn('data-background-image data-shape="original" data-path="/0/%d/b.jpg"' % m2.pk, markup)

            # 999 is not a valid object
            self.assertNotIn('999', markup)
        finally:
            m1.delete()
            m2.delete()


    def test_should_skip_not_allowed_values(self):
        m1 = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)
        m2 = Media.objects.create(caption='B Picture', filename='b.jpg', is_image=True, width=512, height=512)
        try:
            # skip m1, only m2 should appear...
            field = GalleryField(queryset=Media.objects.filter(pk=m2.pk))
            markup = field.widget.render('fieldname', [m1.pk, m2.pk])
            self.assertIn('class="cubane-collection-items"', markup)
            self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="B Picture" data-id="%d">' % m2.pk, markup)
            self.assertIn('data-background-image data-shape="original" data-path="/0/%d/b.jpg"' % m2.pk, markup)
        finally:
            m1.delete()
            m2.delete()


    def test_clean_return_model_instances_in_seq(self):
        m1 = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)
        m2 = Media.objects.create(caption='B Picture', filename='b.jpg', is_image=True, width=512, height=512)
        try:
            form = TestGalleryFieldForm({'images': [m2.pk, m1.pk]})
            self.assertTrue(form.is_valid())
            self.assertEqual([m2, m1], form.cleaned_data.get('images'))
        finally:
            m1.delete()
            m2.delete()


    def test_clean_should_return_empty_queryset_if_not_required_and_no_value(self):
        form = TestGalleryFieldForm({'images': None})
        form.fields['images'].required = False
        self.assertTrue(form.is_valid())
        self.assertEqual(0, len(form.cleaned_data.get('images')))


    def test_clean_should_not_accept_values_that_are_not_lists(self):
        form = TestGalleryFieldForm({'images': 'not a list'})
        self.assertFalse(form.is_valid())
        self.assertEqual({'images': ['Enter a list of values.']}, form.errors)


    def test_clean_should_not_accept_invalid_pk_value(self):
        form = TestGalleryFieldForm({'images': ['not a valid pk value']})
        self.assertFalse(form.is_valid())
        self.assertEqual({'images': ['"not a valid pk value" is not a valid value for a primary key.']}, form.errors)


    def test_clean_should_trigger_error_for_required_field_with_no_value(self):
        form = TestGalleryFieldForm({'images': None})
        self.assertFalse(form.is_valid())
        self.assertEqual({'images': ['This field is required.']}, form.errors)


    def test_clean_should_validate_for_correct_values_matching_choices(self):
        m1 = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)

        form = TestGalleryFieldForm({'images': [m1.pk, 999]})
        self.assertFalse(form.is_valid())
        self.assertEqual({'images': ['Select a valid choice. 999 is not one of the available choices.']}, form.errors)

        m1.delete()


class BackendModelCollectionFieldTestCase(CubaneTestCase):
    def test_should_render_correct_markup_for_entities_with_image(self):
        m = Media.objects.create(caption='A Picture', filename='a.jpg', is_image=True, width=512, height=512)
        p1 = Page.objects.create(title='A', slug='a', image=m)
        p2 = Page.objects.create(title='B', slug='b', image=m)
        try:
            field = ModelCollectionField(queryset=Page.objects.all())
            html = field.widget.render('fieldname', [p1.pk, p2.pk, 999])
            self.assertIn('value="%s"' % p1.pk, html)
            self.assertIn('value="%s"' % p2.pk, html)
            self.assertNotIn('value="%s"' % 999, html)
            self.assertIn('data-background-image data-shape="original" data-path="/0/%d/a.jpg"' % m.pk, html)
        finally:
            p1.delete()
            p2.delete()


    def test_should_render_correct_markup_for_entities_without_image(self):
        p1 = Page.objects.create(title='A', slug='a')
        p2 = Page.objects.create(title='B', slug='b')

        field = ModelCollectionField(queryset=Page.objects.all())
        html = field.widget.render('fieldname', [p1.pk, p2.pk, 999])

        self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="A" data-id="%s">' % p1.pk, html)
        self.assertIn('<div class="cubane-listing-item collection-item cubane-listing-grid-item" title="B" data-id="%s">' % p2.pk, html)

        p1.delete()
        p2.delete()


    def test_clean_return_model_instances_in_seq(self):
        p1 = Page.objects.create(title='A', slug='a')
        p2 = Page.objects.create(title='B', slug='b')

        form = TestModelCollectionFieldForm({'pages': [p1.pk, p2.pk]})
        self.assertTrue(form.is_valid())
        self.assertEqual([p1, p2], form.cleaned_data.get('pages'))

        p1.delete()
        p2.delete()
