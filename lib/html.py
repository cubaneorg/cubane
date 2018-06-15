# coding=UTF-8
from __future__ import unicode_literals
from django.forms.utils import flatatt
from cubane.lib.text import text_from_html
from cubane.lib.url import is_external_url
from bs4 import BeautifulSoup
import re


def transpose_html_headlines(html, level):
    """
    Transpose existing headlines within the given html by the given
    amount of levels, for example a transpose of headlines by a level of 1
    would change every h1 headline into a h2 headline, every h2 headline into
    a h3 headline and so forth. The max. number of headlines supported by html
    is h6, therefore transposing an h6 would result into an h6.
    """
    if level <= 0:
        return html

    def repl(m):
        index = int(m.group('tag')[1])
        index += level
        index = max(0, min(6, index))
        return '%sh%d' % (m.group('bracket'), index)

    pattern = re.compile(r'(?P<bracket></?)(?P<tag>h1|h2|h3|h4|h5|h6)', flags=re.IGNORECASE)
    return re.sub(pattern, repl, html)


def cleanup_html(html):
    """
    Cleanup given html content, for example removing double-empty paragraphs or
    leading or trailing empty paragraphs, which happens a lot when editing
    content.
    """
    if html is None:
        return ''

    # strip white space
    html = html.strip()

    # remove empty paragraphs throughout, ignoring attributes
    html = re.sub(r'<p[^>]*>\s*&nbsp;\s*</p>', '', html)
    html = re.sub(r'<p[^>]*>\s*</p>', '', html)

    # we often find a paragraph starting with whitespace
    html = re.sub(r'<p([^>]*)>(\s|&nbsp;)*', r'<p\1>', html)

    # remove unneccessary <br> tags at the beginning of a paragraph
    html = re.sub(r'<p>(\s*<br([^>]*)>\s*)+', r'<p>', html)

    # remove unneccessary <br> tags at the end of a paragraph
    html = re.sub(r'(\s*<br([^>]*)>\s*)+</p>', r'</p>', html)

    return html


def embed_html(html, embed_code, initial_words=100, subsequent_words=400):
    """
    Return the given HTML code, where the given embed code has been embedded
    after paragraphs, lists, tables or images after a certain 'budget' of
    content has been 'consumed'.
    """
    if html is None:
        html = ''

    # find all paragraphs
    budget_used = 0
    budget = initial_words
    matches = re.finditer(r'<p.*?>(.*?)</p>', html)
    pos = []
    for m in matches:
        # we are doing word analysis on (potential) html text; however
        # it is most likely that we will only have simple inline markup
        # within paragraphs.
        words = re.split(r'\s', text_from_html(m.group(1)))
        words = [x.strip() for x in words]
        words = filter(lambda x: x, words)
        budget_used += len(words)

        if budget_used >= budget:
            budget_used = 0
            budget = subsequent_words
            pos.append(m.end())

    # inset embed code
    if pos:
        # process positions
        offset = 0
        for p in pos:
            index = offset + p
            html = html[:index] + embed_code + html[index:]
            offset += len(embed_code)
    else:
        # not found at all? inject at the end of it. Perhabs we do not have
        # sufficient amount of words/content to start with...
        html += embed_code

    return html


def get_normalised_links(html, href_lambda=None, domain=None):
    """
    Normalises the given link attributes and reconstructs a new link based
    on the given markup. If the target url is external, the link will open
    in a new window; otherwise not.

    Further, any references to beta. sub-domains are replaced with www
    counterparts if the URL is an internal link (with www).

    Finally, internal links are attempted to be re-written by using the
    CMS-based short-ref format instead of relying on hard-coded paths.
    """
    if html is None:
        return ''

    def repl(m):
        # split attributes
        d = BeautifulSoup(m.group(0), 'html5lib')
        a = d.find('a')
        attrs = dict(a.attrs)

        # href present?
        href = attrs.get('href')
        if href:
            # beta sub-domain?
            if href.startswith('http://beta.') or href.startswith('https://beta.'):
                real_href = href.replace('http://beta.', 'http://www.')
                real_href = real_href.replace('https://beta.', 'https://www.')
                if not is_external_url(real_href, domain):
                    attrs['href'] = href = real_href

            # determine internal/external
            if is_external_url(href, domain):
                # should open in new window
                attrs['target'] = '_blank'
                attrs['rel'] = 'noopener noreferrer'
            else:
                # should NOT open in new window
                if 'target' in attrs: del attrs['target']
                if 'rel' in attrs: del attrs['rel']

            # further process or change href
            if href_lambda is not None:
                attrs['href'] = href = href_lambda(href)

        # re-build link tag
        for name, value in attrs.items():
            if isinstance(value, list):
                attrs[name] = ' '.join(value)
        return '<a%s>%s</a>' % (flatatt(attrs), m.group(2))

    return re.sub(r'<a(.*?)>(.*?)</a>', repl, html)