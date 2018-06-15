# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.contenttypes.models import ContentType
from django.db.models import FileField as DjangoFileField
from django.db.models import ManyToManyField
from django.db.models.fields.related import RelatedField
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from cubane.lib.model import get_model_field_names
from cubane.lib.libjson import to_json
from cubane.lib.app import get_models
from cubane.backend.models import ChangeLog
import datetime
import random
import hashlib
import string


class ChangeLogManager(object):
    def __init__(self, request):
        """
        Create a new (empty) changelog manager, ready to record and commit.
        """
        self._request = request
        self._classes = {}
        self._log = []
        self._parent_log = None
        self._commited = False


    def get_changes(self, a, b=None):
        """
        Return a structure in JSON that describes the changes that occurred for
        the given model a (before the change) and b (after the change).
        """
        # nothing to work with
        if a is None and b is None:
            return None

        # identify model class and get list of known models
        _class = a.__class__
        models = get_models()

        # identify all database columns from model
        fieldnames = get_model_field_names(_class)

        # generate index over b (if available)
        index = {}
        if b is not None:
            for entry in b:
                index[entry.get('n')] = entry.get('a')

        def _array_equal(ass, bss):
            if len(ass) != len(bss):
                return False

            for i, a in enumerate(ass):
                if a != bss[i]:
                    return False

            return True

        # generate changes
        result = []
        for fieldname in fieldnames:
            # get field is model
            field = _class._meta.get_field(fieldname)

            # ignore file fields
            if isinstance(field, DjangoFileField):
                continue

            # get previous value (b)
            if b is not None:
                vb = index.get(field.attname)
            else:
                vb = None

            # get current and previous values
            if field.many_to_many:
                # ignore ManyToMany with through model. It will be picked up
                # by collecting related objects
                has_through_model = False
                for m in models:
                    if issubclass(field.rel.through, m):
                        has_through_model = True
                        break
                if has_through_model:
                    continue

                # get list of pk's for many-to-many related objects
                if a.pk:
                    va = getattr(a, field.name)
                    if va is not None: va = [x.pk for x in va.all()]
                else:
                    va = []
            else:
                va = getattr(a, field.attname)

            # value changed?
            changed = False
            if b is not None:
                if isinstance(va, list) and isinstance(vb, list):
                    changed = not _array_equal(va, vb)
                else:
                    changed = va != vb

            if b is None or changed:
                result.append({
                    'n': field.attname,
                    'a': va,
                    'b': vb
                })
        return result


    def create(self, instance):
        """
        Instance created.
        """
        self._add_log(ChangeLog.ACTION_CREATE, instance)


    def edit(self, instance, previous_instance, instance_label=None):
        """
        Instance updated.
        """
        self._add_log(ChangeLog.ACTION_EDIT, instance, previous_instance, instance_label)


    def delete(self, instance):
        """
        Instance updated.
        """
        # issue updates of related objects that are currently pointing to
        # instance and would be set to NULL due to deleting instance.
        self._add_related_log(instance)

        # issue delete of given instance
        self._add_log(ChangeLog.ACTION_DELETE, instance)


    def add_message(self, message_type, message, change):
        """
        Add given flash message and provide undo link based on given change
        hashcode.
        """
        messages.add_message(self._request, message_type, message, extra_tags=change)


    def commit(self, message, instance=None, model=None, flash=True):
        """
        Commit work done so far. If we've collected multiple items that we
        will group them into one item.
        """
        if self._commited:
            return

        # create outer change record
        self._parent_log = self._create_log(message, instance, model=model)
        if not self._parent_log:
            return None

        self._commited = True

        # extract change hashcode
        change = self._parent_log.hashcode

        # message
        if flash:
            self.add_message(messages.SUCCESS, message, change)

        return change


    def materialize(self):
        """
        Write changelog entry to database.
        """
        # click save without changes and without timestamps will generate empty
        # log record
        if len(self._log) == 0:
            return

        if not self._commited or self._parent_log is None:
            return

        # if pk is not int return
        if self._parent_log.target_id is not None:
            try:
                int(self._parent_log.target_id)
                for log in self._log:
                    int(log.target_id)
            except:
                return

        if len(self._log) == 1 and self._parent_log.content_type == self._log[0].content_type and self._parent_log.target_id == self._log[0].target_id:
            # single change
            self._parent_log.action = self._log[0].action
            self._parent_log.changes = self._log[0].changes
            self._parent_log.save()
        else:
            # extract action and content type from first log item
            self._parent_log.action = self._log[-1].action
            self._parent_log.changes = None

            # save outer entry (parent)
            self._parent_log.save()

            # create inner change records
            for seq, log in enumerate(self._log, start=1):
                log.parent = self._parent_log
                log.seq = seq
                log.save()

        # clear log
        self._log = []
        self._parent_log = None


    def undo(self, hashcode):
        """
        Undo given operation identified by given hashcode.
        """
        # get main log
        try:
            parent = ChangeLog.objects.get(parent__isnull=True, hashcode=hashcode)
            parent, undo_create = self._undo_changelog(parent)
            if parent is not None:
                messages.add_message(self._request, messages.SUCCESS, 'Changes restored: <em>%s</em>' % parent.plain_title)
            return parent, undo_create
        except ChangeLog.DoesNotExist:
            return None, False


    def undo_by_ids(self, pks):
        """
        Undo given operation identified by given identifier.
        """
        # get main log entries (most recent first)
        try:
            parents = list(ChangeLog.objects.filter(parent__isnull=True, pk__in=pks).order_by('-created_on'))
            success = True
            n_success = 0
            for parent in parents:
                item, _ = self._undo_changelog(parent)

                if not item:
                    success = False
                else:
                    n_success += 1

            if success:
                messages.add_message(self._request, messages.SUCCESS, '%d of %d changes restored successfully.' % (
                    n_success,
                    len(parents)
                ))

            return success
        except ChangeLog.DoesNotExist:
            return False


    def _undo_changelog(self, parent):
        """
        Undo given changelog entry (parent).
        """
        # cannot restore a changelog entry that has already been restored
        if parent.restored:
            messages.add_message(self._request, messages.ERROR, 'Already restored: <em>%s</em>' % parent.plain_title)
            return None, False

        # get underlying action log in reverse order
        actions = list(ChangeLog.objects.filter(parent=parent).order_by('-seq'))
        if actions:
            # undo underlying actions
            for action in actions:
                self._undo_action(action)
        else:
            # undo parent action
            self._undo_action(parent)

        # mark changelog entries as restored
        for action in actions:
            action.restored = True
            action.save()

        # mark parent as restored
        parent.restored = True
        parent.save()

        # determine if this was an undo for a create
        undo_create = (
            parent is not None and
            parent.action == ChangeLog.ACTION_CREATE and
            (len(actions) == 0 or parent.content_type_id == actions[-1].content_type_id)
        )

        return parent, undo_create


    def _undo_action(self, action):
        """
        Perform undo for given changelog action.
        """
        model = action.content_type.model_class()
        instance = None

        if action.action == ChangeLog.ACTION_DELETE:
            # re-create item
            instance = model()
            deferred = {}
            for k, v in action.field_dict.items():
                field = instance._meta.get_field(k)
                if field.many_to_many:
                    deferred[k] = v
                else:
                    setattr(instance, k, v)
            instance.save()

            # update deferred (many-to-many) fields after the instance has
            # been re-created...
            if deferred:
                for k, v in deferred.items():
                    setattr(instance, k, v)
                instance.save()
        elif action.action == ChangeLog.ACTION_EDIT:
            # undo changes that occured
            instance = model.objects.get(pk=action.target_id)
            for k, v in action.previous_field_dict.items():
                setattr(instance, k, v)
            instance.save()
        elif action.action == ChangeLog.ACTION_CREATE:
            # delete item
            try:
                instance = model.objects.get(pk=action.target_id)
                instance.delete()
            except model.DoesNotExist:
                # does not exist? Fine, we wanted to delete it anyway
                pass

        # call changelog handler on model instance if available
        if instance and hasattr(instance, 'on_changelog_restored'):
            instance.on_changelog_restored(action.action)


    def _create_log(self, message, instance=None, previous_instance=None, action=None, instance_label=None, model=None):
        """
        Create a new changelog entry.
        """
        log = ChangeLog()
        log.title = self._get_title(message, instance, instance_label)[:255]
        log.created_on = datetime.datetime.now()
        log.action = action

        # user
        if hasattr(self._request, 'user') and self._request.user.pk is not None:
            log.user = self._request.user

        # determine changes or list of values
        changes = self.get_changes(instance, previous_instance)
        log.changes = to_json(changes)

        # ignore if there are no changes
        if previous_instance is not None and not changes:
            return None

        # create unique hash identifier
        log.hashcode = self._generate_hashcode()

        # connect instance if present
        if instance is not None:
            log.content_type = self._get_content_type(instance.__class__)
            log.target_id = instance.pk

            # pk must exist and must be numeric
            if log.target_id is None:
                raise ValueError(
                    ('Creating changelog entry for instance of type \'%s\' failed: ' +
                    'Instance pk cannot be None. Did you not call save() before request.changelog.create() ?') %
                        instance.__class__.__name__
                )

            try:
                int(log.target_id)
            except:
                # Creating changelog entry for instance failed:
                # Instance pk must be numeric. silently fail
                return None

        elif model is not None:
            log.content_type = self._get_content_type(model)

        # call changelog handler on instance
        if log and instance and hasattr(instance, 'on_changelog'):
            instance.on_changelog(action)

        return log


    def _add_related_log(self, instance):
        """
        Recursively issue change log entries for related items that are pointing
        to instance but would be set to NULL due to deleting instance.
        """
        # find all models that are holding a reference to the given instance
        # model, which might be one of the following
        # - ForeignKey to instance model
        # - OneToOneField to instance model
        # - ManyToManyField without a through model referencing instance model
        # - GenericRelation.
        # ManyToManyField with a though model are irrelevant, since they will
        # be found because of a ForeignKey that exists to the instance model
        # in the intermediate model class.
        for model in get_models():
            # skip self or ChangeLog
            if model == instance.__class__ or model == ChangeLog:
                continue

            # scan for related fields that are referencing the instance model
            for field in model._meta.get_fields():
                # only RelatedField
                if not isinstance(field, RelatedField):
                    continue

                # ignore ManyToMany or GenericRelation
                if field.many_to_many or isinstance(field, GenericRelation):
                    continue

                # ignore the ones that are not pointing to instance model
                if not issubclass(instance.__class__, field.rel.model):
                    continue

                # get affected target objects
                objects = model.objects.filter(**{
                    field.name: instance.pk
                })

                # generate log entry
                for obj in objects:
                    if field.null:
                        # nullable field -> log edit
                        previous_obj = self.get_changes(obj)
                        setattr(obj, field.attname, None)
                        self.edit(obj, previous_obj)
                    else:
                        # not nullable -> log delete
                        self.delete(obj)


    def _generate_hashcode(self):
        r = random.SystemRandom()
        return hashlib.sha224(''.join([r.choice(string.printable) for i in range(0, 1024)])).hexdigest()


    def _add_log(self, action, instance, previous_instance=None, instance_label=None):
        """
        Add a new changelog entry to the log for this session.
        """
        log = self._create_log(action.title(), instance, previous_instance, action, instance_label)
        if log:
            self._log.append(log)


    def _get_content_type(self, _class):
        """
        Return the content type of the given class.
        """
        name = _class.__name__
        if name not in self._classes:
            self._classes[name] = ContentType.objects.get_for_model(_class)

        return self._classes.get(name)


    def _get_title(self, message, instance, instance_label):
        """
        Return a useful automatic title based on the given verb and model
        instance.
        """
        if instance is not None:
            return '%s %s %s' % (
                message,
                instance._meta.verbose_name,
                instance_label if instance_label else instance
            )
        else:
            return message
