# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.template import loader
from django.shortcuts import resolve_url
from cubane.backend.accounts.models import ProxyUser, ProxyGroup, ProxyPermission
from cubane.backend.changelog import ChangeLogManager
from cubane.lib.template import get_template
from urlparse import urlparse
from functools import wraps, update_wrapper, WRAPPER_ASSIGNMENTS


BOTS = [
    'ABCdatos BotLink',
    'Acme.Spider',
    'Ahoy! The Homepage Finder',
    'Alkaline',
    'Anthill',
    'Walhello appie',
    'Arachnophilia',
    'Arale',
    'Araneo',
    'AraybOt',
    'ArchitextSpider',
    'Aretha',
    'ARIADNE',
    'arks',
    'AskJeeves',
    'ASpider (Associative Spider)',
    'ATN Worldwide',
    'Atomz.com Search Robot',
    'AURESYS',
    'BackRub',
    'Bay Spider',
    'Big Brother',
    'Bjaaland',
    'BlackWidow',
    'Die Blinde Kuh',
    'Bloodhound',
    'Borg-Bot',
    'BoxSeaBot',
    'bright.net caching robot',
    'BSpider',
    'CACTVS Chemistry Spider',
    'Calif',
    'Cassandra',
    'Digimarc Marcspider/CGI',
    'Checkbot',
    'ChristCrawler.com',
    'churl',
    'cIeNcIaFiCcIoN.nEt',
    'CMC/0.01',
    'Collective',
    'Combine System',
    'Conceptbot',
    'ConfuzzledBot',
    'CoolBot',
    'Web Core / Roots',
    'XYLEME Robot',
    'Internet Cruiser Robot',
    'Cusco',
    'CyberSpyder Link Test',
    'CydralSpider',
    'Desert Realm Spider',
    'DeWeb(c) Katalog/Index',
    'DienstSpider',
    'Digger',
    'Digital Integrity Robot',
    'Direct Hit Grabber',
    'DNAbot',
    'DownLoad Express',
    'DragonBot',
    'DWCP (Dridus'' Web Cataloging Project)',
    'e-collector',
    'EbiNess',
    'EIT Link Verifier Robot',
    'ELFINBOT',
    'Emacs-w3 Search Engine',
    'ananzi',
    'esculapio',
    'Esther',
    'Evliya Celebi',
    'FastCrawler',
    'Fluid Dynamics Search Engine robot',
    'Felix IDE',
    'Wild Ferret Web Hopper #1, #2, #3',
    'FetchRover',
    'fido',
    'Hämähäkki',
    'KIT-Fireball',
    'Fish search',
    'Fouineur',
    'Robot Francoroute',
    'Freecrawl',
    'FunnelWeb',
    'gammaSpider, FocusedCrawler',
    'gazz',
    'GCreep',
    'GetBot',
    'GetURL',
    'Golem',
    'Googlebot',
    'Grapnel/0.01 Experiment',
    'Griffon',
    'Gromit',
    'Northern Light Gulliver',
    'Gulper Bot',
    'HamBot',
    'Harvest',
    'havIndex',
    'HI (HTML Index) Search',
    'Hometown Spider Pro',
    'ht://Dig',
    'HTMLgobble',
    'Hyper-Decontextualizer',
    'iajaBot',
    'IBM_Planetwide',
    'Popular Iconoclast',
    'Ingrid',
    'Imagelock',
    'IncyWincy',
    'Informant',
    'InfoSeek Robot 1.0',
    'Infoseek Sidewinder',
    'InfoSpiders',
    'Inspector Web',
    'IntelliAgent',
    'I, Robot',
    'Iron33',
    'Israeli-search',
    'JavaBee',
    'JBot Java Web Robot',
    'JCrawler',
    'Jeeves',
    'JoBo Java Web Robot',
    'Jobot',
    'JoeBot',
    'The Jubii Indexing Robot',
    'JumpStation',
    'image.kapsi.net',
    'Katipo',
    'KDD-Explorer',
    'Kilroy',
    'KO_Yappo_Robot',
    'LabelGrabber',
    'larbin',
    'legs',
    'Link Validator',
    'LinkScan',
    'LinkWalker',
    'Lockon',
    'logo.gif Crawler',
    'Lycos',
    'Mac WWWWorm',
    'Magpie',
    'marvin/infoseek',
    'Mattie',
    'MediaFox',
    'MerzScope',
    'NEC-MeshExplorer',
    'MindCrawler',
    'mnoGoSearch search engine software',
    'moget',
    'MOMspider',
    'Monster',
    'Motor',
    'MSNBot',
    'Muncher',
    'Muninn',
    'Muscat Ferret',
    'Mwd.Search',
    'Internet Shinchakubin',
    'NDSpider',
    'Nederland.zoek',
    'NetCarta WebMap Engine',
    'NetMechanic',
    'NetScoop',
    'newscan-online',
    'NHSE Web Forager',
    'Nomad',
    'The NorthStar Robot',
    'nzexplorer',
    'ObjectsSearch',
    'Occam',
    'HKU WWW Octopus',
    'OntoSpider',
    'Openfind data gatherer',
    'Orb Search',
    'Pack Rat',
    'PageBoy',
    'ParaSite',
    'Patric',
    'pegasus',
    'The Peregrinator',
    'PerlCrawler 1.0',
    'Phantom',
    'PhpDig',
    'PiltdownMan',
    'Pimptrain.com''s robot',
    'Pioneer',
    'html_analyzer',
    'Portal Juice Spider',
    'PGP Key Agent',
    'PlumtreeWebAccessor',
    'Poppi',
    'PortalB Spider',
    'psbot',
    'GetterroboPlus Puu',
    'The Python Robot',
    'Raven Search',
    'RBSE Spider',
    'Resume Robot',
    'RoadHouse Crawling System',
    'RixBot',
    'Road Runner: The ImageScape Robot',
    'Robbie the Robot',
    'ComputingSite Robi/1.0',
    'RoboCrawl Spider',
    'RoboFox',
    'Robozilla',
    'Roverbot',
    'RuLeS',
    'SafetyNet Robot',
    'Scooter',
    'Sleek',
    'Search.Aus-AU.COM',
    'SearchProcess',
    'Senrigan',
    'SG-Scout',
    'ShagSeeker',
    'Shai''Hulud',
    'Sift',
    'Simmany Robot Ver1.0',
    'Site Valet',
    'Open Text Index Robot',
    'SiteTech-Rover',
    'Skymob.com',
    'SLCrawler',
    'Inktomi Slurp',
    'Smart Spider',
    'Snooper',
    'Solbot',
    'Spanner',
    'Speedy Spider',
    'spider_monkey',
    'SpiderBot',
    'Spiderline Crawler',
    'SpiderMan',
    'SpiderView(tm)',
    'Spry Wizard Robot',
    'Site Searcher',
    'Suke',
    'suntek search engine',
    'Sven',
    'Sygol',
    'TACH Black Widow',
    'Tarantula',
    'tarspider',
    'Tcl W3 Robot',
    'TechBOT',
    'Templeton',
    'TeomaTechnologies',
    'TITAN',
    'TitIn',
    'The TkWWW Robot',
    'TLSpider',
    'UCSD Crawl',
    'UdmSearch',
    'UptimeBot',
    'URL Check',
    'URL Spider Pro',
    'Valkyrie',
    'Verticrawl',
    'Victoria',
    'vision-search',
    'void-bot',
    'Voyager',
    'VWbot',
    'The NWI Robot',
    'W3M2',
    'WallPaper (alias crawlpaper)',
    'the World Wide Web Wanderer',
    'w@pSpider by wap4.com',
    'WebBandit Web Spider',
    'WebCatcher',
    'WebCopy',
    'webfetcher',
    'The Webfoot Robot',
    'Webinator',
    'weblayers',
    'WebLinker',
    'WebMirror',
    'The Web Moose',
    'WebQuest',
    'Digimarc MarcSpider',
    'WebReaper',
    'webs',
    'Websnarf',
    'WebSpider',
    'WebVac',
    'webwalk',
    'WebWalker',
    'WebWatch',
    'Wget',
    'whatUseek Winona',
    'WhoWhere Robot',
    'Wired Digital',
    'Weblog Monitor',
    'w3mir',
    'WebStolperer',
    'The Web Wombat',
    'The World Wide Web Worm',
    'WWWC Ver 0.2.5',
    'WebZinger',
    'XGET'
]


def redirect_login(request, login_url='cubane.backend.login',
                   redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Redirect the user to the login screen while ignoring the next argument.
    """
    resolved_url = resolve_url(login_url or settings.LOGIN_URL)
    return HttpResponseRedirect(resolved_url)


def user_has_permission(user, model, verb=None, default=True):
    """
    Return True, if the given user has sufficient permissions to perform
    the given action on the given model; otherwise False.
    Please note that permissions are only checked if
    settings.CUBANE_BACKEND_PERMISSIONS is True; otherwise we only enforce
    staff membership.
    """
    # staff member or superuser required
    if not user.is_staff and not user.is_superuser:
        return False

    # perhabs the model does not allow the operation to begin with...
    # the model can turn off permission for certain actions by setting
    # can_view, can_edit etc to False. If the attr. is not there, we assume
    # that the type of action is permitted (default True).
    if verb:
        op = 'can_%s' % verb
        if not getattr(model, op, True):
            return False

    # superuser can do everything. period.
    if user.is_superuser:
        return default

    # are we checking individual permissions on models?
    if settings.CUBANE_BACKEND_PERMISSIONS and verb:
        is_proxy = model._meta.proxy

        if is_proxy:
            model_name = model.__bases__[0].__name__.lower()
        else:
            model_name = model.__name__.lower()

        perm = '%s.%s_%s' % (model._meta.app_label, verb, model_name)

        if perm and not user.has_perm(perm):
            return False
    else:
        # if we are not checking individual permissions,
        # then the accounts section is only accessable to super users.
        if issubclass(model, (ProxyUser, ProxyGroup, ProxyPermission)):
            return False

    return default


def is_dialog_window_request(request):
    """
    Return True, if the given request is requesting content in the context of
    a dialog window.
    """
    is_browse_dialog = request.GET.get('browse', 'false') == 'true'
    is_create_dialog = request.GET.get('create', 'false') == 'true'
    is_edit_dialog = request.GET.get('edit', 'false') == 'true'
    is_dialog = request.GET.get('dialog', 'false') == 'true'
    is_index_dialog = request.GET.get('index-dialog', 'false') == 'true'
    is_external_dialog = request.GET.get('external-dialog', 'false') == 'true'
    is_frontend_editing = request.GET.get('frontend-editing', 'false') == 'true'
    return (
        is_dialog or
        is_browse_dialog or
        is_create_dialog or
        is_edit_dialog or
        is_index_dialog or
        is_external_dialog or
        is_frontend_editing
    )


def permission_required(verb=None, login_url='cubane.backend.login'):
    """
    Decorator for verifying that certain permissions are met for a view handler
    as part of a View or ModelView.
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if not request.view_instance.user_has_permission(request.user, verb):
                # raise permission denied if we are within a dialog window
                if is_dialog_window_request(request):
                    raise PermissionDenied()
                else:
                    return redirect_login(request, login_url)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def backend_login_required(login_url='cubane.backend.login'):
    """
    Decorator for backend views that checks that the user is logged in,
    redirecting to the log-in page if necessary. The default redirect page is
    the backend dashboard.
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated() and request.user.is_staff:
                return func(request, *args, **kwargs)
            else:
                # raise permission denied if we are within a dialog window
                if is_dialog_window_request(request):
                    raise PermissionDenied()
                else:
                    return redirect_login(request, login_url)
        return wrapper
    return decorator


def identity(f):
    """
    Identity decorator which has no effect on the function f that is wrapped.
    """
    return f


def template(template_name=None, content_type='text/html; charset=utf-8', status_code=200, post_action=None):
    """
    View decorator for rendering templates. The view handler returns a dict,
    which then is used to populate the template.
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if not isinstance(output, dict):
                return output

            # create response object
            if 'response' in output:
                response = output['response']
                del output['response']
            else:
                response = HttpResponse(request, content_type=content_type)

            # template context is the output of the actual (decorated) view
            # handler function we called earlier...
            template_context = output

            # if we are rendering content for the cache system, determine if
            # the template context actually changed compared to the one that
            # is currently cached; if so, we do not have to render anything...
            for_cache = False
            if hasattr(request, 'cache_generator') and request.cache_generator is not None:
                for_cache = True
                render_required, new_mtime = request.cache_generator.content_changed(
                    template_context,
                    request.cache_filepath
                )

                # keep render response-relevant data
                response.cache_mtime = new_mtime
                response.cache_template_context = template_context
            else:
                render_required = True

            if render_required:
                # determine template to render
                if template_name != None:
                    template = get_template(template_name)
                elif 'template' in output:
                    template = get_template(output['template'])
                    del output['template']
                else:
                    raise ValueError(
                        'No Template given. Provide template name either by ' +
                        'argument to @render() or template field in ' +
                        'template context.'
                    )

                # render and return response
                response.content = template.render(template_context, request)
            else:
                # empty render result, since the result is already cached
                response.content = ''

            # add status code to the response
            response.status_code = status_code

            # execute post-response action
            if post_action:
                post_action(request, template_context, response)

            return response
        return wrapper
    return renderer


def deny_bot():
    """
    Deny access if we identify a bot based on the user agent or we do not have
    a user agent at all
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            user_agent = request.META.get('HTTP_USER_AGENT', None)

            if not user_agent:
                return HttpResponseForbidden('Request without user agent are not allowed.')

            if 'bot' in user_agent.lower():
                return HttpResponseForbidden('Request denied. See robots.txt.')

            for botname in BOTS:
                if botname in user_agent:
                    return HttpResponseForbidden('Request denied. See robots.txt.')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator