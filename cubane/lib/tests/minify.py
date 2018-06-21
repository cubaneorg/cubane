# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.utils import override_settings
from cubane.lib.minify import minify_files
from cubane.lib.file import file_get_contents
import tempfile
import os


REQUIRE_JS_MINIFIED = 'define("Point.js",["require","exports","module"],function(c,a,d){var b=function(g,f){this.x=g,this.y=f};b.prototype.add=function(e,f){this.x+=e,this.y+=f},d.exports=b}),define("main",["require","exports","module","Point.js"],function(d,b,f){var c=d("Point.js"),a=c(0,0);a.add(5,3)}),require.config({baseUrl:"/static/testapp/js/"}),require(["main"]),define("require_js_main",function(){});'


@CubaneTestCase.complex()
class LibMinifyFilesTestCase(CubaneTestCase):
    """
    cubane.lib.minify.minify_files

    Compression should:
    - execute template files
    - joined all files (in the order given)
    - removed comments
    - relocate import rules to the top (css)
    - rewrite relative urls, ignoring data urls
    - compress/minify content
    - removed leading/tailing white space
    """
    def test_should_execute_templates(self):
        content = self._get_minified_content('css/style.templating.css', 'css')
        self.assertEqual('body{background-color:#123456}', content)


    def test_should_relocate_import_rules_to_the_top(self):
        content = self._get_minified_content([
            'css/test_a.css',
            'css/test_b.css'   # contains @import
        ], 'css')
        self.assertEqual(
            "@import url('/static/testapp/css/empty.css');" +
            "@import url('/static/testapp/css/foo.css');" +
            "@import url('/static/testapp/css/bar.css');" +
            "@import url('/static/testapp/css/foobar.css');" +
            "body{background-color:red}h1{font-size:24px}",
            content
        )


    def test_should_fix_calc_compressor_bug(self):
        content = self._get_minified_content('css/calc.css', 'css')
        self.assertEqual(
            'body{width:calc(100% + 20px);width:calc((100% - (3 * 4px)) / 4);width:calc(50% * -0.1)}',
            content
        )


    def test_should_minify_js_files(self):
        content = self._get_minified_content([
            'js/test_a.js',
            'js/test_b.js'
        ], 'js')
        self.assertEqual(
            'function testA(){return 5}function testB(){return testA()*2};',
            content
        )


    def test_should_minify_require_js(self):
        content = self._get_minified_content('js/require_js_main.js', 'js')
        self.assertEqual(REQUIRE_JS_MINIFIED, content)


    @override_settings(REQUIRE_JS=[{
        'filename': 'testapp/js/require_js_main.js',
        'baseurl': 'testapp/js',
        'module': 'require_js_main'
    }])
    def test_should_minify_require_js_with_custom_base_path_and_module_name(self):
        content = self._get_minified_content('js/require_js_main.js', 'js')
        self.assertEqual(REQUIRE_JS_MINIFIED, content)


    def test_minify_empty_result_should_yield_empty_content(self):
        content = self._get_minified_content('css/empty.css', 'css')
        self.assertEqual('', content)


    def test_minify_error_should_raise_exception(self):
        base_path = self.get_testapp_static_path()
        dst_filename = os.path.join(tempfile.gettempdir(), 'minified.js')

        with self.assertRaisesRegexp(ValueError, 'Error compressing js content'):
            minify_files([
                os.path.join(base_path, 'js', 'invalid.js')
            ], dst_filename, 'js')


    @override_settings(GENERATE_MINIFY_SRC=True)
    def test_should_generate_src_files_if_feature_is_turned_on(self):
        base_path = self.get_testapp_static_path()
        dst_filename = os.path.join(tempfile.gettempdir(), 'minified.css')
        src_filename = os.path.join(tempfile.gettempdir(), 'minified.css.src')

        minify_files([
            os.path.join(base_path, 'css', 'test_minify.css')
        ], base_path, dst_filename, 'css')

        content = file_get_contents(src_filename)
        os.remove(dst_filename)
        os.remove(src_filename)

        self.assertEqual('\nbody {\n    color: red;\n}\n\n', content)


    def test_should_rewrite_relative_urls(self):
        content = self._get_minified_content('css/rel_url.css', 'css')
        self.assertEqual(
            "@import url('/static/a.css');" +
            "@import url('/static/b.css');" +
            "@import url('/static/c.css');" +
            "@import url('/static/d.css');" +
            "@import url('/static/e.css');" +
            "h1{background-image:url('/static/img/test_images/test.jpg')}" +
            "h2{background-image:url('/static/img/test_images/test.png')}" +
            "h3{background-image:url('/static/img/test_images/test.svg')}" +
            "h4{background-image:url('data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4gPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJncmFkIiBncmFkaWVudFVuaXRzPSJvYmplY3RCb3VuZGluZ0JveCIgeDE9IjAuNSIgeTE9IjAuMCIgeDI9IjAuNSIgeTI9IjEuMCI+PHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iI2ZmZmZmZiIgc3RvcC1vcGFjaXR5PSIwLjAiLz48c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwMDAwMDAiIHN0b3Atb3BhY2l0eT0iMC4xIi8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PHJlY3QgeD0iMCIgeT0iMCIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNncmFkKSIgLz48L3N2Zz4g')}" +
            "h5{background-image:url('/static/img/foo.jpg')}" +
            "h6{background-image:url('/media/img/bar.jpg')}",
            content
        )


    def _get_minified_content(self, filenames, filetype):
        """
        Minify given list of files of given file type.
        """
        if not isinstance(filenames, list):
            filenames = [filenames]

        dst_filename = os.path.join(tempfile.gettempdir(), 'minified')
        base_path = self.get_testapp_static_path()
        filenames = [os.path.join(base_path, filename) for filename in filenames]

        minify_files(filenames, base_path, dst_filename, filetype)
        content = file_get_contents(dst_filename)
        os.remove(dst_filename)

        return content