# coding=UTF-8
from __future__ import unicode_literals
from django.template import Template, Context, TemplateSyntaxError
from django.template.defaultfilters import slugify
from django.test.utils import override_settings
from django.test import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.blog.models import BlogPost
from cubane.cms.models import Page
from cubane.cms.templatetags.cms_tags import *
from cubane.cms.views import get_cms, fake_request
from cubane.media.models import Media
from cubane.lib.paginator import create_paginator
from cubane.testapp.models import Settings
from mock import Mock, patch
import datetime


class CMSImageTagTestCase(CubaneTestCase):
    def test_should_return_image_tag_with_src(self):
        self.assertEqual(
            '<img src="test.jpg">',
            image_tag('test.jpg')
        )


    def test_should_return_image_tag_with_srcand_alt_as_keyword_argument(self):
        self.assertEqual(
            '<img src="test.jpg" alt="Test">',
            image_tag('test.jpg', alt='Test')
        )


class CMSSocialTagTestCase(CubaneTestCase):
    def test_should_return_image_tag_in_link_tag(self):
        self.assertEqual(
            '<a href="http://www.innershed.com"><img src="test.jpg"></a>',
            social_tag('http://www.innershed.com', 'test.jpg')
        )


class CMSSiteIdentificationTagTestCase(CubaneTestCase):
    def test_should_return_empty_string_without_settings(self):
        self.assertEqual(
            '',
            self._render()
        )


    def test_should_return_empty_string_if_no_site_identification_keys_are_setup(self):
        self.assertEqual(
            '',
            self._render(Mock(webmaster_key=None, globalsign_key=None))
        )


    def test_should_return_meta_for_google_webmaster_if_setup(self):
        self.assertEqual(
            '<meta name="google-site-verification" content="test" />',
            self._render(Mock(webmaster_key='test', globalsign_key=None))
        )


    def test_should_return_meta_for_globalsign_domain_verification_if_setup(self):
        self.assertEqual(
            '<meta name="globalsign-domain-verification" content="test" />',
            self._render(Mock(webmaster_key=None, globalsign_key='test'))
        )


    def _render(self, context=None):
        return site_identification(Context({
            'settings': context
        }))


class CMSCMSTemplateTagsMetaTitleTestCase(CubaneTestCase):
    """
    cubane.cms.templatetags.cms_tags.meta_title()
    """
    def test_should_return_page_meta_title_and_settings_name(self):
        self.assertEqual(
            'Foo | Bar',
            meta_title({
                'current_page': self._page(meta_title='Foo'),
                'settings': self._settings('Bar')
            })
        )


    def test_should_return_page_meta_title_and_settings_meta_name_if_provided(self):
        self.assertEqual(
            'Foo | FooBar',
            meta_title({
                'current_page': self._page(meta_title='Foo'),
                'settings': self._settings('Bar', 'FooBar')
            })
        )


    def test_should_obmit_settings_name_if_no_settings_available(self):
        self.assertEqual(
            'Foo',
            meta_title({
                'current_page': self._page(meta_title='Foo')
            })
        )


    def test_should_obmit_settings_name_if_empty(self):
        self.assertEqual(
            'Foo',
            meta_title({
                'current_page': self._page(meta_title='Foo'),
                'settings': self._settings('')
            })
        )


    def test_should_obmit_settings_name_if_none(self):
        self.assertEqual(
            'Foo',
            meta_title({
                'current_page': self._page(meta_title='Foo'),
                'settings': self._settings(None)
            })
        )


    def test_should_use_page_title_if_meta_title_is_none(self):
        self.assertEqual(
            'Foo | Bar',
            meta_title({
                'current_page': self._page(title='Foo', meta_title=None),
                'settings': self._settings('Bar')
            })
        )


    def test_should_use_page_title_if_meta_title_is_empty(self):
        self.assertEqual(
            'Foo | Bar',
            meta_title({
                'current_page': self._page(title='Foo', meta_title=''),
                'settings': self._settings('Bar')
            })
        )


    def test_should_obmit_settings_name_if_already_provided_through_page_meta_title(self):
        self.assertEqual(
            'Foo | Bar',
            meta_title({
                'current_page': self._page(meta_title='Foo | Bar'),
                'settings': self._settings('  Bar')
            })
        )


    def test_should_obmit_settings_name_if_already_provided_through_page_title(self):
        self.assertEqual(
            'Foo | Bar',
            meta_title({
                'current_page': self._page(title='Foo | Bar'),
                'settings': self._settings('  Bar')
            })
        )


    @override_settings(CMS_META_TITLE_SEPARATOR=' - ')
    def test_should_allow_overriding_separator(self):
        self.assertEqual(
            'Foo - Bar',
            meta_title({
                'current_page': self._page(meta_title='Foo'),
                'settings': self._settings('Bar')
            })
        )


    def test_should_be_settings_name_if_no_page_available(self):
        self.assertEqual(
            'Bar',
            meta_title({
                'settings': self._settings('Bar')
            })
        )


    def test_should_be_given_argument_if_string_and_not_page(self):
        self.assertEqual(
            'Test Title',
            meta_title({}, 'Test Title')
        )


    def test_should_be_empty_if_no_page_nor_settings(self):
        self.assertEqual(
            '',
            meta_title({})
        )


    def _page(self, title=None, meta_title=None):
        page = Page()
        page.title = title
        page._meta_title = meta_title
        return page


    def _settings(self, name, meta_name=None):
        settings = Settings()
        settings.name = name
        settings.meta_name = meta_name
        return settings


class CMSRenderMetaTagTestCase(CubaneTestCase):
    def test_meta_tag_should_return_html_tag(self):
        self.assertEqual(render_meta_tag('keywords', 'cubane, cms, test'), '<meta name="keywords" content="cubane, cms, test" />')


    def test_meta_tag_should_return_empty_string_for_no_value_argument(self):
        self.assertEqual(render_meta_tag('keywords', ''), '')


class CMSChildPagesTestCase(CubaneTestCase):
    def setUp(self):
        self.page = self._page('Page 1', entity_type='BlogPost')


    def tearDown(self):
        Page.objects.all().delete()
        BlogPost.objects.all().delete()


    def test_should_return_html_for_listing_child_pages(self):
        child_pages = [
            self._child_page(1, self.page),
            self._child_page(2, self.page),
            self._child_page(3, self.page)
        ]
        content = self._render_child_pages(child_pages)
        self.assertIn('class="cubane-blog-listing"', content)
        self.assertNotIn('class="pagination"', content)


    def test_should_use_pagination_if_configured_for_entity_type(self):
        child_pages = [
            self._child_page(1, self.page),
            self._child_page(2, self.page),
            self._child_page(3, self.page)
        ]
        factory = RequestFactory()
        request = factory.get('/')
        paged_child_pages = create_paginator(
            request,
            child_pages,
            page_size = 1,
            min_page_size = 1,
            max_page_size = 10
        )

        content = self._render_child_pages(paged_child_pages)
        self.assertIn('class="cubane-blog-listing"', content)
        self.assertIn('class="pagination"', content)
        self.assertIn('class="pagination-page-number">1</span>', content)
        self.assertIn('<span class="pagination-max-page-number">3</span>', content)


    def test_should_return_empty_string_for_empty_list_of_child_pages(self):
        self.assertEqual(
            '',
            self._render_child_pages(None)
        )


    def test_should_raise_error_if_template_not_found(self):
        with self.assertRaisesRegexp(ValueError, 'Error rendering child page listing item'):
            Template("{% load cms_tags %}{% child_pages 'test' %}").render(Context({}))


    def _render_child_pages(self, child_pages):
        return Template("{% load cms_tags %}{% child_pages child_pages 'blogpost' %}").render(Context({'child_pages': child_pages}))


    def _page(self, title, template='testapp/page.html', nav='header', entity_type=None, seq=0, legacy_url=None, identifier=None, parent=None):
        p = Page(
            title=title,
            slug=slugify(title),
            template=template,
            _nav=nav,
            entity_type=entity_type,
            seq=seq,
            legacy_url=legacy_url,
            identifier=identifier,
            parent=parent
        )
        p.save()
        return p


    def _child_page(self, number, page=None):
        c = BlogPost(
            title='Child Page %s' % number,
            slug=slugify('Child Page %s' % number),
            template='testapp/page.html',
            page=page,
            seq=number
        )
        c.save()
        return c


class CMSMapTestCase(CubaneTestCase):
    def test_should_return_map_html(self):
        content = Template("{% load cms_tags %} {% map lat lng zoom name %}").render(Context({'lat': '52.6757648', 'lng': '1.3737302', 'zoom': 8, 'name': 'map'}))
        self.assertEqual(' <div class="enquiry-map-canvas" data-key="foo" data-lat="52.6757648" data-lng="1.3737302" data-title="map" data-zoom="8"></div>',
            content
        )


    def test_should_return_empty_string(self):
        content = Template("{% load cms_tags %} {% map lat lng zoom name %}").render(Context({'lat': '52.6757648', 'lng': '1.3737302', 'zoom': None, 'name': 'map'}))
        self.assertEqual(u' ', content)


class CMSContactMapTestCase(CubaneTestCase):
    def test_should_return_contact_map_html(self):
        settings = Settings()
        settings.lat  = '52.6757648'
        settings.lng  = '1.3737302'
        settings.zoom = '8'
        settings.name = 'map'
        settings.save()
        content = Template("{% load cms_tags %} {% contact_map %}").render(Context({'settings': settings}))
        self.assertEqual(u' <div class="enquiry-map-canvas" data-key="foo" data-lat="52.6757648" data-lng="1.3737302" data-title="map" data-zoom="8"></div>',
            content
        )


    def test_should_return_empty_string(self):
        content = Template("{% load cms_tags %} {% contact_map %}").render(Context({}))
        self.assertEqual(u' ', content)


class CMSLinkTagTestCase(CubaneTestCase):
    def test_should_return_link_to_given_target(self):
        self.assertEqual(
            '<a href="http://www.innershed.com/">Innershed</a>',
            self._render("{% link_tag href name %}", {
                'href': 'http://www.innershed.com/',
                'name': 'Innershed'
            })
        )


    def test_should_return_link_to_given_target_with_given_keyword_arguments(self):
        self.assertEqual(
            '<a href="http://www.innershed.com/" title="Test">Innershed</a>',
            self._render("{% link_tag href='http://www.innershed.com/' content='Innershed' title='Test' %}")
        )

    def test_should_raise_error_with_missing_name(self):
        with self.assertRaises(TemplateSyntaxError):
            self._render("{% link_tag href %}", {'href': 'http://www.innershed.com'})


    def test_should_raise_error_with_missing_href_and_name(self):
        with self.assertRaises(TemplateSyntaxError):
            self._render("{% link_tag %}")


    def _render(self, template, context={}):
        return Template("{% load cms_tags %}" + template).render(Context(context))


class CMSSlotTestCase(CubaneTestCase):
    CONTENT_LAZYLOAD_IMAGE_REF          = '<span class="lazy-load"><span class="lazy-load-shape-original" style="padding-bottom:100.0%;"><noscript data-shape="original" data-path="/0/1/" data-blank="0" data-sizes="xx-small" data-alt="Test" data-title="Test" data-svg="0" data-inline="0"><img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="Test" title="Test"></noscript></span></span>'
    CONTENT_LAZYLOAD_IMAGE_REF_LIGHTBOX = '<a class="lazy-load lightbox" href="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" title="Test"><span class="lazy-load-shape-original" style="padding-bottom:100.0%;"><noscript data-shape="original" data-path="/0/1/" data-blank="0" data-sizes="xx-small" data-alt="Test" data-title="Test" data-svg="0" data-inline="0"><img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="Test" title="Test"></noscript></span></a>'


    def test_should_return_error_if_slot_does_not_exist(self):
        self.assertEqual(
            "[Slot 'none' does not exist (referenced via 'none')]",
            self._render("{% load cms_tags %}{% slot 'none' %}")
        )


    def test_should_return_empty_string_for_empty_slot(self):
        self.assertEqual(
            '',
            self._render("{% load cms_tags %}{% slot 'content' %}")
        )


    def test_should_return_slot_frame_markup_in_preview_mode(self):
        self.assertEqual(
            '<div class="cms-slot" data-slotname="content" data-headline-transpose="0"></div>',
            self._render("{% load cms_tags %}{% slot 'content' %}", {'cms_preview': True})
        )


    def test_should_return_slot_frame_markup_in_preview_mode_including_headline_transpose(self):
        self.assertEqual(
            '<div class="cms-slot" data-slotname="content" data-headline-transpose="3"></div>',
            self._render("{% load cms_tags %}{% slot 'content' 3 %}", {'cms_preview': True})
        )


    def test_should_render_slot_content_from_page(self):
        page = Page()
        page.set_slot_content('content', '<h1>Test</h1>')
        self.assertEqual(
            '<h1>Test</h1>',
            self._render("{% load cms_tags %}{% slot 'content' %}", {'page': page})
        )


    def test_should_render_child_page_rather_than_page_if_provided(self):
        page = Page()
        page.set_slot_content('content', '<h1>Page</h1>')

        child_page = BlogPost()
        child_page.set_slot_content('content', '<h1>Child Page</h1>')

        self.assertEqual(
            '<h1>Child Page</h1>',
            self._render("{% load cms_tags %}{% slot 'content' %}", {
                'page': page,
                'child_page': child_page
            })
        )


    def test_should_ignore_transpose_if_not_an_integer(self):
        page = Page()
        page.set_slot_content('content', '<h1>Page</h1>')
        self.assertEqual(
            '<h1>Page</h1>',
            self._render("{% load cms_tags %}{% slot 'content' 'not-an-integer' %}", {'page': page})
        )


    def test_should_transpose_html_headlines_according_to_transpose_argument(self):
        page = Page()
        page.set_slot_content('content', '<h1>Page</h1>')
        self.assertEqual(
            '<h3>Page</h3>',
            self._render("{% load cms_tags %}{% slot 'content' 2 %}", {'page': page})
        )


    @override_settings(CMS_RENDER_SLOT_CONTAINER=True)
    def test_should_render_slot_container_if_configured_in_settings(self):
        self.assertEqual(
            '<div class="cms-slot-container"></div>',
            self._render("{% load cms_tags %}{% slot 'content' %}")
        )


    def test_should_rewrite_lazyload_images(self):
        self.assertEqual(
            self.CONTENT_LAZYLOAD_IMAGE_REF,
            self._render_image(lightbox=False)
        )


    def test_should_rewrite_lazyload_images_as_lightbox(self):
        self.assertEqual(
            self.CONTENT_LAZYLOAD_IMAGE_REF_LIGHTBOX,
            self._render_image(lightbox=True)
        )


    @override_settings(INSTALLED_APPS=['cubane.cms', 'cubane.media'])
    def test_should_rewrite_lazyload_images_ignoring_lightbox_if_lightbox_is_not_installed(self):
        self.assertEqual(
            self.CONTENT_LAZYLOAD_IMAGE_REF,
            self._render_image(lightbox=True)
        )


    @override_settings(INSTALLED_APPS=['cubane.cms'])
    def test_should_ignore_rewriting_lazyload_images_if_media_is_not_installed(self):
        self.assertEqual(
            self._image_markup(lightbox=False),
            self._render_image(lightbox=False)
        )


    def test_should_ignore_rewriting_lazyload_images_if_media_asset_not_found(self):
        self.assertEqual(
            self._image_markup(lightbox=False),
            self._render_image(lightbox=False, media_id=2)
        )


    def test_should_ignore_rewriting_lazyload_images_if_media_asset_id_is_not_a_valid_pk_in_markup(self):
        self.assertEqual(
            self._image_markup(lightbox=False, media_id='not-a-valid-pk'),
            self._render_image(lightbox=False, markup_media_id='not-a-valid-pk')
        )


    def test_should_fallback_to_original_shape_if_specified_shape_does_not_exist(self):
        page = Page()
        page.set_slot_content('content', self._image_markup())
        html = self._render("{% load cms_tags %}{% slot 'content' 0 'shape-does-not-exist' %}", {
            'page': page,
            'images': {
                1: Media(id=1, caption='Test', width=64, height=64)
            }
        })
        self.assertMarkup(html, 'noscript', {
            'data-shape': 'original'
        })


    def test_should_raise_error_for_missing_slotname_argument(self):
        with self.assertRaisesRegexp(TemplateSyntaxError, 'takes at least one argument'):
            self._render("{% load cms_tags %}{% slot %}")


    def test_should_rewrite_page_links(self):
        self.assertEqual(
            '<a href="http://www.testapp.cubane.innershed.com/foo/">Foo</a>',
            self._render_link('#link[Page:1]', {
                'Page': {
                    '1': Page(id=1, slug='foo')
                }
            })
        )


    def test_should_return_empty_link_for_unresolved_page_link_type(self):
        self.assertEqual(
            '<a href="">Foo</a>',
            self._render_link('#link[UnknownType:1]', {
                'Page': {
                    '1': Page(id=1, slug='foo')
                }
            })
        )


    def test_should_return_empty_link_for_unresolved_page_link_id(self):
        self.assertEqual(
            '<a href="">Foo</a>',
            self._render_link('#link[Page:2]', {
                'Page': {
                    '1': Page(id=1, slug='foo')
                }
            })
        )


    @override_settings(DEBUG=True)
    def test_should_raise_exception_for_unresolved_page_link_in_debug(self):
        with self.assertRaisesRegexp(ValueError, 'Unable to resolve page link'):
            self._render_link('#link[Page:2]', {
                'Page': {
                    '1': Page(id=1, slug='foo')
                }
            })


    def _render(self, template, context={}):
        return Template(template).render(Context(context))


    def _render_image(self, lightbox=False, media_id=1, markup_media_id=1):
        page = Page()
        page.set_slot_content('content', self._image_markup(lightbox, markup_media_id))
        return self._render("{% load cms_tags %}{% slot 'content' %}", {
            'page': page,
            'images': {
                media_id: Media(id=media_id, caption='Test', width=64, height=64)
            }
        })


    def _render_link(self, link, page_links):
        page = Page()
        page.set_slot_content('content', '<a href="%s">Foo</a>' % link)
        return self._render("{% load cms_tags %}{% slot 'content' %}", {
            'page': page,
            'page_links': page_links
        })


    def _image_markup(self, lightbox=False, media_id=1):
        return '<img src="http://www.testapp.cubane.innershed.com/media/originals/0/%(id)s/test.jpg" alt="Test" width="64" data-width="64" data-height="64" data-cubane-lightbox="%(lightbox)s" data-cubane-media-id="%(id)s" data-cubane-media-size="auto" />' % {
            'id': media_id,
            'lightbox': 'true' if lightbox else 'false'
        }


class CMSGoogleAnalyticsKeyTestCase(CubaneTestCase):
    @override_settings(DEBUG=True, DEBUG_GOOGLE_ANALYTICS='12345678')
    def test_should_return_default_analytics_key_for_debugging_if_configured(self):
        self.assertEqual('12345678', get_google_analytics_key(None))


    @override_settings(DEBUG=True)
    def test_should_return_empty_for_debugging_if_no_default_analytics_key_is_configured(self):
        self.assertEqual('', get_google_analytics_key(None))


    def test_should_return_google_analytics_key_from_settings_when_in_production(self):
        context = Context({
            'settings': Mock(analytics_key='12345678')
        })
        self.assertEqual('12345678', get_google_analytics_key(context))


    def test_should_return_empty_in_production_if_no_google_analytics_key_is_setup(self):
        context = Context({
            'settings': Mock(analytics_key=None)
        })
        self.assertEqual('', get_google_analytics_key(context))


class CMSGoogleAnalyticsTestCase(CubaneTestCase):
    def test_default_analytics_javascript(self):
        self.assertEqual(
            "<script>var _gaq=_gaq||[];_gaq.push(['_setAccount','12345678']);_gaq.push(['_trackPageview']);(function(){var ga=document.createElement('script');ga.type='text/javascript';ga.async=true;ga.src=('https:'==document.location.protocol?'https://ssl':'http://www')+'.google-analytics.com/ga.js';var s=document.getElementsByTagName('script')[0];s.parentNode.insertBefore(ga, s);})();</script>",
            google_analytics(self._get_context())
        )


    def test_universal_analytics_javascript(self):
        self.assertEqual(
            "<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m) })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create','12345678','auto');ga('send','pageview');</script>",
            google_analytics_universal(self._get_context())
        )


    @override_settings(CUBANE_GOOGLE_ANALYTICS_ASYNC=True)
    def test_universal_analytics_javascript_async(self):
        self.assertEqual(
            "<script>window.ga=window.ga||function(){(ga.q=ga.q||[]).push(arguments)};ga.l=+new Date;ga('create', '12345678', 'auto');ga('send', 'pageview');</script><script async src='https://www.google-analytics.com/analytics.js'></script>",
            google_analytics_universal(self._get_context())
        )


    def test_universal_analytics_ecommerce_javascript(self):
        self.assertEqual(
            "<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create', '12345678');ga('require', 'ec');</script>",
            google_analytics_ecommerce(self._get_context())
        )


    @override_settings(CUBANE_GOOGLE_ANALYTICS_ASYNC=True)
    def test_universal_analytics_ecommerce_javascript_async(self):
        self.assertEqual(
            "<script>window.ga=window.ga||function(){(ga.q=ga.q||[]).push(arguments)};ga.l=+new Date;ga('create', '12345678', 'auto');ga('require', 'ec');</script><script async src='https://www.google-analytics.com/analytics.js'></script>",
            google_analytics_ecommerce(self._get_context())
        )


    def test_universal_analytics_javascript_with_hash_location(self):
        self.assertEqual(
            "<script>(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');ga('create','12345678','auto');ga('send','pageview',{'page':location.pathname+location.search+location.hash});window.onhashchange=function(){ga('send','pageview',{'page':location.pathname+location.search+location.hash});};</script>",
            google_analytics_universal(self._get_context(hash_location=True))
        )


    def _get_context(self, key='12345678', hash_location=False):
        return Context({'settings': Mock(analytics_key=key, analytics_hash_location=hash_location)})


class CMSTwitterWidgetTestCase(CubaneTestCase):
    def test_should_return_empty_string_if_twitter_is_not_configured(self):
        self.assertEqual('', twitter_widget(Context({})))


    def test_should_return_html_if_twitter_is_configured(self):
        self.assertEqual(
            '<a class="twitter-timeline" href="https://twitter.com/twitterapi" data-widget-id="fake-id">Tweets by @innershed</a><script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>',
            twitter_widget(Context({
                'settings': Mock(twitter_widget_id='fake-id', twitter_name='@innershed')
            }))
        )


class CMSSocialMediaLinksTestCase(CubaneTestCase):
    def test_should_return_empty_string_if_no_social_media_is_configured(self):
        self.assertEqual(
            '',
            social_media_links(Context({}))
        )


    def test_should_return_html(self):
        settings = Settings()
        settings.twitter  = 'Innershed'
        self.assertEqual(
            '<div class="automated-social-links"><a href="Innershed" target="_blank"><svg viewBox="0 0 64 64" id="icon-twitter" class="icon-social icon-social-twitter"><path d="M32,0C14.3,0,0,14.3,0,32c0,17.7,14.3,32,32,32c17.7,0,32-14.3,32-32C64,14.3,49.7,0,32,0z M45,26.2c0,0.3,0,0.5,0,0.8\n\tC45,35.4,38.7,45,27.1,45c-3.6,0-6.9-1-9.7-2.8c0.5,0.1,1,0.1,1.5,0.1c3,0,5.7-1,7.8-2.7c-2.8-0.1-5.1-1.9-5.9-4.4\n\tc0.4,0.1,0.8,0.1,1.2,0.1c0.6,0,1.1-0.1,1.7-0.2c-2.9-0.6-5.1-3.1-5.1-6.2c0,0,0-0.1,0-0.1c0.8,0.5,1.8,0.8,2.9,0.8\n\tc-1.7-1.1-2.8-3.1-2.8-5.2c0-1.2,0.3-2.2,0.9-3.2c3.1,3.8,7.8,6.3,13,6.6c-0.1-0.5-0.2-0.9-0.2-1.4c0-3.5,2.8-6.3,6.3-6.3\n\tc1.8,0,3.5,0.8,4.6,2c1.4-0.3,2.8-0.8,4-1.5c-0.5,1.5-1.5,2.7-2.8,3.5c1.3-0.2,2.5-0.5,3.6-1C47.3,24.2,46.2,25.3,45,26.2z"/></svg></a></div>',
            social_media_links(Context({
                'settings': settings
            }))
        )


class CMSOpeningTimesTestCase(CubaneTestCase):
    def test_should_return_empty_string_if_no_settings(self):
        self.assertEqual(
            '',
            opening_times(Context({}))
        )


    def test_should_return_html_for_opening_times(self):
        settings = Settings()
        settings.monday_start = datetime.time(9)
        settings.monday_close = datetime.time(17)
        settings.opening_times_enabled = True
        self.assertEqual(
            '<p><span class="opening_times_day">Monday</span><span class="opening_times_col">:</span><span class="opening_times_range">09:00 - 17:00</span></p>',
            opening_times(Context({
                'settings': settings
            }))
        )


class CMSNewsletterTestCaseBase(CubaneTestCase):
    def _settings(self):
        settings = Settings()
        settings.mailchimp_api = 'fake-api'
        settings.mailchimp_list_id = 'fake-list-id'
        return settings


    def _request(self, post, data={}):
        factory = RequestFactory()
        request = factory.post('/', data) if post else factory.get('/', data)
        return request


    def _context(self, post=False, data={}):
        return Context({'settings': self._settings(), 'request': self._request(post, data)})


class CMSNewsletterSignupFormTestCase(CMSNewsletterTestCaseBase):
    def test_should_raise_error_without_settings(self):
        with self.assertRaises(ValueError):
            newsletter_signup_form(Context({}))


    def test_should_return_empty_string_without_mailchimp_api(self):
        settings = Settings()
        self.assertEqual(
            '',
            newsletter_signup_form(Context({'settings': settings}))
        )


    def test_should_raise_error_without_request(self):
        with self.assertRaisesRegexp(ValueError, 'Expected \'request\' in template context.'):
            newsletter_signup_form(Context({'settings': self._settings()}))


    def test_should_return_html_for_form(self):
        html = newsletter_signup_form(self._context(post=False))
        self.assertMarkup(html, 'div', {'class': 'mailchimp-subscription-form'})
        self.assertMarkup(html, 'form', {'method': 'post'})
        self.assertMarkup(html, 'form', {'method': 'post'})
        self.assertMarkup(html, 'input', {'name': 'mailchimp_subscription__name', 'required': True})
        self.assertMarkup(html, 'input', {'name': 'mailchimp_subscription__email', 'required': True})


    def test_should_present_errors_on_post(self):
        html = newsletter_signup_form(self._context(post=True))
        self.assertMarkup(html, 'div', {'class': 'control-group control-group-mailchimp_subscription__email required error'})
        self.assertMarkup(html, 'div', {'class': 'help-inline'}, 'This field is required.')


    @patch('cubane.cms.templatetags.cms_tags.MailSnake')
    def test_should_present_success_message_on_post_without_errors(self, MailSnake):
        self.assertIn(
            'To complete the subscription process, please click the link in the email we just sent you.',
            newsletter_signup_form(self._context(post=True, data={
                'mailchimp_subscription__name': 'Foo Bar',
                'mailchimp_subscription__email': 'foobar@innershed.com'
            }))
        )


    @patch('cubane.cms.templatetags.cms_tags.MailSnake')
    def test_should_present_error_message_on_post_with_error_subscribing_user(self, MailSnake):
        MailSnake().listSubscribe.side_effect = Exception()
        self.assertIn(
            'Unfortunately we were unable to process your request. Please try again later...',
            newsletter_signup_form(self._context(post=True, data={
                'mailchimp_subscription__name': 'Foo Bar',
                'mailchimp_subscription__email': 'foobar@innershed.com'
            }))
        )


class CMSNewsletterSignupFormAjaxTestCase(CMSNewsletterTestCaseBase):
    def test_should_raise_error_without_settings(self):
        with self.assertRaises(ValueError):
            newsletter_signup_form_ajax(Context({}))


    def test_should_return_empty_string_without_mailchimp_api(self):
        settings = Settings()
        self.assertEqual(
            '',
            newsletter_signup_form_ajax(Context({'settings': settings}))
        )


    def test_should_raise_error_without_request(self):
        with self.assertRaisesRegexp(ValueError, 'Expected \'request\' in template context.'):
            newsletter_signup_form_ajax(Context({'settings': self._settings()}))


    def test_should_return_html_for_form(self):
        html = newsletter_signup_form_ajax(self._context(post=False))
        self.assertMarkup(html, 'div', {'class': 'mailchimp-subscription-form'})
        self.assertMarkup(html, 'form', {'method': 'post'})
        self.assertMarkup(html, 'input', {'name': 'mailchimp_subscription__email'})


    def test_should_present_errors_on_post(self):
        html = newsletter_signup_form_ajax(self._context(post=True))
        self.assertMarkup(html, 'div', {'class': 'mailchimp-subscription-form'})
        self.assertMarkup(html, 'div', {'class': 'help-inline'}, 'This field is required.')