# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.lib.mail import cubane_send_cms_enquiry_mail
from cubane.cms.views import get_cms


class Command(BaseCommand):
    """
    Generate CMS test email.
    """
    args = ''
    help = 'Generate CMS test email'


    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--email',
            metavar=('Target email address'),
            required=True,
            help='The email address to whom the test email will be send.'
        )


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Sending CMS Test Email...Please Wait...'

        # we require to have the enquiry page setup in settings...
        cms = get_cms()
        if not cms.settings.enquiry_template:
            print 'No Enquiry Page setup. Please choose a CMS page that is used for sending enquiry emails.'
            return

        # send email
        cubane_send_cms_enquiry_mail(
            None,
            options.get('email'),
            '%s | Test enquiry email.' % cms.settings.name
        )