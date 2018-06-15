# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils.module_loading import import_module
from cubane.views import ModelView
from cubane.backend.views import BackendSection
from cubane.backend.accounts.forms import AccountForm, GroupForm, PermissionForm
from cubane.backend.accounts.forms import ChangePasswordForm
from cubane.backend.accounts.models import ProxyUser, ProxyGroup, ProxyPermission
from cubane.lib.module import register_class_extensions
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class AccountView(ModelView):
    """
    Edit staff accounts. Staff members can edit other staff member accounts but
    cannot edit superuser accounts. Superuser accounts can edit all staff member
    accounts and superuser accounts.
    """
    namespace = 'cubane.backend.accounts'
    template_path = 'cubane/backend/accounts/'
    model = ProxyUser
    form = AccountForm

    patterns = (
        ('change-password/', 'change_password', {}, 'change_password'),
    )

    listing_actions = (
        ('[Change Password]', 'change_password', 'single'),
    )

    shortcut_actions = [
        'change_password'
    ]


    @classmethod
    def register_extension(cls, *args):
        """
        Register a new extension(s) for the accounts view class.
        """
        return register_class_extensions('ExtendedAccountsView', cls, args)


    def _get_objects(self, request):
        """
        - Staff members can see all staff members but not superusers.
        - Superusers can see all staff members and superusers.
        """
        if request.user.is_superuser:
            return ProxyUser.objects.filter(
                Q(is_staff=True) |
                Q(is_superuser=True)
            )
        else:
            return ProxyUser.objects.filter(
                is_staff=True
            ).exclude(
                is_superuser=True
            )


    def before_save(self, request, d, instance, edit):
        # every user we create is a staff member.
        if instance and not edit:
            instance.is_staff = True

        # when creating a new user, set the initial password if available
        if not edit and 'initial_password' in d:
            instance.set_password(d.get('initial_password'))


    def change_password(self, request):
        """
        Change password for selected user.
        """
        pk = request.GET.get('pk', None)
        account = self.get_object_or_404(request, pk)

        if request.method == 'POST':
            form = ChangePasswordForm(request.POST)
        else:
            form = ChangePasswordForm()

        form.configure(request)

        if request.method == 'POST' and form.is_valid():
            # change user's password
            d = form.cleaned_data
            account.set_password(d['password'])
            account.save()

            # keep session alive; otherwise the user would need to re-login
            update_session_auth_hash(request, account)

            # flash message
            messages.add_message(
                request,
                messages.SUCCESS,
                'Password for user <em>%s</em> successfully changed.' % account.username,
                extra_tags='safe'
            )
            return self._redirect(request, 'index')

        return {
            'form': form,
            'account': account
        }


class AccountBackendSubSection(BackendSection):
    """
    Backend sub-section for managing staff user accounts.
    """
    title = 'User Accounts'
    slug = 'accounts'


    def __init__(self, *args, **kwargs):
        super(AccountBackendSubSection, self).__init__(*args, **kwargs)
        self.view = self.get_account_view()


    def get_account_view(self):
        """
        Return a new instance of the account view.
        """
        _class = AccountView

        # give each module the chance to extend the base class
        for app_name in settings.INSTALLED_APPS:
            app = import_module(app_name)
            if hasattr(app, 'install_account_view'):
                _class = app.install_account_view(_class)

        # creates a new instance
        return _class()


class AccountBackendSection(BackendSection):
    """
    Backend section for managing staff user accounts, roles and permissions.
    """
    title = 'User Accounts'
    slug = 'accounts'
    priority = -1
    sections = [
        AccountBackendSubSection()
    ]