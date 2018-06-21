# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from cubane.ishop import get_customer_model


def shop_login_required():
    """
    Require authenticated user session, otherwise redirect to login page.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # authenticated users are free to continue
            if request.user.is_authenticated():
                if get_customer_model().objects.filter(user=request.user).count() == 1:
                    return view_func(request, *args, **kwargs)

            # otherwise we redirect to checkout login page
            return HttpResponseRedirect(reverse('shop.account.login'))

        return _wrapped_view
    return decorator


def shop_checkout_login_required():
    """
    Decorator for views that are part of the checkout. It makes sure that the
    user is logged in (as the default login_required decorator would do). In
    addition, this decorator also allows an AnonymousUser to be present as long
    as the user provided an email address.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # authenticated users are free to continue
            if request.user.is_authenticated():
                if get_customer_model().objects.filter(user_id=request.user.id).count() == 1:
                    return view_func(request, *args, **kwargs)

            # Do we provide guest checkout?
            if request.settings.guest_checkout:
                # AnonymousUser need to provide an email
                if request.user.is_anonymous():
                    if request.session.get(settings.GUEST_USER_SESSION_VAR, None) != None:
                        return view_func(request, *args, **kwargs)

                # otherwise we redirect to checkout login page
                return HttpResponseRedirect(reverse('shop.order.login'))
            else:
                # No guest checkout -> Go to account registration/login
                return HttpResponseRedirect(reverse('shop.account.login') + '?checkout=1')
        return _wrapped_view
    return decorator