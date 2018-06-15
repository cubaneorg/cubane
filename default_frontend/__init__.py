"""
Default_frontend adds default javascript and css content that is specifically
targeted to frontend websites.

It mainly adds basic support for print style, external links, automatic
form element focus etc.
"""
from cubane.lib.app import require_app


RESOURCES = [
    'js/default_frontend.js',
    'js/mailchimp.js',
    'css/default_frontend.css',
    'print|css/default_frontend_print.css'
]
