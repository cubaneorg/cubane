# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.cms.views import CMS
from cubane.enquiry.views import default_enquiry_form, get_enquiry_model
from $TARGET_NAME$.forms import FrontendEnquiryForm


class $TARGET_NAME_CAMEL_CASE$CMS(CMS):
    def on_template_context(self, request, context, template_context):
        """
        Override: Template context
        """
        # TODO: Add additional template context for all pages
        # or specific pages. You can only override other handlers,
        # for example on_homepage() or on_contact_page() in order
        # to run specific code for specific pages.
        template_context.update({
        })

        return template_context


    def on_contact_page(self, request, context, template_context):
        """
        Override: Return custom enquiry form.
        """
        return default_enquiry_form(
            request,
            context,
            template_context,
            get_enquiry_model(),
            formclass=FrontendEnquiryForm
        )