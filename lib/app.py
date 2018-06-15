# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.apps import apps
import sys
import hashlib


MODEL_TO_HASH = None
HASH_TO_MODEL = None


def model_to_hash(model):
    """
    Return the hash that represents the given model class.
    """
    global MODEL_TO_HASH

    _build_model_cache()
    return MODEL_TO_HASH.get(model)


def hash_to_model(h):
    """
    Return the model class based on the given hash value.
    """
    global HASH_TO_MODEL

    _build_model_cache()
    return HASH_TO_MODEL.get(h)


def _build_model_cache():
    """
    Build model cache for all models that are installed.
    """
    global MODEL_TO_HASH
    global HASH_TO_MODEL

    if MODEL_TO_HASH is None:
        MODEL_TO_HASH = {}
        HASH_TO_MODEL = {}

        _hashes = []
        for m in get_models():
            _hash = hashlib.sha256('.'.join([m.__module__, m.__name__])).hexdigest()

            # construct minimum viable hash value without collision
            h = ''
            i = 1
            while not h or h in _hashes:
                h += _hash[:i]
                i += 1

            MODEL_TO_HASH[m] = h
            HASH_TO_MODEL[h] = m
            _hashes.append(h)


def get_models():
    """
    Return a list of all installed django models.
    """
    return apps.get_models()


def get_app_label_ref(import_path):
    """
    Return the app label reference based on the given import path.
    """
    parts = import_path.split('.')
    parts = filter(lambda p: p not in ['models', 'cubane'], parts)
    parts = parts[:2]
    return '.'.join(parts)


def require_app(app_name, required_app_name):
    """
    DEBUG only: Require the given django app(s) to be installed.
    Otherwise rise exception.
    """
    if len(sys.argv) >= 2 and sys.argv[0] == 'manage.py' and sys.argv[1] != 'runserver' and not settings.TEST:
        return

    if settings.DEBUG:
        if isinstance(required_app_name, list):
            one_app_installed = False
            for app in required_app_name:
                if app in sys.modules and app in settings.INSTALLED_APPS:
                    one_app_installed = True
                    break
            if not one_app_installed:
                raise ImportError(
                    ('Django app %(app)s requires either of these apps to be installed: %(required_app)s. ' +
                    'Make sure that at least one is included in INSTALLED_APPS ' +
                    'before %(app)s.') % {
                        'app': app_name,
                        'required_app': " or ".join(required_app_name)
                    }
                )
        else:
            if required_app_name not in sys.modules or \
               required_app_name not in settings.INSTALLED_APPS:
                raise ImportError(
                    ('Django app %(app)s requires the app %(required_app)s. ' +
                    'Make sure that %(required_app)s is included in INSTALLED_APPS ' +
                    'before %(app)s.') % {
                        'app': app_name,
                        'required_app': required_app_name
                    }
                )
