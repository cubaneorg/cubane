# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.file import ensure_dir, file_get_contents
from cubane.lib.serve import serve_static_with_context
import os
import re
import subprocess
import codecs


YUI_VERSION = '2.4.8'
PATTERN_JS_CONSOLE = re.compile(r'^\s*console\.\w+\(.*?\);\s*$', re.MULTILINE | re.I | re.DOTALL)


def fix_calc_compressor_bug(css):
    calcRx = re.compile('calc\((.*?)(;|})', re.MULTILINE)
    plusRx = re.compile('(?<![*/]\s)[+]', re.MULTILINE)
    minusRx = re.compile('(?<![*/]\s)[-]', re.MULTILINE)

    def fixCss(match):
        expr = plusRx.sub(' + ', match.group(1))
        expr = minusRx.sub(' - ', expr)

        # remove double spaces
        expr = re.sub('\s{2,}', ' ', expr)
        return 'calc(' + expr + '%s' % match.group(2)

    return calcRx.sub(fixCss, css)


def minify(content, filetype='js'):
    """
    Return the compressed version of the given input content based on given
    content type (js/css).
    """
    # remove any calls to console.*();, e.g. console.log(...);
    if filetype == 'js':
        content = re.sub(PATTERN_JS_CONSOLE, '; \n', content)

    # trim content
    content = content.strip()

    # only invoke the compressor if we actually have content to compress...
    if content == '':
        return content

    # call external compressor
    command = settings.MINIFY_CMD_JS if filetype == 'js' else settings.MINIFY_CMD_CSS
    p = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # push content into pipe as utf8
    (output, err_output) = p.communicate(content.encode('utf8'))
    p.wait()

    # raise exception on compression error
    if p.returncode != 0:
        raise ValueError('Error compressing %s content: %s' % (filetype, err_output))

    # decode as utf-8
    output = output.decode('utf8')

    # trim result
    output = output.strip().strip('\n')

    # correst common compressor BUG regarding calc() css func.
    if filetype == 'css':
        output = fix_calc_compressor_bug(output)

    # return minified content
    return output


def relocate_css_import_rules(content):
    """
    Move all @import css rules to the top of the css file but preserve
    the order in which they occure.
    """
    # collect @import rules
    rules = []
    def collect_rule(m):
        url = m.group('url')
        if url is None: url = m.group('url2')
        url = url.strip('\'')
        url = url.strip('"')
        url = url.strip()
        rules.append('@import url(\'%s\');' % url)
        return ''
    content = re.sub(r'@import\s+url\s*\((?P<url>.*?)\)\s*;?|@import\s+[\'"](?P<url2>.*?)[\'"]\s*;?', collect_rule, content)

    # append rules to the beginning of the file
    return '\n'.join(rules) + '\n' + content


def relocate_css_relative_resource_urls(content, base, filename, dst_filename):
    """
    Replace all relative urls in css files with the right positions
    """
    current_folder = os.path.dirname(filename)

    def repl_url(m):
        url = m.group('url')
        import_rule = False
        if url is None:
            url = m.group('import_url')
            import_rule = True

        # strip url and calc. absolute url path
        url = url.strip('\'')
        url = url.strip('"')
        url = url.strip()
        if not url.startswith('data:'):
            url = os.path.abspath(os.path.join(current_folder, url)).replace(base, '')
            if not url.startswith('/media/') and not url.startswith('/static/'):
                url = '/static' + url

        # re-inject correct url rule
        if import_rule:
            return '@import url(\'%s\')' % url
        else:
            return 'url(\'%s\')' % url

    return re.sub(r'url\((?P<url>.*?)\)|@import\s+[\'"](?P<import_url>.*?)[\'"]', repl_url, content)


def rewrite_css_content(content):
    """
    Rewrite css content, before compressing it. For example, @import rules
    need to be relocated to the start of the file.
    """
    content = relocate_css_import_rules(content)

    return content


def compile_if_require_js_hook(filename):
    """
    Checks whether filename matches the first entry of settings.REQUIRE_JS
    and replaces the file(-name) with a require js compiled JS version.
    """
    if True in [entry["filename"] in filename for entry in settings.REQUIRE_JS]:
        # get temp filename *.jsc
        new_filename = filename + '.jsc'

        # try compiling it
        rhinojsjar = os.path.join(settings.CUBANE_PATH, 'bin', 'requirejs', 'rhino-js.jar')
        closurejar = os.path.join(settings.CUBANE_PATH, 'bin', 'requirejs', 'closure-compiler.jar')
        rjs = os.path.join(settings.CUBANE_PATH, 'bin', 'requirejs', 'r.js')

        # get baseurl if not provided from the filename (folder file resides in)
        if 'baseurl' in entry:
            baseURL = os.path.join(settings.STATIC_ROOT, entry['baseurl'].lstrip('/'))
        else:
            baseURL,_ = os.path.split(filename)

        # get module name if not provided (same as filename without extension)
        if 'module' in entry:
            modulename = entry['module']
        else:
            _, modulename = os.path.split(filename)
            modulename, _ = os.path.splitext(modulename)

        # execute command
        cmd = ' '.join([
            'java',
            '-classpath',
            '%s:%s' % (rhinojsjar, closurejar),
            'org.mozilla.javascript.tools.shell.Main',
            rjs,
            '-o',
            'baseUrl=%s' % baseURL, # root directory, modules are relative to baseURL
            'name=%s' % modulename, # module name e.g. main (from main.js)
            'out=%s' % new_filename])

        p = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        p.wait() # wait for the process to finish compiling

        # if compilation succeeded return the compiled new file
        if os.path.exists(new_filename):
            return new_filename

    # if javascript file needs no compilation or compilation failed
    return filename



def merge_files(filenames, base, filetype, dst_filename, identifier=None):
    """
    Merge multiple files together and return their content.
    """
    content = []
    for fname in filenames:
        filename = fname
        if filetype == 'js':
            filename = compile_if_require_js_hook(filename)

        # silently ignore missing files
        try:
            txt = file_get_contents(filename)
        except IOError:
            txt = ''

        # Replace any django template variables by running it through a template
        # and return the template content
        if 'templating' in filename:
            txt = serve_static_with_context(txt, identifier)

        if len(txt) > 0:
            if filetype == 'css':
                txt = relocate_css_relative_resource_urls(txt, base, filename, dst_filename)
            content.append(txt)
            content.append('\n')
    return '\n'.join(content)


def minify_files(filenames, base, dst_filename, filetype='js', identifier=None):
    """
    Merge given file names, compress the result and write it to the given
    dest. filename.
    """
    # merge
    content = merge_files(filenames, base, filetype, dst_filename, identifier)

    # rewrite content
    if filetype == 'css':
        content = rewrite_css_content(content)

    # write out source file before compressing it (debug only)
    if settings.GENERATE_MINIFY_SRC:
        f = codecs.open(dst_filename + '.src', 'w', 'utf8')
        f.write(content)
        f.close()

    # compress
    if content != '':
        content = minify(content, filetype)

    # ensure directory exists...
    ensure_dir(dst_filename)

    # write compressed file
    f = codecs.open(dst_filename, 'w', 'utf8')
    f.write(content)
    f.close()
