# coding=UTF-8
from __future__ import unicode_literals
from cubane.cms.views import get_cms


def cubane_cms_context():
    """
    Decorator for injecting cms-relevant template context data, such as
    navigation or cms-wide settings.
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # call actual view handler
            context = func(request, *args, **kwargs)

            # if the result is a dict, inject cms-related context
            if isinstance(context, dict):
                # get cache generator if this is rendering content for the
                # cache system...
                if hasattr(request, 'cache_generator'):
                    cache_generator = request.cache_generator
                else:
                    cache_generator = None

                # get template context from cms
                cms = request.cms if hasattr(request, 'cms') else get_cms()
                page = context.get('page')
                page_context = context.get('pageinfo', {})
                page_context_class = context.get('page_context_class')
                cms_context = cms.get_template_context(
                    request,
                    page=page,
                    page_context=page_context,
                    page_context_class=page_context_class,
                    cache_generator=cache_generator,
                    additional_context=context
                )
                return cms_context
            else:
                return context
        return wrapper
    return decorator