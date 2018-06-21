import django.dispatch

before_cms_save = django.dispatch.Signal(providing_args=["request", "cleaned_form_data", "model_instance", "was_edited"])
after_cms_save = django.dispatch.Signal(providing_args=["request", "cleaned_form_data", "model_instance", "was_edited"])