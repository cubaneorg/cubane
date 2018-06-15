# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.text import slugify
from cubane.lib.utf8 import utf8_stream, DETECT_ENCODING
from cubane.ishop import get_category_model, get_product_model
from cubane.ishop.models import Variety, VarietyOption, VarietyAssignment
from cubane.ishop.models import ProductSKU
from cubane.cms.views import get_cms
from cubane.media.models import Media
from cubane.media.views import load_media_gallery, save_media_gallery
from cubane.tasks import TaskRunner
from copy import copy
from decimal import Decimal
import cubane.lib.ucsv as csv
import re
import urlparse
from urllib import urlencode


class ShopInventoryImporter(object):
    FIELDS = [
        'sku',
        'description',
        'price',
        'stock',
        'barcode',
        'on-website'
    ]


    @property
    def has_errors(self):
        """
        Return True, if there are any errors.
        """
        return len(self._errors) > 0 or self._row_error_occured


    @property
    def num_records_processed(self):
        """
        Return the number of records (input rows) processed.
        """
        return self._num_records_processed


    def import_from_stream(self, request, stream, encoding=DETECT_ENCODING):
        """
        Import shop data from given stream, read the data as CSV data, process
        the data through model forms and import successfully validated
        data for products, SKUs, categories and images.
        """
        # create CSV reader
        self._reader = csv.reader(
            utf8_stream(stream, encoding=encoding),
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL,
            encoding=encoding
        )
        self._line = 1
        self._user = request.user
        self._errors = []
        self._row_error_occured = False
        self._num_records_processed = 0

        # get cms
        self.cms = get_cms()

        # read headers
        header, header_labels = self._get_headers()

        # read data lines as dict.
        data = self._get_lines_as_dict(header)

        # process data
        self._import_inventory(data)

        # collect row-specific errors
        for row in data:
            if self._row_has_errors(row):
                for error in row.get('_errors', []):
                    self._error_on_line(row.get('_line_number'), error.get('message'), self._get_row_html_excerpt(row, error.get('field'), header_labels))

        # sort error messages by line number
        self._errors.sort(key=lambda error: error.get('line'))


    def _get_headers(self):
        """
        Read header names
        """
        # read header line
        header_labels = self._read_line()
        header = [slugify(cell.strip()) for cell in header_labels]
        for i, cell in enumerate(header):
            for field in self.FIELDS:
                if field in cell:
                    header[i] = field
        return header, header_labels


    def _import_inventory(self, data):
        """
        Process inventory data.
        """
        sku_seen = []
        for row in data:
            sku = row.get('sku')
            barcode = row.get('barcode')
            price = row.get('price')
            stock = row.get('stock')
            on_website = row.get('on-website')

            # we need at least an SKU
            if not sku:
                self._field_error(row, 'sku', 'SKU \'<em>%s</em>\' cannot be empty.' % sku)
                continue

            # sku seen before
            if sku in sku_seen:
                self._field_error(row, 'sku', 'SKU \'<em>%s</em>\' appears multiple times.' % sku)
                continue

            # on website?
            if not (on_website and on_website.lower() == 'yes'):
                continue

            # only process this item, if there is actually data associated with
            # it, like stock level or price
            if not (barcode or price or stock):
                continue

            # find matching sku (product or sku record)
            changed = False
            try:
                sku = ProductSKU.objects.get(sku=sku)
                changed = self._update(sku, barcode, price, stock)
            except ProductSKU.DoesNotExist:
                try:
                    product = Product.objects.get(sku=sku)
                    changed = self._update(product, barcode, price, stock)
                except Product.DoesNotExist:
                    self._field_error(row, 'sku', 'Unknown SKU \'<em>%s</em>\' appears to not match any known SKU number in the system.' % sku)

            if changed:
                self._num_records_processed += 1

            sku_seen.append(sku)


    def _update(self, obj, barcode, price, stocklevel):
        """
        Update the given entity regarding barcode, price and stock level.
        """
        changed = False

        if barcode and obj.barcode != barcode:
            obj.barcode = barcode
            changed = True

        if price and obj.price != price:
            obj.price = price
            changed = True

        if stocklevel and obj.stocklevel != stocklevel:
            obj.stocklevel = stocklevel
            changed = True

        if changed:
            obj.save()

        return changed


    def _get_lines_as_dict(self, header):
        """
        Read the rest of the file and return a list of dict., mapped by
        header name.
        """
        data = []
        line = self._line - 1
        while True:
            # line counter
            line += 1

            # read next row until done
            try:
                row = self._read_line()
            except StopIteration:
                break

            # ignore rows that are all together empty
            if len(filter(lambda cell: cell != '', row)) == 0:
                continue

            # convert data row into dict.
            d = {}
            for i, cell in enumerate(row):
                # strip cell value (if string)
                if isinstance(cell, basestring):
                    cell = cell.strip()

                if header[i]:
                    # header exist. Add to dict, if not there yet
                    if header[i] not in d:
                        d[header[i]] = cell

            # append line number
            d['_line_number'] = line

            # append data record
            data.append(d)
        return data


    def _read_line(self):
        """
        Read and return the next line.
        """
        line = self._reader.next()
        self._line += 1
        return line


    def _error(self, message, excerpt_html=None):
        """
        Report given error message for the current line read from input stream.
        """
        self._error_on_line(self._line, message, excerpt_html)


    def _error_on_line(self, line, message, excerpt_html=None):
        """
        Report given error message for the given line number.
        """
        self._errors.append({
            'line': line,
            'message': message,
            'excerpt_html': excerpt_html
        })


    def _get_row_html_excerpt(self, row, error_fieldname, header_labels):
        """
        Generate an excerpt of the given row which then may become part of
        an error message concerning the given row.
        """
        html = ['<table class="full-with small-content">']

        # headers
        html.append('<tr>')
        for label in header_labels:
            if label == error_fieldname:
                label = '<em>%s</em>' % label

            html.append('<th>%s</th>' % label)
        html.append('</tr>')

        # data row
        html.append('<tr>')
        for fieldname in header_labels:
            if fieldname:
                value = row.get(fieldname, '')

                if isinstance(value, list):
                    value = ', '.join([unicode(v) for v in value if v != ''])

                if fieldname == error_fieldname:
                    value = '<em>%s</em>' % value

                html.append('<td>%s</td>' % value)
        html.append('</tr>')
        html.append('</table>')

        return ''.join(html)


    def _row_error(self, row, message):
        """
        Generate the given error message for the given row.
        """
        self._field_error(row, None, message)


    def _field_error(self, row, fieldname, message):
        """
        Generate the given error message for the given row and field.
        """
        if '_errors' not in row:
            row['_errors'] = []

        row['_errors'].append({
            'message': message,
            'field': fieldname
        })

        self._row_error_occured = True


    def _row_has_errors(self, row):
        """
        Return True, if the given row has at least one error.
        """
        return len(row.get('_errors', [])) > 0


    def get_formatted_errors(self):
        """
        Return list of all error messages containing line number and sorted by
        line number. It also contains an excerpt of the input line.
        """
        return [
            '<em>Line %d</em>: %s%s' % (
                error.get('line'),
                error.get('message'),
                (error.get('excerpt_html') if error.get('excerpt_html') else '')
            ) for error in self._errors
        ]


class ShopDataImporter(object):
    REQUIRED_FIELDS = [
        'sku',
        'product_sku',
        'title',
        'categories',
        'price'
    ]


    @property
    def has_errors(self):
        """
        Return True, if there are any errors.
        """
        return len(self._errors) > 0 or self._row_error_occured


    @property
    def num_records_processed(self):
        """
        Return the number of records (input rows) processed.
        """
        return self._num_records_processed


    def __init__(self, import_images=True):
        """
        Create a new shop data importer for the given user.
        """
        self._import_images = import_images


    def import_from_stream(self, request, stream, encoding=DETECT_ENCODING):
        """
        Import shop data from given stream, read the data as CSV data, process
        the data through model forms and import successfully validated
        data for products, SKUs, categories and images.
        """
        # create CSV reader
        self._reader = csv.reader(
            utf8_stream(stream, encoding=encoding),
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL
        )
        self._request = request
        self._line = 1
        self._user = request.user
        self._errors = []
        self._row_error_occured = False
        self._num_records_processed = 0

        # get cms
        self.cms = get_cms()

        # skip lines
        lines_skipped = settings.CUBANE_SHOP_IMPORT.get('skip')
        self._skip_lines(lines_skipped)

        # read headers
        (header, header_labels) = self._get_headers()

        # read data lines as dict.
        data = self._get_lines_as_dict(header)

        # verify input data
        self.verify_data(data)

        # import categories
        self.import_categories(data)

        # import varieties and options
        varieties = self.import_varieties(header_labels)
        self.import_varity_options(data, varieties)

        # import products, variety assignments and SKUs
        groups = self.import_products(data)
        self.import_variety_assignments(groups, varieties)
        self.import_product_sku(groups, varieties)

        # download and import images, but only if we have not observed any
        # errors yet, otherwise it is likely that we will end up downloading
        # media data for no good reason, since we will revert all changes due
        # to errors anyhow...
        if self._import_images and not self.has_errors:
            self.import_images(groups)

            if TaskRunner.is_available():
                TaskRunner.notify()

        # collect row-specific errors
        for row in data:
            if self._row_has_errors(row):
                for error in row.get('_errors', []):
                    self._error_on_line(row.get('_line_number'), error.get('message'), self._get_row_html_excerpt(row, error.get('field'), header_labels))

        # sort error messages by line number
        self._errors.sort(key=lambda error: error.get('line'))

        # number of records processed
        self._num_records_processed = len(data)


    def get_formatted_errors(self):
        """
        Return list of all error messages containing line number and sorted by
        line number. It also contains an excerpt of the input line.
        """
        return [
            '<em>Line %d</em>: %s%s' % (
                error.get('line'),
                error.get('message'),
                (error.get('excerpt_html') if error.get('excerpt_html') else '')
            ) for error in self._errors
        ]


    def _read_line(self):
        """
        Read and return the next line.
        """
        line = self._reader.next()
        self._line += 1
        return line


    def _error(self, message, excerpt_html=None):
        """
        Report given error message for the current line read from input stream.
        """
        self._error_on_line(self._line, message, excerpt_html)


    def _error_on_line(self, line, message, excerpt_html=None):
        """
        Report given error message for the given line number.
        """
        self._errors.append({
            'line': line,
            'message': message,
            'excerpt_html': excerpt_html
        })


    def _get_row_html_excerpt(self, row, error_fieldname, header_labels):
        """
        Generate an excerpt of the given row which then may become part of
        an error message concerning the given row.
        """
        html = ['<table class="full-with small-content">']

        # headers
        html.append('<tr>')
        for label in header_labels:
            if label == error_fieldname:
                label = '<em>%s</em>' % label

            html.append('<th>%s</th>' % label)
        html.append('</tr>')

        # data row
        html.append('<tr>')
        for fieldname in header_labels:
            if fieldname:
                value = row.get(fieldname, '')

                if isinstance(value, list):
                    value = ', '.join([unicode(v) for v in value if v != ''])

                if fieldname == error_fieldname:
                    value = '<em>%s</em>' % value

                html.append('<td>%s</td>' % value)
        html.append('</tr>')
        html.append('</table>')

        return ''.join(html)


    def _row_error(self, row, message):
        """
        Generate the given error message for the given row.
        """
        self._field_error(row, None, message)


    def _field_error(self, row, fieldname, message):
        """
        Generate the given error message for the given row and field.
        """
        if '_errors' not in row:
            row['_errors'] = []

        row['_errors'].append({
            'message': message,
            'field': fieldname
        })

        self._row_error_occured = True


    def _row_has_errors(self, row):
        """
        Return True, if the given row has at least one error.
        """
        return len(row.get('_errors', [])) > 0


    def _parse_decimal(self, decimal_value):
        """
        Parse decimal value for given row and decimal value (string).
        """
        try:
            return Decimal(decimal_value.strip('£').replace(',', ''))
        except:
            raise ValueError()


    def _skip_lines(self, lines):
        """
        Skip given number of lines.
        """
        for i in range(0, lines):
            self._read_line()


    def get_download_link(self, link):
        """
        Normalise the given download link.
        """
        link = link.strip()
        if link.startswith('https://www.dropbox.com/'):
            url_parts = list(urlparse.urlparse(link))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update({'dl': '1'})
            url_parts[4] = urlencode(query)
            link = urlparse.urlunparse(url_parts)
        return link


    def _get_headers(self):
        """
        Read header names
        """
        # read header line
        org_header = self._read_line()

        # get normalised headers from settings
        norm_header = copy(settings.CUBANE_SHOP_IMPORT.get('header'))
        header_map = {}
        for key, title in norm_header.items():
            header_map[title.strip()] = key

        # normalise original headers and re-encode them using the
        # normalised system names
        header = []
        header_labels = {}
        for title in org_header:
            stripped_title = title.strip()
            if stripped_title in header_map:
                mapped_title = header_map.get(stripped_title)
                if mapped_title in header:
                    self._error('Header title \'<em>%s</em>\' appears more than once.' % title)
                header.append(mapped_title)
                header_labels[mapped_title] = [mapped_title.title()]
            else:
                # the name might match multiple headers
                matched = False
                for pattern, fieldname in header_map.items():
                    m = re.match(pattern, stripped_title)
                    if m:
                        header.append(fieldname)

                        if fieldname not in header_labels:
                            header_labels[fieldname] = []
                        if len(m.groups()) == 0:
                            header_labels[fieldname].append(m.group(0).title())
                        else:
                            header_labels[fieldname].append(m.groups()[-1].title())

                        matched = True
                        break

                if not matched:
                    # unknown column, skip header
                    header.append(None)

        return (header, header_labels)


    def _get_lines_as_dict(self, header):
        """
        Read the rest of the file and return a list of dict., mapped by
        header name.
        """
        data = []
        line = self._line - 1
        while True:
            # line counter
            line += 1

            # read next row until done
            try:
                row = self._read_line()
            except StopIteration:
                break

            # ignore rows that are all together empty
            if len(filter(lambda cell: cell != '', row)) == 0:
                continue

            # identify multi-value columns
            multi_value = {}
            for field in header:
                multi_value[field] = len(filter(lambda x: x == field, header)) > 1

            default = settings.CUBANE_SHOP_IMPORT.get('default', {})

            # convert data row into dict.
            d = {}
            for i, cell in enumerate(row):
                # strip cell value (if string)
                if isinstance(cell, basestring):
                    cell = cell.strip()

                if header[i]:
                    # header exist. Add to dict, if not there yet
                    if header[i] not in d:
                        # single value
                        d[header[i]] = cell

                        # make value a list if the column exists multiple times
                        if multi_value.get(header[i]):
                            # a list with an empty value becames an empty list
                            if d[header[i]] != '':
                                d[header[i]] = [d[header[i]]]
                            else:
                                d[header[i]] = []
                    else:
                        d[header[i]].append(cell)

            # handle default values
            for field, ref_field in default.items():
                if field not in d or d.get(field) == '' or d.get(field) == []:
                    if ref_field in d:
                        d[field] = d[ref_field]

            # append line number
            d['_line_number'] = line

            # append data record
            data.append(d)
        return data


    def verify_data(self, data):
        """
        Verify that the input data is valid.
        """
        required_fields = self.REQUIRED_FIELDS + self.get_required_fields()
        for row in data:
            # required fields
            for required_field in required_fields:
                if required_field not in row or row.get(required_field) == [] or row.get(required_field) == '':
                    self._field_error(row, required_field, 'Required field \'<em>%s</em>\' is empty but a value is required.' % required_field)


    def get_required_fields(self):
        """
        Return required fields.
        """
        return []


    def import_categories(self, data):
        """
        Import missing categories and change category hierarchy according to
        categories found in the input file. Further, add the field '_category'
        to the data set that refers to the actual category instance for the
        product.
        """
        category_model = get_category_model()
        for row in data:
            parent_category = None
            category_titles = []

            categories = filter(lambda x: x != '', row.get('categories'))
            for category_title in categories:
                category_titles.append(category_title)
                slug = slugify('-'.join(category_titles))
                try:
                    category = category_model.objects.get(parent=parent_category, slug=slug)
                except category_model.DoesNotExist:
                    category = category_model()
                    category.title = category_title
                    category.slug = slug

                category.parent = parent_category
                category.set_nav(settings.CMS_DEFAULT_NAVIGATION)
                category.save()

                parent_category = category

            # inject actual category back into the data
            row['_category'] = parent_category


    def import_varieties(self, header_labels):
        """
        Import varieties and variety options.
        """
        varieties = []
        for title in header_labels.get('variety_options'):
            slug = slugify(title)
            try:
                variety = Variety.objects.get(slug=slug)
            except Variety.DoesNotExist:
                variety = Variety()
                variety.slug = slug
                variety.style = Variety.STYLE_LIST
                variety.display_title = title

            variety.title = title
            variety.enabled = True
            variety.save()
            varieties.append(variety)
        return varieties


    def import_varity_options(self, data, varieties):
        """
        Import variety options for given set of varieties.
        """
        # collect all presented options for each variety
        for v in varieties:
            v._options = []
        for row in data:
            options = row.get('variety_options')
            for variety, option in zip(varieties, options):
                if option != '' and not option in variety._options:
                    variety._options.append(option)

        # create individual options for each variety
        for variety in varieties:
            seq = 1
            for option_title in variety._options:
                try:
                    option = VarietyOption.objects.get(variety=variety, title=option_title)
                except VarietyOption.DoesNotExist:
                    option = VarietyOption()
                    option.title = option_title
                    option.variety = variety

                option.seq = seq
                option.enabled = True
                option.save()

                seq += 1


    def import_products(self, data):
        """
        Import products (groups).
        """
        # group input data by product sku
        groups = {}
        for row in data:
            product_sku = row.get('product_sku')
            if product_sku not in groups:
                groups[product_sku] = {
                    'rows': []
                }
            groups[product_sku].get('rows').append(row)

        # combine certain fields per group
        for group in groups.values():
            rows = group.get('rows')
            group['title'] = rows[0].get('title')
            group['category'] = rows[0].get('_category')
            group['images'] = []
            group['price'] = None
            for row in rows:
                try:
                    price = self._parse_decimal(row.get('price'))
                except ValueError:
                    self._field_error(row, 'price', 'Unable to parse cell value \'<em>%s</em>\' as a decimal value for determining the lowest product price.' % row.get('price'))
                    price = Decimal('0.00')

                row['price_parsed'] = price

                # lowest price is base price for product
                if row.get('price_parsed') < group.get('price') or group.get('price') is None:
                    group['price'] = row.get('price_parsed')

                # all image links without duplicates in the order given
                for image in row.get('images'):
                    if image not in group.get('images'):
                        group['images'].append(image)

        # process products (groups).
        product_model = get_product_model()
        for product_sku, group in groups.items():
            row = group.get('rows')[0]

            # title cannot be empty
            if not group.get('title'):
                continue

            try:
                product = product_model.objects.get(sku=product_sku)
            except product_model.DoesNotExist:
                product = product_model()
                product.sku = product_sku

            # title cannot already exist, unless for the product
            # we are working with
            title = group.get('title')
            products_with_same_title = product_model.objects.filter(title=title)
            if product.pk:
                products_with_same_title = products_with_same_title.exclude(pk=product.pk)
            if products_with_same_title.count() > 0:
                self._field_error(row, 'title', 'The product title \'%s\' is used multiple times. A product with the same title already exists with the SKUs \'%s\'.' % (
                    title,
                    ', '.join(['<em>%s</em>' % p.sku for p in products_with_same_title])
                ))
                continue

            # slug cannot already exist, unless for the product
            # we are working with
            slug = slugify(title)
            products_with_same_slug = product_model.objects.filter(slug=slug)
            if product.pk:
                products_with_same_slug = products_with_same_slug.exclude(pk=product.pk)
            if products_with_same_slug.count() > 0:
                self._field_error(row, 'title', 'The product slug \'%s\', which has been automatically generated from the product title \'%s\' already exists. A product with the same title already exists with the SKUs \'%s\'.' % (
                    slug,
                    title,
                    ', '.join(['<em>%s</em>' % p.sku for p in products_with_same_slug])
                ))
                continue

            product.title = title
            product.slug = slug
            product.category = group.get('category')
            product.price = group.get('price')
            product.draft = False
            self.on_import_product(product, group)
            product.save()
            group['product'] = product

        return groups


    def import_variety_assignments(self, groups, varieties):
        """
        Import variety assignments
        """
        for product_sku, group in groups.items():
            product = group.get('product')
            if not product:
                continue

            variety_options = []
            for row in group.get('rows'):
                # determine unique set of variety options used by the product
                for variety, option in zip(varieties, row.get('variety_options')):
                    if option != '':
                        option = VarietyOption.objects.get(variety=variety, title=option)
                        if option not in variety_options:
                            variety_options.append(option)

            # assign all varieties to the product
            assignment_ids = []
            for option in variety_options:
                try:
                    assignment = VarietyAssignment.objects.get(product=product, variety_option=option)
                except VarietyAssignment.DoesNotExist:
                    assignment = VarietyAssignment()
                    assignment.product = product
                    assignment.variety_option = option
                    assignment.save()
                assignment_ids.append(assignment.id)

            # delete all deprecated assignments
            deprecated_assignments = VarietyAssignment.objects.filter(product=product).exclude(pk__in=assignment_ids)
            for assignment in deprecated_assignments:
                assignment.delete()


    def import_product_sku(self, groups, varieties):
        """
        Import SKU records
        """
        for product_sku, group in groups.items():
            product = group.get('product')
            if not product:
                continue

            for row in group.get('rows'):
                variety_options = []
                for variety, option in zip(varieties, row.get('variety_options')):
                    if option != '':
                        option = VarietyOption.objects.get(variety=variety, title=option)
                        variety_options.append(option)

                # generate product skus
                try:
                    sku = ProductSKU.objects.get(sku=row.get('sku'))
                except ProductSKU.DoesNotExist:
                    sku = ProductSKU()

                sku.product = product
                sku.sku = row.get('sku')
                try:
                    sku.price = self._parse_decimal(row.get('price'))
                except ValueError:
                    self._field_error(row, 'price', 'Unable to parse cell value \'<em>%s</em>\' as a decimal value for field \'price\'.' % row.get('price'))
                sku.save()
                sku.variety_options = variety_options


    def import_images(self, groups):
        """
        After all data is sound without any errors, import images.
        """
        self.import_product_images(groups)


    def import_product_images(self, groups):
        """
        Import product images.
        """
        # process all products
        for product_sku, group in groups.items():
            product = group.get('product')
            if not product:
                continue

            # create media folder for each product
            product_folder = self.get_product_media_folder(product, group)

            # process all product images
            media = []
            image_links = group.get('images', [])
            for image_link in image_links:
                if image_link != '':
                    m = self.download_media(image_link, product_folder)
                    media.append(m)

            if len(media) > 0:
                # assign first image in the set as the main image of the product
                product.image = media[0]
                product.save()

                # assign all images as the gallery for the product
                save_media_gallery(self._request, request, product, media)


    def download_media(self, url, folder=None):
        """
        Download a media asset with given link (or receive from previously
        downloaded asset).
        """
        url = self.get_download_link(url)

        try:
            m = Media.objects.get(external_url=url)
        except Media.DoesNotExist:
            # create empty media item
            if TaskRunner.is_available():
                m = self.cms.create_blank_external_media(url, folder=folder)
            else:
                m = self.cms.create_media_from_url(url, folder=folder)
                m.external_url = url

        if m.pk is None or m.parent_id != folder.pk:
            m.parent = folder
            m.save()

        return m


    def on_import_product(self, product, group):
        """
        Perform additional operation before the given product is saved.
        """
        pass


    def get_product_media_folder(self, product, group):
        """
        Return a media folder (or None for root), that is used to attache
        product image shots for the given product/group.
        """
        # create media folder for products
        products_folder = cms.create_media_folder('Products')
        return self.cms.create_media_folder(product.title, products_folder)