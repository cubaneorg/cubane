# coding=UTF-8
from __future__ import unicode_literals
import os
import subprocess
import re
import json


CMD_CUBANE = """
from django.conf import settings
import cubane
from cubane.cms.views import get_cms_settings
from cubane.lib.libjson import to_json
cms_installed = 'cubane.cms' in settings.INSTALLED_APPS
site_settings = get_cms_settings() if cms_installed else object()
email = getattr(site_settings, 'email', None)
print(to_json({
    'version': cubane.VERSION,
    'domain': settings.DOMAIN_NAME,
    'email': email,
    'captcha': settings.CAPTCHA
}))
"""


CMD_IKIT = """
from django.conf import settings
import ikit
from ikit.cms.views import get_cms_settings
from ikit.lib.libjson import to_json
cms_installed = 'ikit.cms' in settings.INSTALLED_APPS
site_settings = get_cms_settings() if cms_installed else object()
email = getattr(site_settings, 'email', None)
print(to_json({
    'version': ikit.VERSION,
    'domain': settings.DOMAIN_NAME,
    'email': email,
    'captcha': settings.CAPTCHA
}))
"""


def find_file(folder, filename, max_level=4):
    """
    Yield all direct parent folders containing a file matching the given
    filename within any sub-folder (or directly) of the given folder.
    """
    if max_level > 0:
        matches = []
        for item in os.listdir(folder):
            if not item.startswith('.') and not item.startswith('_'):
                abs_item = os.path.join(folder, item)
                if item == filename and os.path.isfile(abs_item):
                    yield folder
                elif os.path.isdir(abs_item):
                    for parent_dir in find_file(abs_item, filename, max_level - 1):
                        yield parent_dir


def get_app_info(folder, cmd, user=None):
    """
    Return True, if the given folder is indeed a cubane app.
    """
    # run as user?
    if not user:
        # get user
        m = re.match(r'^\/home\/(.*?)\/', folder)
        if m:
            return get_app_info(folder, cmd, m.group(1))

    # execute command
    current_path = os.getcwd()
    try:
        os.chdir(folder)

        shell_cmd = 'python manage.py shell'
        if user:
            shell_cmd ='sudo su - %s -c "cd %s && %s"' % (user, folder, shell_cmd)

        p = subprocess.Popen(
            shell_cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, err_output) = p.communicate(cmd)
        p.wait()

        if p.returncode == 0:
            output = output.decode('utf8')
            output = output.replace('>>>', '')
            output = output.replace('...', '')
            output = output.strip()
            try:
                return json.loads(output)
            except:
                return False

    finally:
        os.chdir(current_path)

    return False


def scan_app(folder):
    """
    Scan given app, which is most-likely a cubane-based app.
    """
    info = get_app_info(folder, CMD_CUBANE)
    if not info:
        info = get_app_info(folder, CMD_IKIT)

    if info:
        yield info


def scan_folder(folder):
    """
    Scan given folder for manage.py to identify a possible cubane installation.
    """
    for app_folder in find_file(folder, 'manage.py'):
        for info in scan_app(app_folder):
            yield info


def scan_sites(folder):
    """
    Scan for cubane-based sites within the given folder.
    """
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        print '\'%s\' is not a directory or does not exist.' % folder
        return

    print 'Scanning: %s' % folder
    print ''.join(['%-50s' % col for col in ['Domain', 'Version', 'Email', 'Captcha']])
    print '-' * 4 * 50
    for info in scan_folder(folder):
        row = [
            info.get('domain'),
            info.get('version'),
            info.get('email'),
            info.get('captcha')
        ]
        print ''.join(['%-50s' % col for col in row])