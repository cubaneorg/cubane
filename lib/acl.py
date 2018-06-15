# coding=UTF-8
from __future__ import unicode_literals


class Acl(object):
    """
    Provides helper functions for querying access control information for
    models. Access control information is only applicable to staff members
    using the backend system without superuser privileges.
    """
    DEFAULT_ACL = {}


    NONE   = 0
    ALL    = 1
    OWN    = 2


    def __init__(self, model, *args, **kwargs):
        """
        Create a new ACL representation based on the given string.
        """
        from django.conf import settings

        def _default(name):
            return settings.CUBANE_BACKEND_DEFAULT_ACL.get(name, Acl.NONE)

        def _kwargs(name):
            return kwargs.get(name, _default(name))

        self._model = model
        self._create = _kwargs('create')
        self._read   = _kwargs('read')
        self._update = _kwargs('update')
        self._delete = _kwargs('delete')
        self._import = _kwargs('data_import')
        self._export = _kwargs('data_export')
        self._merge  = _kwargs('merge')


    @classmethod
    def default(cls, model):
        """
        Return the default ACL.
        """
        acl = cls.DEFAULT_ACL.get(model)
        if not acl:
            acl = cls.DEFAULT_ACL[model] = Acl(model)

        return acl


    @classmethod
    def of(cls, model):
        """
        Return the Acl for the given model.
        """
        if model:
            if not hasattr(model, '_acl'):
                model._acl = Acl.default(model)

                from django.conf import settings
                if hasattr(settings, 'CUBANE_BACKEND_ACL'):
                    if settings.CUBANE_BACKEND_ACL:
                        acl_class = settings.CUBANE_BACKEND_ACL.get(model.__name__)
                        if acl_class:
                            if hasattr(acl_class, 'acl'):
                                model._acl = acl_class.parse(model, acl_class.acl)
                            else:
                                model._acl = acl_class(model)

            return model._acl

        return Acl.default(model)


    @classmethod
    def parse(cls, model, s):
        """
        Parse ACL information from the given compact string representation in
        the format C/R/U/D or C/R1/U1/D1.
        """
        if s and isinstance(s, basestring):
            parts = s.upper().split('/')
            parts = [p.strip() for p in parts]
            parts = filter(lambda x: x, parts)

            def parse_rule(allowed_parts):
                s = None
                for p in allowed_parts:
                    if p in parts:
                        s = p
                        break

                if s:
                    if s in ['C', 'R', 'U', 'D', 'I', 'E', 'M']:
                        return Acl.ALL
                    elif s in ['R1', 'U1', 'D1']:
                        return Acl.OWN

                return Acl.NONE

            return cls(
                model,
                create=parse_rule(['C']),
                read=parse_rule(['R', 'R1']),
                update=parse_rule(['U', 'U1']),
                delete=parse_rule(['D', 'D1']),
                data_import=parse_rule(['I']),
                data_export=parse_rule(['E']),
                merge=parse_rule(['M'])
            )

        return cls.default(model)


    @property
    def model(self):
        return self._model


    @property
    def create(self):
        return self._create != Acl.NONE


    @property
    def read(self):
        return self._read == Acl.ALL


    @property
    def read1(self):
        return self._read == Acl.OWN


    @property
    def update(self):
        return self._update == Acl.ALL


    @property
    def update1(self):
        return self._update == Acl.OWN


    @property
    def delete(self):
        return self._delete == Acl.ALL


    @property
    def delete1(self):
        return self._delete == Acl.OWN


    @property
    def data_import(self):
        return self._import == Acl.ALL


    @property
    def data_export(self):
        return self._export == Acl.ALL


    @property
    def merge(self):
        return self._merge == Acl.ALL


    def can(self, view):
        """
        Return True, if this ACL allows the given view operation to be performed.
        """
        if view == 'add':
            return self.create
        elif view == 'view':
            return self.read or self.read1
        elif view == 'edit':
            return self.update or self.update1
        elif view == 'delete':
            return self.delete or self.delete1
        elif view == 'import':
            return self.data_import
        elif view == 'export':
            return self.data_export
        elif view == 'merge':
            return self.merge
        else:
            return False


    def filter(self, request, objects):
        """
        Return a queryset that confirms to ACL rules of this model view.
        """
        if not request.user.is_superuser:
            if self.read1:
                objects = self.belongs_to_user(request, objects, request.user)
            elif not self.read:
                objects = objects.none()

        return objects


    def belongs_to_user(self, request, objects, user):
        """
        Virtual: Customise the given queryset to filter for objects that
        only belong to the given user.
        """
        return objects.filter(created_by=user)


    def can_edit_instance(self, request, instance):
        """
        Return True, if the current user has permission to edit the given instance.
        """
        # cannot check instance that is None
        if instance is None:
            return False

        # instance must be of same class
        if instance.__class__ != self._model:
            return False

        # need request and user
        if request is None or request.user is None:
            return False

        # superuser can edit everything regardless
        if request.user.is_superuser:
            return True

        # edit permission on all instances would allow us to edit
        if self.update:
            return True

        # if we only have access to some instances, run user code to make that
        # decision for us...
        if self.update1:
            return self.user_can_edit_instance(request.user, instance)

        # no access
        return False


    def user_can_edit_instance(self, user, instance):
        """
        Virtual: Decide if a user can edit the given instance assuming that
        the user does not have general edit permissions for all instances.
        """
        # by default, we are allowed to edit an instance that the user created
        return instance.created_by_id == user.pk


    def __str__(self):
        return self.__unicode__()


    def __repr__(self):
        return self.__unicode__()


    def __unicode__(self):
        def display(prefix, r):
            if r == Acl.ALL:
                return prefix
            elif r == Acl.OWN:
                return prefix + '1'
            else:
                return '-'

        return '/'.join([
            display('C', self._create),
            display('R', self._read),
            display('U', self._update),
            display('D', self._delete)
        ])