#
# Standard Tests
#
from cubane.lib.tests.args import *
from cubane.lib.tests.app import *
from cubane.lib.tests.auth import *
from cubane.lib.tests.bad_words import *
from cubane.lib.tests.barcodes import *
from cubane.lib.tests.choices import *
from cubane.lib.tests.conversion import *
from cubane.lib.tests.crypt import *
from cubane.lib.tests.date import *
from cubane.lib.tests.default import *
from cubane.lib.tests.deploy import *
from cubane.lib.tests.excerpt import *
from cubane.lib.tests.file import *
from cubane.lib.tests.geocode import *
from cubane.lib.tests.html import *
from cubane.lib.tests.ident import *
from cubane.lib.tests.image import *
from cubane.lib.tests.ip import *
from cubane.lib.tests.libjson import *
from cubane.lib.tests.list import *
from cubane.lib.tests.model import *
from cubane.lib.tests.module import *
from cubane.lib.tests.num import *
from cubane.lib.tests.text import *
from cubane.lib.tests.url import *
from cubane.lib.tests.parse import *
from cubane.lib.tests.password import *
from cubane.lib.tests.range import *
from cubane.lib.tests.resources import *
from cubane.lib.tests.request import *
from cubane.lib.tests.serve import *
from cubane.lib.tests.spfcheck import *
from cubane.lib.tests.style import *
from cubane.lib.tests.templatetags import *
from cubane.lib.tests.tags import *
from cubane.lib.tests.tree import *
from cubane.lib.tests.paginator import *
from cubane.lib.tests.ucsv import *
from cubane.lib.tests.verbose import *

# requires postgresql
from cubane.lib.tests.fts import *
from cubane.lib.tests.latlng import *

# generally slow tests (for example network-bound)
from cubane.lib.tests.http import *
from cubane.lib.tests.minify import *

# this is very slow even though we use in-memory email dispatch
from cubane.lib.tests.mail import *