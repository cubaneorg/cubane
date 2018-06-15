# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.lib.url import make_absolute_url
from cubane.media.models import Media
from cubane.cms.views import get_cms
import os


class Command(BaseCommand):
    """
    Generate cms test page.
    """
    args = ''
    help = 'Generate cms test page'


    CONTENT = """
        <h1>Headlines</h1>
        <hr/>
        <h1>Headline Level 1</h1>
        <h2>Headline Level 2</h2>
        <h3>Headline Level 3</h3>
        <h4>Headline Level 4</h4>
        <h5>Headline Level 5</h5>
        <h6>Headline Level 6</h6>
        <br/><br/>

        <h1>String and bold Text</h1>
        <hr/>
        <p>Please make sure that <strong>This text is STRONG</strong>.</p>
        <p>Please make sure that <b>This text is BOLD</b>.</p>
        <br/><br/>

        <h1>Italic Text</h1>
        <hr/>
        <p>Please make sure that <em>This text is EMPHASISED</em>.</p>
        <p>Please make sure that <i>This text is italic</i>.</p>
        <br/><br/>

        <h1>Underline Text</h1>
        <hr/>
        <p>Please make sure that <u>This text is UNDERLINED</u>.</p>
        <br/><br/>

        <h1>Inline Anchor</h1>
        <hr/>
        <p>Please make sure that <a href="http://www.google.co.uk/">This text is a link with some hover state</a>.</p>
        <br/><br/>

        <h1>Unordered List</h1>
        <hr/>
        <p>The following should represent an unordered list:</p>
        <ul>
            <li>List Item 1</li>
            <li>List Item 2</li>
            <li>List Item 3</li>
        </ul>
        <br/><br/>

        <h1>Ordered List</h1>
        <hr/>
        <p>The following should represent an ordered list:</p>
        <ol>
            <li>List Item 1</li>
            <li>List Item 2</li>
            <li>List Item 3</li>
        </ol>
        <br/><br/>

        <h1>Table</h1>
        <hr/>
        <p>The following should represent a week breakfast, lunch and dinner table with table headers on the first row and first column.</p>
        <p>Make sure that the table is responsive as well.</p>
        <table>
            <tr>
                <th>&nbsp;</th>
                <th>Monday</th>
                <th>Tuesday</th>
                <th>Wednesday</th>
                <th>Thursday</th>
                <th>Friday</th>
            </tr><tr>
                <th>Breakfast</th>
                <td>Cereal</td>
                <td>Sandwitch</td>
                <td>Omelette</td>
                <td>Cereal</td>
                <td>Eggs and Toast</td>
            </tr><tr>
                <th>Lunch</th>
                <td>Mac'n Cheese</td>
                <td>Pasta</td>
                <td>Salad</td>
                <td>Burgers</td>
                <td>Fish'n Chips</td>
            </tr><tr>
                <th>Dinner</th>
                <td>Sandwiches</td>
                <td>Salad</td>
                <td>Sandwiches</td>
                <td>Sandwiches</td>
                <td>Salad</td>
            </tr>
        </table>

        <h1>Image Alignment</h1>
        <hr/>
        <p>Please make sure that the image and text text are aligned correctly and that there is enough white space between the image and the text.</p>

        <img src="%(img_url)s" width="200" data-width="200" data-height="%(img_height)s" data-cubane-lightbox="false" data-cubane-media-id="%(img_id)s" data-cubane-media-size="custom" style="float: left;">
        <p>The image should appear to the <b>LEFT</b> of this text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus in mi turpis. Proin tristique aliquam aliquet. Nunc sollicitudin pulvinar congue. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec libero ante, rutrum ac erat quis, pulvinar blandit est. Nam porta pretium eros, a lobortis tortor maximus sed. Ut maximus luctus orci ac tincidunt. Ut nec convallis tellus. Mauris sollicitudin risus felis, vitae accumsan orci tincidunt eget. Ut semper ut mi eu venenatis. Sed semper lectus non semper euismod. Quisque mi ipsum, accumsan at augue sed, molestie hendrerit eros. Phasellus cursus elit non massa dignissim blandit.</p>

        <img src="%(img_url)s" width="200" data-width="200" data-height="%(img_height)s" data-cubane-lightbox="false" data-cubane-media-id="%(img_id)s" data-cubane-media-size="custom" style="float: right;">
        <p>The image should appear to the <b>RIGHT</b> of this text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus in mi turpis. Proin tristique aliquam aliquet. Nunc sollicitudin pulvinar congue. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec libero ante, rutrum ac erat quis, pulvinar blandit est. Nam porta pretium eros, a lobortis tortor maximus sed. Ut maximus luctus orci ac tincidunt. Ut nec convallis tellus. Mauris sollicitudin risus felis, vitae accumsan orci tincidunt eget. Ut semper ut mi eu venenatis. Sed semper lectus non semper euismod. Quisque mi ipsum, accumsan at augue sed, molestie hendrerit eros. Phasellus cursus elit non massa dignissim blandit.</p>

        <img src="%(img_url)s" width="200" data-width="200" data-height="%(img_height)s" data-cubane-lightbox="false" data-cubane-media-id="%(img_id)s" data-cubane-media-size="custom" style="margin-left: auto; margin-right: auto;">
        <p>The image should appear <b>CENTER</b> to this text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus in mi turpis. Proin tristique aliquam aliquet. Nunc sollicitudin pulvinar congue. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec libero ante, rutrum ac erat quis, pulvinar blandit est. Nam porta pretium eros, a lobortis tortor maximus sed. Ut maximus luctus orci ac tincidunt. Ut nec convallis tellus. Mauris sollicitudin risus felis, vitae accumsan orci tincidunt eget. Ut semper ut mi eu venenatis. Sed semper lectus non semper euismod. Quisque mi ipsum, accumsan at augue sed, molestie hendrerit eros. Phasellus cursus elit non massa dignissim blandit.</p>

        <img src="%(img_url)s" data-width="200" data-height="%(img_height)s" data-cubane-lightbox="false" data-cubane-media-id="%(img_id)s" data-cubane-media-size="auto" style="float: left;" />
        <p>This image should be visible, add default width in your style file. Please make sure it is displayed correctly on mobile.</p>
    """

    def handle(self, *args, **options):
        """
        Run command.
        """
        cms = get_cms()

        # remove any existing test page
        page = cms.get_page_by_slug('testpage')
        if page:
            page.delete()

        # find some image with high-enough res. or create a new test image
        try:
            img = Media.objects.filter(is_image=True, width__gte=200)[0]
        except IndexError:
            # create new test image
            img_path = os.path.join(settings.BASE_PATH, 'backend', 'static', 'cubane', 'backend', 'img', 'logo.png')
            img = cms.create_media_from_file(path, 'Test Image for TestPage')

        # create new test page
        page = cms.create_page({
            'title': 'Test Page',
            'slug': 'testpage',
        })
        page.set_slot_content(cms.get_default_slotname(), self.CONTENT % {
            'img_url': img.original_url,
            'img_height': 200 / img.aspect_ratio,
            'img_id': img.pk
        })
        page.save()

        print 'Test page generated.'
        print make_absolute_url(page.get_absolute_url(), force_debug=True)
