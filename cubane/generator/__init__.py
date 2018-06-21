# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.ident import to_camel_case
from cubane.lib.file import is_text_file, file_get_contents, file_put_contents
import os
import re
import random
import shutil


def generate_from_template(template_name, target_name, domain_name, admin_email):
    """
    Generate a new directory folder based on the given template
    """
    # make sure that inout is normalised
    target_name = target_name.lower().strip()
    domain_name = domain_name.lower().strip()
    admin_email = admin_email.lower().strip()

    # get source path
    source_path = _get_source_path(template_name)

    # abort if the source path does not exist
    if not os.path.exists(source_path):
        os.sys.stderr.write('Abort: Template with the name \'%s\' does not exists: %s.\n' % (template_name, source_path))
        return False

    # get absolute path to target
    target_path = _get_target_path(target_name)

    # create target folder if it does not exist yet
    if not os.path.exists(target_path):
        os.mkdir(target_path)

    # abort if the target folder is not empty (ignoring hidden files, like .git)
    if not _folder_is_empty(target_path):
        os.sys.stderr.write('Abort: Target path is not empty: %s.\n' % target_path)
        return False

    # construct substitution context
    context = _get_context(target_name, domain_name, admin_email)

    # copy files
    _copy_tree(source_path, target_path, context)

    return True


def _folder_is_empty(folder):
    """
    Return True, if the given folder is empty (apart from hidden files, like .git).
    """
    return len(filter(lambda x: not x.startswith('.'), os.listdir(folder))) == 0


def _get_source_path(template_name):
    """
    Return the absolute path of the source folder for the template with the
    given name.
    """
    template_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(template_path, 'templates', template_name))


def _get_target_path(target_name):
    """
    Return the absolute path of the target folder with the given target name
    and the current working directory.
    """
    return os.path.abspath(os.path.join(os.getcwd(), target_name))


def _generate_django_secret_key():
    """
    Generates a new random secret key to be used for DJANGO.
    """
    return ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])


def _get_context(target_name, domain_name, admin_email):
    """
    Return a set of data entries (context) that is used for substitution of
    file and folder names as well as file content.
    """
    return {
        'TARGET_NAME': target_name,
        'TARGET_NAME_CAMEL_CASE': to_camel_case(target_name),
        'DOMAIN_NAME': domain_name,
        'ADMIN_EMAIL': admin_email,
        'SECRET_KEY': _generate_django_secret_key()
    }


def _get_substituted_content(content, context):
    """
    Substitude variables in the given content based on the given context.
    """
    def repl(m):
        name = m.group('var')[1:-1]
        if name in context:
            return context[name]
        else:
            return m.group(0)
    return re.sub(r'(?P<var>\$[-_A-Z0-9]+\$)', repl, content)


def _copy_tree(source, dest, context):
    """
    Copy all files and folders from the given source to the given dest.
    folder. Each file name and file content is processed to replace
    certain variables, such as $TARGET_NAME$.
    """
    for root, folders, files in os.walk(source):
        for name in files:
            _copy_tree_item(source, dest, root, name, context, is_file=True)

        for name in folders:
            _copy_tree_item(source, dest, root, name, context, is_file=False)


def _copy_tree_item(source, dest, root, name, context, is_file):
    """
    Copy given folder or file with the given name within the given root
    folder from the given source folder to the given dest. folder.
    """
    # determine paths
    src_path = os.path.join(root, name)
    dst_path = src_path.replace(source, dest)

    # substitude variables in paths
    dst_path = _get_substituted_content(dst_path, context)

    # copy item
    if is_file:
        _copy_file(src_path, dst_path, context)
    else:
        _create_folder(dst_path)


def _copy_file(src_path, dst_path, context):
    """
    Copy the given file to the given dest. path. The filename and it's
    content may be substituted.
    """
    if is_text_file(src_path):
        # text, substritute content against given context
        content = file_get_contents(src_path)
        content = _get_substituted_content(content, context)
        file_put_contents(dst_path, content)
    else:
        # binary, directly copy without substitution
        shutil.copyfile(src_path, dst_path)


def _create_folder(path):
    """
    Creates the given folder path. The path name may be substituted.
    """
    os.mkdir(path)
