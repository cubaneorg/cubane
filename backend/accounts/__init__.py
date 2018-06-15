from cubane.lib.app import require_app
require_app(__name__, 'cubane.backend')


def install_backend(backend):
    from cubane.backend.accounts.views import AccountBackendSection
    backend.register_section(AccountBackendSection())
