from django.conf import settings
from cubane.tests.base import CubaneTestCase
from cubane.models import Country
from cubane.media.models import Media
from cubane.testapp.models import (
    TestDateTimeReadOnlyBase,
    TestModel,
    TestNotNullableForeignKey,
    TestNullableForeignKeyCascaded
)
from freezegun import freeze_time
from datetime import datetime
from mock import patch


# include other tests covering sub-components of this module
from cubane.models.tests.mixin import *
from cubane.models.tests.fields import *
from cubane.models.tests.data import *


class ModelsTestCaseBase(CubaneTestCase):
    TIMESTAMP     = datetime(2016, 10, 26, 0, 0)
    TIMESTAMP_STR = '2016-10-26'

    LATER_TIMESTAMP     = datetime(2016, 10, 27, 0, 0)
    LATER_TIMESTAMP_STR = '2016-10-27'


class ModelsDateTimeReadOnlyBaseSaveTestCase(ModelsTestCaseBase):
    """
    cubane.models.DateTimeReadOnlyBase.save()
    """
    def test_save_should_update_created_on_timestamp(self):
        freezer = freeze_time(self.TIMESTAMP_STR)
        freezer.start()
        x = TestDateTimeReadOnlyBase.objects.create()
        freezer.stop()

        self.assertEqual(self.TIMESTAMP, x.created_on)

        # saving again should not change timestamp
        x.save()
        self.assertEqual(self.TIMESTAMP, x.created_on)


class DateTimeBaseGetChecksumTestCase(ModelsTestCaseBase):
    """
    cubane.models.DateTimeBase.get_checksum()
    """
    def test_get_checksum_should_return_checksum_over_model_instance_fields(self):
        x = TestModel()
        self.assertEqual(
            '866e701a01787d8a3323568493600eebf65a3d49',
            x.get_checksum()
        )


class DateTimeBaseSaveTestCase(ModelsTestCaseBase):
    """
    cubane.models.DateTimeBase.save()
    """
    def test_save_should_update_created_on_timestamp(self):
        freezer = freeze_time(self.TIMESTAMP_STR)
        freezer.start()
        x = TestModel.objects.create()
        freezer.stop()

        self.assertEqual(self.TIMESTAMP, x.created_on)

        # saving again should not change timestamp
        x.save()
        self.assertEqual(self.TIMESTAMP, x.created_on)


    def test_save_should_always_update_updated_on_field(self):
        freezer = freeze_time(self.TIMESTAMP_STR)
        freezer.start()
        x = TestModel.objects.create()
        freezer.stop()

        self.assertEqual(self.TIMESTAMP, x.updated_on)

        freezer = freeze_time(self.LATER_TIMESTAMP_STR)
        freezer.start()
        x.save()
        freezer.stop()

        self.assertEqual(self.LATER_TIMESTAMP, x.updated_on)


class DateTimeBaseDeleteTestCase(ModelsTestCaseBase):
    """
    cubane.models.DateTimeBase.delete()
    """
    @patch('cubane.testapp.models.TestModel.clear_nullable_related')
    def test_should_clear_nullable_related_on_delete(self, clear_nullable_related):
        x = TestModel.objects.create()
        x.delete()
        clear_nullable_related.assert_called_with()


class DateTimeBaseClearNullableRelatedTestCase(ModelsTestCaseBase):
    """
    cubane.models.DateTimeBase.clear_nullable_related()
    """
    def test_should_set_related_instance_to_null(self):
        image = Media.objects.create(caption='foo')
        x = TestModel.objects.create(title='bar', image=image)
        try:
            image.delete()
            x = TestModel.objects.get(title='bar')
            self.assertIsNone(x.image)
        finally:
            [x.delete() for x in Media.objects.filter(caption='foo')]
            [x.delete() for x in TestModel.objects.filter(title='bar')]


    def test_cannot_cascade_set_null_if_field_is_not_nullable(self):
        image = Media.objects.create(caption='foo')
        x = TestNotNullableForeignKey.objects.create(image=image)
        try:
            image.delete()
            with self.assertRaisesRegexp(TestNotNullableForeignKey.DoesNotExist, 'matching query does not exist'):
                x = TestNotNullableForeignKey.objects.get(pk=x.pk)
        finally:
            [x.delete() for x in Media.objects.filter(caption='foo')]
            [x.delete() for x in TestNotNullableForeignKey.objects.all()]


    def test_should_clear_nullable_related_recursivly(self):
        image = Media.objects.create(caption='foo')
        y = TestNotNullableForeignKey.objects.create(image=image)
        x = TestNullableForeignKeyCascaded.objects.create(parent=y)
        try:
            # since y depends on image and the relationship is not nullable,
            # this will implicitly delete y, but the relationship between x and
            # y is nullable, which should be set to null prior of
            # deleting y and image.
            image.delete()

            # image gone
            self.assertEqual(0, Media.objects.filter(caption='foo').count())

            # y gone
            self.assertEqual(0, TestNotNullableForeignKey.objects.count())

            # x still there
            self.assertEqual(1, TestNullableForeignKeyCascaded.objects.count())
        finally:
            [x.delete() for x in Media.objects.filter(caption='foo')]
            [x.delete() for x in TestNotNullableForeignKey.objects.all()]
            [x.delete() for x in TestNullableForeignKeyCascaded.objects.all()]


class CountryToDictTestCase(ModelsTestCaseBase):
    """
    cubane.models.Country.to_dict()
    """
    def test_should_return_dict_representation(self):
        self.assertEqual({
            'iso': 'GB',
            'iso3': 'GBR',
            'numcode': 826,
            'printable_name': 'United Kingdom',
            'name': 'UNITED KINGDOM'
        }, Country.objects.get(iso='GB').to_dict())