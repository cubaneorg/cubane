# coding=UTF-8
from __future__ import unicode_literals
from django.db.models import Max
from django.db.models.fields import NOT_PROVIDED, FieldDoesNotExist
from cubane.lib.model import save_model
from cubane.lib.app import get_models
from cubane.cms import get_page_model_name, get_page_model
from cubane.cms.models import ChildPage, Entity


class CMSScriptingMixin(object):
    def get_supported_models(self):
        return [
            get_page_model(),
            ChildPage,
            Entity
        ]


    def delete_content(self):
        """
        Delete all cms content including images.
        """
        self.delete_child_pages()
        self.delete_entities()
        self.delete_pages()


    def delete_child_pages(self):
        """
        Delete all child pages.
        """
        for model in get_models():
            if issubclass(model, ChildPage):
                for page in model.objects.all():
                    page.delete()


    def delete_entities(self):
        """
        Delete all cms entities.
        """
        for model in get_models():
            if issubclass(model, Entity):
                for page in model.objects.all():
                    page.delete()


    def delete_pages(self):
        """
        Delete all cms pages.
        """
        for page in self.get_page_model().objects.all():
            page.delete()


    def create_object(self, model_name, properties):
        """
        Create and return a new cms object.
        """
        # create fake request
        request = self.fake_request()

        # create a new instance
        model = self.get_object_model(model_name)
        if not model:
            raise ValueError('Unknown model name: \'%s\'.' % model_name)

        # get form class
        try:
            formclass = model.get_form()
        except:
            raise ValueError('Unable to call \'get_form\' class method on model \'%s\'', model)

        # construct form data and defaults
        data = {}
        for field in model._meta.fields:
            if field.default != NOT_PROVIDED:
                data[field.name] = field.default
        data.update(properties)

        # create form
        try:
            form = formclass(data)
        except:
            raise ValueError('Unable to create a new instance of the model form \'%s\'.' % formclass)

        # create model instance
        instance = model()

        # configure form
        if not hasattr(form, 'configure'):
            raise NotImplementedError(
                ('The form \'%s\' must implement ' +
                 'configure(request, instance=None, edit=True) in order to comply with ' +
                 'the model view %s.') % (
                    formclass.__name__,
                    self.__class__.__name__
                )
            )
        form.configure(request, edit=False, instance=instance)

        # validate form
        if not form.is_valid():
            err_messages = []
            for err, messages in form.errors.items():
                err_messages.append('%s: %s' % (err, ', '.join(messages)))
            raise ValueError('The form did not validate:\n%s' % '\n'.join(err_messages))

        # save model instance
        save_model(data, instance)

        # update seq
        try:
            field = self.get_seq_model_field(model)
            r = model.objects.all().aggregate(Max('seq'))
            seq = r.get('seq__max')
            if seq == None: seq = 0
            instance.seq = seq + 1
            instance.save()
        except FieldDoesNotExist:
            pass

        # return new instance
        return instance


    def create_page(self, properties):
        return self.create_object(get_page_model_name(), properties)


    def get_seq_model_field(self, model):
        return model._meta.get_field('seq')


    def get_object_model(self, model_name):
        """
        Create a object model with given name.
        """
        # only consider the axtual name
        if '.' in model_name:
            model_name = model_name.split('.')[-1]

        supported_models = self.get_supported_models()
        for model in get_models():
            valid = False
            for supported_model in supported_models:
                if issubclass(model, supported_model):
                    if model_name == model.__name__:
                        return model
        return None