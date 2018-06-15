# coding=UTF-8


def setup(app):
    app.add_crossref_type(
        directivename='settings',
        rolename='settings',
        indextemplate='pair: %s; settings',
    )
    app.add_crossref_type(
        directivename='templatetag',
        rolename='ttag',
        indextemplate='pair: %s; template tag'
    )
    app.add_crossref_type(
        directivename='templatefilter',
        rolename='tfilter',
        indextemplate='pair: %s; template filter'
    )
    app.add_crossref_type(
        directivename='listing',
        rolename='listing',
        indextemplate='pair: %s; listings',
    )

    return {'parallel_read_safe': False}