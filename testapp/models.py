# coding=UTF-8
from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from cubane.models import DateTimeBase, DateTimeReadOnlyBase, Country
from cubane.models.fields import MultiSelectField, TagsField
from cubane.cms.models import Page, Entity, ChildPage, SettingsBase, PageAbstract
from cubane.media.models import Media
from cubane.enquiry.models import AdvancedEnquiry
from cubane.directory.models import DirectoryContentBase
from cubane.directory.models import DirectoryCategory
from cubane.directory.models import DirectoryContentAggregator
from cubane.directory.models import DirectoryContentAndAggregator
from cubane.directory.models import DirectoryContentEntity
from cubane.directory.models import DirectoryEntity
from cubane.directory.models import DirectoryPageAggregator
from cubane.ishop.models import ShopEntity
from cubane.ishop.models import ProductBase, CategoryBase, OrderBase, CustomerBase, ShopSettings
from cubane.ishop.models import FeaturedItemBase
import os


class Settings(ShopSettings):
    """
    CMS settings
    """
    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import SettingsForm
        return SettingsForm


class Enquiry(AdvancedEnquiry):
    """
    Enquiry.
    """
    class Meta:
        verbose_name        = 'Enquiry'
        verbose_name_plural = 'Enquiries'


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import EnquiryForm
        return EnquiryForm


class CustomPage(PageAbstract):
    class Meta:
        ordering = ['seq', '_meta_description']


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import CustomPageForm
        return CustomPageForm


class CustomDirectoryPage(PageAbstract, DirectoryPageAggregator):
    """
    CMS Page with directory content aggregator capabilities.
    """
    @classmethod
    def get_form(cls): # pragma: no cover
        from cubane.testapp.forms import CustomDirectoryPageForm
        return CustomDirectoryPageForm


class CustomChildPage(ChildPage):
    class Meta:
        verbose_name        = 'Custom Child Page'
        verbose_name_plural = 'Custom Child Pages'


    @classmethod
    def get_form(cls): # pragma: no cover
        from cubane.testapp.forms import CustomChildPageForm
        return CustomChildPageForm


class TestModelBase(Entity):
    class Meta:
        abstract = True


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True,
        default=''
    )

    text = models.CharField(
        verbose_name='Text',
        max_length=255,
        null=True
    )


    def get_uppercase_title(self):
        return self.title.upper() if self.title else ''


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import TestModelForm
        return TestModelForm


    def __unicode__(self): # pragma: no cover
        return self.title


class TestGroupedModelA(Entity):
    class Meta:
        verbose_name        = 'Test Grouped Model A'
        verbose_name_plural = 'Test Grouped Models A'

    class Listing:
        group = 'Group'

    def __unicode__(self): # pragma: no cover
        return ''


class TestGroupedModelB(Entity):
    class Meta:
        verbose_name        = 'Test Grouped Model B'
        verbose_name_plural = 'Test Grouped Models B'

    class Listing:
        group = 'Group'

    def __unicode__(self): # pragma: no cover
        return ''


class TestModel(TestModelBase):
    """
    Model for use in tests.
    """
    class Meta:
        verbose_name        = 'Test Model'
        verbose_name_plural = 'Test Models'

    class Listing:
        pass


    image = models.ForeignKey(
        Media,
        verbose_name='Image',
        null=True,
        blank=True
    )

    def __unicode__(self): # pragma: no cover
        return ''

    @property
    def parent_model(self): # pragma: no cover
        if self.id:
            m = TestModel()
            m.title = 'Bar'
            return m
        else:
            return None


class TestModelFilterByCountry(models.Model):
    class Meta:
        verbose_name        = 'Test Model Filter by Country'
        verbose_name_plural = 'Test Models Filter by Country'


    class Listing:
        filter_by = [
            'title',
            'country'
        ]


    title = models.CharField(max_length=255)
    country = models.ForeignKey(Country)


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import TestModelFilterByCountryForm
        return TestModelFilterByCountryForm


class TestLikeIndexUniqueModel(models.Model):
    title = models.TextField(
        verbose_name='Title',
        db_index=True,
        unique=True
    )

class TestLikeIndexNotUniqueModel(models.Model):
    title = models.TextField(
        verbose_name='Title',
        db_index=True
    )

class TestFieldWithoutIndexModel(models.Model):
    title = models.TextField(
        verbose_name='Title',
    )


class TestModelWithoutDefault(models.Model):
    title = models.CharField(max_length=32, null=True)
    test = models.CharField(max_length=8, null=False)


class TestModelWithJsonFields(TestModelBase):
    class Meta:
        verbose_name        = 'Test Model With Json Fields'
        verbose_name_plural = 'Test ModelS With Json Fields'

    def get_json_fieldnames(self):
        return ['id', 'title']


class TestModelWithManyToMany(Entity):
    """
    Model for use in tests.
    """
    class Meta:
        verbose_name        = 'Test Model With ManyToMany'
        verbose_name_plural = 'Test Model with ManyToMany'


    class Listing:
        filter_by = ['pages']


    title = models.CharField(
        verbose_name='Title',
        max_length=255
    )

    pages = models.ManyToManyField(
        Page
    )


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import TestModelWithManyToManyForm
        return TestModelWithManyToManyForm


    def __unicode__(self): # pragma: no cover
        return self.title


class TestModelImportExport(Entity):
    """
    Model to test import/export (CSV)
    """
    class Meta:
        verbose_name        = 'Test Model Import Export'
        verbose_name_plural = 'Test Model Import Export'


    class Listing:
        data_columns = [
            'id',
            'title',
            'enabled',
            'enabled_display',
            'address_type',
            'is_company'
        ]


    ADDRESS_TYPE_BUSINESS = 1
    ADDRESS_TYPE_HOME     = 2
    ADDRESS_TYPE_CHOICES = (
        (ADDRESS_TYPE_BUSINESS, 'Business'),
        (ADDRESS_TYPE_HOME,     'Home')
    )


    title = models.CharField(
        verbose_name='Title',
        null=True,
        blank=True,
        max_length=255
    )

    enabled = models.BooleanField(
        verbose_name='Enabled'
    )

    address_type = models.IntegerField(
        verbose_name='Display_type',
        choices=ADDRESS_TYPE_CHOICES
    )

    email = models.CharField(
        verbose_name='Email',
        null=True,
        blank=True,
        max_length=255
    )

    user = models.ForeignKey(User, null=True, blank=True)


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import TestModelImportExportForm
        return TestModelImportExportForm


    @property
    def enabled_display(self):
        return 'yes' if self.enabled else 'no'


    def is_company(self):
        return self.address_type == self.ADDRESS_TYPE_BUSINESS


    def __unicode__(self): # pragma: no cover
        return self.title


class TestModelImportNumericZero(Entity):
    class Meta:
        verbose_name        = 'Test Model Import Numeric Zero'
        verbose_name_plural = 'Test Model Import Numeric Zero'


    class Listing:
        data_columns = [
            'id',
            'number'
        ]


    number = models.IntegerField()


    @classmethod
    def get_form(cls): # pragma: no cover
        from cubane.testapp.forms import TestModelImportNumericZeroForm
        return TestModelImportNumericZeroForm


    def __unicode__(self): # pragma: no cover
        return ''


class Location(DateTimeBase):
    """
    Test entity with geo-location
    """
    class Meta:
        verbose_name        = 'Location'
        verbose_name_plural = 'Locations'

    lat = models.FloatField(
        verbose_name='Latitude',
        db_index=True,
        help_text='Geographic latitude degrees (N/S)'
    )

    lng = models.FloatField(
        verbose_name='Longitude',
        db_index=True,
        help_text='Geographic longitude degrees (E/W)'
    )

    def __unicode__(self): # pragma: no cover
        return '%s : %s' % (self.lat, self.lng)


class TestFTSPart(DateTimeBase):
    class Meta:
        verbose_name        = 'Test FTS Part'
        verbose_name_plural = 'Test FTS Parts'

    class FTS:
        columns = {
            'fts_index': ['partno', 'name']
        }

    partno = models.CharField(max_length=32)
    name = models.CharField(max_length=255)

    def __unicode__(self): # pragma: no cover
        return self.partno


class TestModelWithPermissionsDefined(TestModelBase):
    class Meta:
        verbose_name        = 'Test Model With Permissions Defined'
        verbose_name_plural = 'Test Models With Permissions Defined'

    can_edit = False


class TestDirectoryContent(DirectoryContentBase):
    class Meta:
        verbose_name        = 'Test Directory Content'
        verbose_name_plural = 'Test Directory Content'


class TestDirectoryContentWithBackendSections(DirectoryContentBase):
    class Meta:
        verbose_name        = 'Test DC With Backend Sections'
        verbose_name_plural = 'Test DC With Backend Sections'

    BACKEND_SECTION_A        = 1
    BACKEND_SECTION_B        = 2
    BACKEND_SECTION_CHOICES  = (
        (BACKEND_SECTION_A, 'A'),
        (BACKEND_SECTION_B, 'B'),
    )

    BACKEND_SECTION_TITLE = {
        BACKEND_SECTION_A: 'A',
        BACKEND_SECTION_B: 'B',
    }

    backend_section = models.IntegerField(
        db_index=True,
        editable=False,
        default=BACKEND_SECTION_A,
        choices=BACKEND_SECTION_CHOICES
    )


    @classmethod
    def get_backend_sections(cls):
        return ('backend_section', cls.BACKEND_SECTION_CHOICES)


    @classmethod
    def get_backend_section_title(cls, backend_section):
        return cls.BACKEND_SECTION_TITLE.get(backend_section)


class TestContentAggregator(DirectoryContentAndAggregator):
    class Meta:
        verbose_name        = 'Test Content Aggregator'
        verbose_name_plural = 'Test Content Aggregators'


class TestDirectoryCategory(DirectoryCategory):
    class Meta:
        verbose_name        = 'Test Directory Category'
        verbose_name_plural = 'Test Directory Categories'


class TestDirectoryContentEntity(DirectoryContentEntity):
    class Meta:
        verbose_name        = 'Test Directory Content Entity'
        verbose_name_plural = 'Test Directory Content Entities'


    title = models.CharField(max_length=255, null=True)
    image = models.ForeignKey(Media, null=True, blank=True)


    def __unicode__(self): # pragma: no cover
        return self.title


class TestDirectoryEntity(DirectoryEntity):
    class Meta:
        verbose_name        = 'Test Directory Entity'
        verbose_name_plural = 'Test Directory Entities'

    image = models.ForeignKey(Media, null=True, blank=True)


    def __unicode__(self): # pragma: no cover
        return ''


class TestDirectoryPageAggregator(DirectoryPageAggregator):
    class Meta:
        verbose_name        = 'Test Directory Page Aggregator'
        verbose_name_plural = 'Test Directory Page Aggregators'


class TestDirectoryChildPageAggregator(ChildPage, DirectoryContentAggregator):
    class Meta:
        verbose_name        = 'Test Directory Child Page Aggregator'
        verbose_name_plural = 'Test Directory Child Page Aggregators'


class Product(ProductBase):
    pass


class Category(CategoryBase):
    pass


class Order(OrderBase):
    pass


class Customer(CustomerBase):
    pass


class Brand(ShopEntity):
    def __unicode__(self): # pragma: no cover
        return ''


class BrandWithImage(ShopEntity):
    image = models.ForeignKey(
        Media,
    )

    def __unicode__(self): # pragma: no cover
        return ''


class BrandWithGroup(ShopEntity):
    class Listing:
        group = 'Foo'

    def __unicode__(self): # pragma: no cover
        return ''


class FeaturedItem(FeaturedItemBase):
    pass


class TestMultiSelectField(models.Model):
    class Meta:
        verbose_name        = 'Test MultiSelect Field'
        verbose_name_plural = 'Test MultiSelect Fields'

    DEPARTMENT_CHOICES = (
        ('it', 'IT'),
        ('sales', 'Sales'),
        ('marketing', 'Marketing'),
        ('qa', 'Quality Assurance'),
        ('development', 'Development'),
        ('design', 'Design'),
    )

    department = MultiSelectField(
        choices=DEPARTMENT_CHOICES,
        default='it,sales',
    )


class TestNullableMultiSelectField(models.Model):
    class Meta:
        verbose_name        = 'Test Nullable MultiSelect Field'
        verbose_name_plural = 'Test Nullable MultiSelect Fields'


    DEPARTMENT_CHOICES = (
        ('it', 'IT'),
        ('sales', 'Sales'),
        ('marketing', 'Marketing'),
        ('qa', 'Quality Assurance'),
        ('development', 'Development'),
        ('design', 'Design'),
    )

    department = MultiSelectField(
        choices=DEPARTMENT_CHOICES,
        null=True,
        blank=True
    )


class TestMultiSelectOptGroupChoicesField(models.Model):
    class Meta:
        verbose_name        = 'Test OptGroup MultiSelect Field'
        verbose_name_plural = 'Test OptGroup MultiSelect Fields'

    DEPARTMENT_CHOICES = (
        ('Development', [
            ('it', 'IT'),
            ('qa', 'Quality Assurance'),
            ('development', 'Development'),
            ('design', 'Design'),
        ]),
        ('Support', [
            ('sales', 'Sales'),
            ('marketing', 'Marketing')
        ])
    )

    department = MultiSelectField(
        choices=DEPARTMENT_CHOICES,
        default='it,sales',
    )


class TestTagsField(models.Model):
    class Meta:
        verbose_name        = 'Test Tags Field'
        verbose_name_plural = 'Test Tags Fields'

    class Listing:
        filter_by = ['tags']


    TAG_CHOICES = (
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
    )

    tags = TagsField(
        max_length=255,
        choices=TAG_CHOICES,
        default='#a#b#',
    )


    @classmethod
    def get_form(cls):
        from cubane.testapp.forms import TestTagsFieldForm
        return TestTagsFieldForm


class TestNullableTagsField(models.Model):
    class Meta:
        verbose_name        = 'Test Nullable Tags Field'
        verbose_name_plural = 'Test Nullable Tags Fields'


    TAG_CHOICES = (
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
    )

    tags = TagsField(
        max_length=255,
        choices=TAG_CHOICES,
        null=True,
        blank=True
    )


class TestTagsOptGroupField(models.Model):
    class Meta:
        verbose_name        = 'Test Tags OptGroup Field'
        verbose_name_plural = 'Test Tags OptGroup Fields'


    TAG_CHOICES = (
        ('Foo', [
            ('a', 'A'),
            ('b', 'B'),
        ]),
        ('Bar', [
            ('c', 'C')
        ])
    )

    tags = TagsField(
        max_length=255,
        choices=TAG_CHOICES,
        default='#a#b#',
    )


class TestTreeNode(models.Model):
    class Meta:
        verbose_name        = 'Test Tree Node'
        verbose_name_plural = 'Test Tree Nodes'

    title = models.CharField(
        max_length=255,
    )

    parent = models.ForeignKey('self', null=True, blank=True)
    seq = models.IntegerField(default=1, db_index=True)


    def __unicode__(self): # pragma: no cover
        return self.title


class TestPageWithMedia(models.Model):
    title = models.CharField(max_length=255)
    media = models.ManyToManyField(Media, through='TestPageMedia')

    def __unicode__(self): # pragma: no cover
        return '%s' % self.title


class TestPageMedia(models.Model):
    from_page = models.ForeignKey(
        TestPageWithMedia,
        related_name='+',
    )

    to_media = models.ForeignKey(
        Media,
        related_name='+',
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
    )


    def __unicode__(self): # pragma: no cover
        return unicode(self.to_media_id)


class TestModelNotNullableWithoutDefault(models.Model):
    title = models.CharField(max_length=255)


class TestModelNotNullableWithDefault(models.Model):
    title = models.CharField(max_length=255, default='default')


class TestDateTimeReadOnlyBase(DateTimeReadOnlyBase):
    pass


class TestNotNullableForeignKey(DateTimeBase):
    image = models.ForeignKey(
        Media,
    )


class TestNullableForeignKeyCascaded(DateTimeBase):
    parent = models.ForeignKey(
        TestNotNullableForeignKey,
        null=True,
        blank=True
    )