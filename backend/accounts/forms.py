# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.contrib.auth.models import User, Group
from cubane.forms import BaseModelForm, BaseForm
from cubane.backend.accounts.models import ProxyUser, ProxyGroup, ProxyPermission


class AccountForm(BaseModelForm):
    """
    Form for editing staff accounts.
    """
    class Meta:
        model = ProxyUser
        fields = '__all__'
        exclude = ['password', 'date_joined', 'is_staff', 'last_login', 'user_permissions']
        section_fields = [
            ':Account Details',
            'username',
            'first_name',
            'last_name',
            'email',
            'initial_password',
            'initial_password_confirm',

            ':Permissions',
            'is_active',
            'is_superuser',
            'groups'
        ]


    initial_password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        help_text='Provide the initial password for this user account.'
    )

    initial_password_confirm = forms.CharField(
        label='Password (confirm)',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (confirm)'}),
        help_text='Confirm the password by re-typing the password from above.'
    )


    def configure(self, request, instance, edit):
        super(AccountForm, self).configure(request, instance, edit)

        # Only superuser can change superuser field.
        if not request.user.is_superuser:
            del self.fields['is_superuser']

        # password confirmation only available for create
        if edit:
            del self.fields['initial_password']
            del self.fields['initial_password_confirm']
            self.update_sections()

        # do not present groups if we do not have groups available
        if Group.objects.count() == 0:
            del self.fields['groups']
            self.update_sections()


    def clean_username(self):
        d = self.cleaned_data
        username = d.get('username')

        if username:
            username = username.lower()

            # username must be unique
            users = User.objects.filter(username__iexact=username)
            if self._edit and self._instance:
                users = users.exclude(pk=self._instance.pk)
            if users.count() > 0:
                raise forms.ValidationError('A user with that username already exists.')

        return username


    def clean_email(self):
        d = self.cleaned_data
        email = d.get('email')

        if email:
            email = email.lower()

            # email must be unique
            users = User.objects.filter(email__iexact=email)
            if self._edit and self._instance:
                users = users.exclude(pk=self._instance.pk)
            if users.count() > 0:
                raise forms.ValidationError('A user with that email address already exists.')

        return email


    def clean_initial_password_confirm(self):
        password = self.cleaned_data.get('initial_password', None)
        password_confirm = self.cleaned_data.get('initial_password_confirm', None)

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Password Confirmation does not match Password.')

        return password_confirm


class GroupForm(BaseModelForm):
    """
    Form for editing account groups.
    """
    class Meta:
        model = ProxyGroup
        fields = '__all__'


class PermissionForm(BaseModelForm):
    """
    Form for editing user permissions.
    """
    class Meta:
        model = ProxyPermission
        fields = '__all__'


class ChangePasswordForm(BaseForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )

    password_confirm = forms.CharField(
        label='Password (confirm)',
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (confirm)'})
    )

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password', None)
        password_confirm = self.cleaned_data.get('password_confirm', None)

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Password Confirmation does not match Password.')

        return password_confirm
