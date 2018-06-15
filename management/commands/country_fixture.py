# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.lib.libjson import decode_json
from cubane.lib.file import file_get_contents, file_put_contents
import os


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Run command.
        """
        # load source data
        filename = os.path.join(settings.CUBANE_PATH, 'rawdata', 'countries.json')
        json = decode_json(file_get_contents(filename))

        # generate xml file content
        xml = []
        xml.append('<?xml version="1.0" encoding="utf-8"?>')
        xml.append('<django-objects version="1.0">')
        for c in json:
            # country name(s)
            name = c.get('name')

            # num code
            num_code = c.get('ccn3')

            # calling code
            calling_code = c.get('callingCode')
            if len(calling_code) >= 1:
                calling_code = calling_code[0]
            else:
                calling_code = None

            # generate xml
            xml.append('  <object pk="%s" model="cubane.country">' % c.get('cca2'))
            xml.append('    <field type="CharField" name="name">%s</field>' % name.get('common').upper())
            xml.append('    <field type="BooleanField" name="flag_state">0</field>')
            xml.append('    <field type="CharField" name="printable_name">%s</field>' % name.get('common'))
            xml.append('    <field type="CharField" name="iso3">%s</field>' % c.get('cca3'))
            xml.append('    <field type="BooleanField" name="landlocked">%s</field>' % ('1' if c.get('landlocked') else '0'))
            if num_code:
                xml.append('    <field type="PositiveSmallIntegerField" name="numcode">%s</field>' % num_code)
            xml.append('    <field type="CharField" name="calling_code">%s</field>' % calling_code)
            xml.append('  </object>')
        xml.append('</django-objects>')

        # save to xml file (fixture)
        filename = os.path.join(settings.CUBANE_PATH, 'fixtures', 'cubane', 'country.xml')
        file_put_contents(filename, '\n'.join(xml))

        # import fixture file
        call_command('loaddata', 'cubane/country.xml', interactive=False)