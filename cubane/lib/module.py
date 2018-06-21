# coding=UTF-8
from __future__ import unicode_literals
from django.utils.module_loading import import_module
import sys
import imp
import inspect


def module_exists(module_name):
    """
    Return True, if a python module with the given name exists and could be
    loaded without actually loading it.
    """
    try:
        imp.find_module(module_name)
        return True
    except ImportError:
        return False


def get_module_by_name(module_name):
    """
    Return the module with the given name assuming that the modul was
    loaded prior to the call to this function. If no such module exists,
    an exception is thrown.
    """
    try:
        return sys.modules[module_name]
    except:
        raise ImportError(
            'Unable to refer to module %s.' % module_name
        )


def get_class_from_string(classname):
    """
    Return the class object based on the given full string containing the
    model and the name of the class.
    """
    try:
        module_name, classname = classname.rsplit('.', 1)
    except (ValueError, AttributeError):
        raise ImportError()

    m = import_module(module_name)
    return getattr(m, classname)


def register_class_extension(name, base, extension):
    """
    Register an extension for the given base class by extending it with the
    given extension mixin class. This returns a new type which adds the
    given extension to the given base class.
    all
    """
    bases = base.__bases__
    if len(bases) == 1:
        bases = (base,)
    if extension not in bases:
        bases = (extension,) + bases

    # type accepts str, not unicode
    return type(str(name), bases, {})


def register_class_extensions(name, base, extensions):
    """
    Register multiple extensions for the given base class.
    """
    for extension in extensions:
        base = register_class_extension('ExtendedCMS', base, extension)
    return base