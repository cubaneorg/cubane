# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth.models import User
from cubane.tests.base import CubaneTestCase
from cubane.models.data import Exporter, Importer
from cubane.testapp.models import TestModelImportExport, TestModelImportNumericZero
from cubane.testapp.forms import TestModelImportExportForm, TestModelImportNumericZeroForm
import cStringIO


@CubaneTestCase.complex()
class CubaneModelsDataTestCaseBase(CubaneTestCase):
    CSV_DATA = (
        '"id","title","enabled","enabled_display","address_type","is_company"\r\n' +
        '"1","Test 1","False","no","1","True"\r\n' +
        '"2","Test 2","True","yes","1","True"\r\n' +
        '"3","Test 3","True","yes","2","False"\r\n' +
        '"4","","False","no","2","False"\r\n' +
        '"5",",Test ""5""","False","no","1","True"\r\n'
    )


    CSV_DATA_ALL_COLUMNS = (
        '"id","created_on","created_by","updated_on","updated_by","deleted_on","deleted_by","seq","title","enabled","address_type","email","user"\r\n' +
        '"1","","","","","","","0","Test 1","False","1","",""\r\n' +
        '"2","","","","","","","0","Test 2","True","1","",""\r\n' +
        '"3","","","","","","","0","Test 3","True","2","",""\r\n' +
        '"4","","","","","","","0","","False","2","",""\r\n' +
        '"5","","","","","","","0",",Test ""5""","False","1","",""\r\n'
    )


    def setUp(self):
        self.reset_db_seq([User, TestModelImportExport])
        self.data_columns = None
        self.user = self._create_user('admin')
        self.exporter = Exporter(TestModelImportExport)
        self.importer = Importer(
            TestModelImportExport,
            TestModelImportExportForm,
            TestModelImportExport.objects.all(),
            self.user
        )
        self.assertEqual(1, User.objects.count())
        self.assertEqual(0, TestModelImportExport.objects.count())


    def tearDown(self):
        [m.delete() for m in TestModelImportExport.objects.all()]
        [u.delete() for u in User.objects.all()]
        self.assertEqual(0, User.objects.count())
        self.assertEqual(0, TestModelImportExport.objects.count())


    def _create_request(self):
        factory = RequestFactory()
        request = factory.get('/')
        setattr(request, 'session', 'session')
        setattr(request, '_messages', FallbackStorage(request))
        return request


    def _create_stream(self, data):
        stream = cStringIO.StringIO()
        stream.write(chr(0xEF))
        stream.write(chr(0xBB))
        stream.write(chr(0xBF))
        stream.write(data.encode('utf-8'))
        stream.seek(0)
        return stream


    def _create_user(self, username):
        u = User(username=username)
        u.set_password('password')
        u.save()
        return u


    def _assertCSV(self, csv):
        if self.data_columns:
            TestModelImportExport.Listing.data_columns = self.data_columns

        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(TestModelImportExport.objects.all(), stream)

        if self.data_columns:
            delattr(TestModelImportExport.Listing, 'data_columns')

        self._assertCSVDiff(csv, stream.getvalue()[3:].decode('utf-8'))


    def _assertCSVDiff(self, csv, exported_csv):
        """
        if exported_csv.startswith('\uefbbbf'):
            exported_csv = exported_csv[1:]

        diff = '\n'.join([
            '%-3s %-60s | %-60s' % (
                '' if left == right else '=>',
                left,
                right
            ) for left, right in zip(csv.split('\r\n'), exported_csv.split('\r\n'))
        ])
        """

        self.assertEqual(csv, exported_csv)


    def _assert_no_form_errors(self, request):
        self.assertEqual(0, len(request._messages._queued_messages))


    def _assert_form_error(self, request, msg):
        for m in request._messages._queued_messages:
            if m.message == msg:
                return
        self.assertTrue(False, 'Expected form message not found: %s. Available messages: %s' % (msg, ', '.join([m.message for m in request._messages._queued_messages])))


    def _assert_import(self, request, import_csv, expected_csv):
        stream = self._create_stream(import_csv)
        self.importer.import_from_stream(request, stream)
        self._assertCSV(expected_csv)


    def _get_objects(self):
        return [
            TestModelImportExport(id=1, title='Test 1',    enabled=False, address_type=TestModelImportExport.ADDRESS_TYPE_BUSINESS),
            TestModelImportExport(id=2, title='Test 2',    enabled=True,  address_type=TestModelImportExport.ADDRESS_TYPE_BUSINESS),
            TestModelImportExport(id=3, title='Test 3',    enabled=True,  address_type=TestModelImportExport.ADDRESS_TYPE_HOME),
            TestModelImportExport(id=4, title=None,        enabled=False, address_type=TestModelImportExport.ADDRESS_TYPE_HOME),
            TestModelImportExport(id=5, title=',Test "5"', enabled=False, address_type=TestModelImportExport.ADDRESS_TYPE_BUSINESS)
        ]


@CubaneTestCase.complex()
class ModelsDataImporterTestCase(CubaneModelsDataTestCaseBase):
    def test_import_from_stream_should_import_csv_data(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA, self.CSV_DATA)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterDefaultDataColumnsTestCase(CubaneModelsDataTestCaseBase):
    def setUp(self):
        super(ModelsDataImporterDefaultDataColumnsTestCase, self).setUp()
        self.data_columns = TestModelImportExport.Listing.data_columns
        delattr(TestModelImportExport.Listing, 'data_columns')


    def tearDown(self):
        super(ModelsDataImporterDefaultDataColumnsTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.data_columns


    def test_import_from_stream_should_import_csv_data_based_on_default_data_columns(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA, self.CSV_DATA)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataExporterTestCase(CubaneModelsDataTestCaseBase):
    def test_csv_export(self):
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(self._get_objects(), stream)
        self.assertEqual(self.CSV_DATA, stream.getvalue()[3:].decode('utf-8'))


    def test_export_to_response(self):
        r = self.exporter.export_to_response(self._get_objects(), 'data.csv')
        self.assertEqual('text/csv', r['Content-Type'] )
        self.assertEqual(self.CSV_DATA, r.content[3:].decode('utf-8'))


@CubaneTestCase.complex()
class ModelsDataExporterRenameColumnsTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_RENAMED_COLUMNS = (
        '"id","name"\r\n' +
        '"1","Test 1"\r\n' +
        '"2","Test 2"\r\n' +
        '"3","Test 3"\r\n' +
        '"4",""\r\n' +
        '"5",",Test ""5""' + '"\r\n'
    )


    def setUp(self):
        super(ModelsDataExporterRenameColumnsTestCase, self).setUp()
        self.data_columns = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title:as(name)'
        ]


    def tearDown(self):
        super(ModelsDataExporterRenameColumnsTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.data_columns


    def test_csv_export_renaming_columns(self):
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(self._get_objects(), stream)
        self.assertEqual(self.CSV_DATA_RENAMED_COLUMNS, stream.getvalue()[3:].decode('utf-8'))


@CubaneTestCase.complex()
class ModelsDataExporterDefaultDataColumnsTestCase(CubaneModelsDataTestCaseBase):
    def setUp(self):
        super(ModelsDataExporterDefaultDataColumnsTestCase, self).setUp()
        self.data_columns = TestModelImportExport.Listing.data_columns
        delattr(TestModelImportExport.Listing, 'data_columns')


    def tearDown(self):
        super(ModelsDataExporterDefaultDataColumnsTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.data_columns


    def test_csv_export_with_default_data_columns(self):
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(self._get_objects(), stream)
        self.assertEqual(self.CSV_DATA_ALL_COLUMNS, stream.getvalue()[3:].decode('utf-8'))


@CubaneTestCase.complex()
class ModelsDataExporterIgnoreColumnsTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_EXCLUDING_COLUMNS = (
        '"id","title"\r\n' +
        '"1","Test 1"\r\n' +
        '"2","Test 2"\r\n' +
        '"3","Test 3"\r\n' +
        '"4",""\r\n' +
        '"5",",Test ""5""' + '"\r\n'
    )


    def setUp(self):
        super(ModelsDataExporterIgnoreColumnsTestCase, self).setUp()
        TestModelImportExport.Listing.data_ignore = [
            'enabled',
            'enabled_display',
            'address_type',
            'is_company'
        ]


    def tearDown(self):
        super(ModelsDataExporterIgnoreColumnsTestCase, self).tearDown()
        delattr(TestModelImportExport.Listing, 'data_ignore')


    def test_csv_export_should_ignore_columns(self):
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(self._get_objects(), stream)
        self.assertEqual(self.CSV_DATA_EXCLUDING_COLUMNS, stream.getvalue()[3:].decode('utf-8'))


@CubaneTestCase.complex()
class ModelsDataImporterMapFieldsTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_MAP_FIELDS = (
        '"id","name","active","active_dsp","address_type","is_company"\r\n' +
        '"1","Test 1","False","no","1","True"\r\n' +
        '"2","Test 2","True","yes","1","True"\r\n' +
        '"3","Test 3","True","yes","2","False"\r\n' +
        '"4","","False","no","2","False"\r\n' +
        '"5",",Test ""5""","False","no","1","True"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterMapFieldsTestCase, self).setUp()
        TestModelImportExport.Listing.data_map_fields = {
            'name': 'title',
            'active': 'enabled',
            'active_dsp': 'enabled_display'
        }


    def tearDown(self):
        super(ModelsDataImporterMapFieldsTestCase, self).tearDown()
        delattr(TestModelImportExport.Listing, 'data_map_fields')


    def test_importer_should_map_column_names(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_MAP_FIELDS, self.CSV_DATA)
        self._assert_form_error(request, 'Header field \'active_dsp\' in the CSV file does not exist in database. Ignoring field.')


@CubaneTestCase.complex()
class ModelsDataImporterDefaultValueTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_MISSING_FIELDS = (
        '"id","title","enabled","enabled_display","address_type","is_company"\r\n' +
        '"1",,"False","no","1","True"\r\n' +
        '"2",,"True","yes","1","True"\r\n' +
        '"3","Test 3","True","yes","2","False"\r\n' +
        '"4","","False","no","2","False"\r\n' +
        '"5",",Test ""5""","False","no","1","True"\r\n'
    )

    EXPECTED_CSV_DATA_MISSING_FIELDS = (
        '"id","title","enabled","enabled_display","address_type","is_company"\r\n' +
        '"1","no","False","no","1","True"\r\n' +
        '"2","yes","True","yes","1","True"\r\n' +
        '"3","Test 3","True","yes","2","False"\r\n' +
        '"4","no","False","no","2","False"\r\n' +
        '"5",",Test ""5""","False","no","1","True"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterDefaultValueTestCase, self).setUp()
        TestModelImportExport.Listing.data_default_values = {
            'title': 'enabled_display'
        }


    def tearDown(self):
        super(ModelsDataImporterDefaultValueTestCase, self).tearDown()
        delattr(TestModelImportExport.Listing, 'data_default_values')


    def test_importer_should_take_default_from_other_column(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_MISSING_FIELDS, self.EXPECTED_CSV_DATA_MISSING_FIELDS)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterRespectNumericZeroTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA = (
        '"id","number"\r\n' +
        '"1","0"\r\n'
    )

    EXPECTED_CSV_DATA = (
        '"id","number"\r\n' +
        '"1","0"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterRespectNumericZeroTestCase, self).setUp()
        self.reset_db_seq([TestModelImportNumericZero])
        self.exporter = Exporter(TestModelImportNumericZero)
        self.importer = Importer(
            TestModelImportNumericZero,
            TestModelImportNumericZeroForm,
            TestModelImportNumericZero.objects.all(),
            self.user
        )


    def tearDown(self):
        super(ModelsDataImporterRespectNumericZeroTestCase, self).tearDown()
        [x.delete() for x in TestModelImportNumericZero.objects.all()]
        self.assertEqual(0, TestModelImportNumericZero.objects.count())


    def _assertCSV(self, csv):
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(TestModelImportNumericZero.objects.all(), stream)
        self._assertCSVDiff(csv, stream.getvalue()[3:].decode('utf-8'))


    def test_importer_should_respect_numeric_zero_as_data_value(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA, self.EXPECTED_CSV_DATA)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterUnnamedColumnsTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_UNNAMED_COLUMN = (
        '"id","title","enabled","address_type",""\r\n' +
        '"1","Test 1","False","1","True",""\r\n' +
        '"2","Test 2","True","2","False",""\r\n'
    )

    EXPECTED_CSV_DATA_UNNAMED_COLUMN = (
        '"id","title","enabled","enabled_display","address_type","is_company"\r\n' +
        '"1","Test 1","False","no","1","True"\r\n' +
        '"2","Test 2","True","yes","2","False"\r\n'
    )


    def test_importer_should_ignore_unnamed_columns(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_UNNAMED_COLUMN, self.EXPECTED_CSV_DATA_UNNAMED_COLUMN)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterEditCaseTestCase(CubaneModelsDataTestCaseBase):
    def test_importer_should_update_existing_records(self):
        t = TestModelImportExport(
            id=1, title='Test 1 - Already Exists',
            enabled=False, address_type=TestModelImportExport.ADDRESS_TYPE_BUSINESS
        )
        t.save()

        request = self._create_request()
        self._assert_import(request, self.CSV_DATA, self.CSV_DATA)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataCustomPKTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_CUSTOM_PK = (
        '"id","title","enabled","address_type",""\r\n' +
        '"1","Test 1","False","1","True",""\r\n' +
        '"2","Test 2","True","2","False",""\r\n'
    )

    EXPECTED_CSV_DATA_CUSTOM_PK = (
        '"title","enabled","address_type"\r\n' +
        '"Test 1","False","1"\r\n' +
        '"Test 2","True","2"\r\n'
    )

    EXPECTED_CSV_DATA_CUSTOM_PK_NOT_PRESENT = (
        '"title","created_on","created_by","updated_on","updated_by","deleted_on","deleted_by","seq","enabled","address_type","email","user"\r\n' +
        '"Test 1","","","","","","","0","False","1","",""\r\n' +
        '"Test 2","","","","","","","0","True","1","",""\r\n' +
        '"Test 3","","","","","","","0","True","2","",""\r\n' +
        '"","","","","","","","0","False","2","",""\r\n' +
        '",Test ""5""","","","","","","","0","False","1","",""\r\n'
    )


    def setUp(self):
        super(ModelsDataCustomPKTestCase, self).setUp()
        TestModelImportExport.Listing.data_id_field = 'title'
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'title',
            'enabled',
            'address_type'
        ]


    def tearDown(self):
        super(ModelsDataCustomPKTestCase, self).tearDown()
        delattr(TestModelImportExport.Listing, 'data_id_field')
        TestModelImportExport.Listing.data_columns = self.cols


    def test_exporter_should_not_export_default_pk_because_custom_pk_is_present(self):
        # force exporter to use all fields, which should then
        # exclude primary key, since we defined a custom one...
        delattr(TestModelImportExport.Listing, 'data_columns')

        # export
        stream = cStringIO.StringIO()
        self.exporter.export_to_stream(self._get_objects(), stream)
        self.assertEqual(self.EXPECTED_CSV_DATA_CUSTOM_PK_NOT_PRESENT, stream.getvalue()[3:].decode('utf-8'))


    def test_importer_should_correlate_records_by_using_specified_column(self):
        t = TestModelImportExport(
            id=3,
            title='Test 1', # pk (id) does not match, but title does
            enabled=True,
            address_type=TestModelImportExport.ADDRESS_TYPE_HOME
        )
        t.save()

        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_CUSTOM_PK, self.EXPECTED_CSV_DATA_CUSTOM_PK)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterAcceptFormattedEmailsTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_EMAIL = (
        '"id","title","enabled","address_type","email"\r\n' +
        '"1","Test 1","False","1","jan.kueting@innershed.com"\r\n' +
        '"2","Test 2","True","2","Jan Kueting <jan.kueting@innershed.com>"\r\n'
    )

    EXPECTED_CSV_DATA_EMAIL = (
        '"id","title","enabled","enabled_display","address_type","is_company","email"\r\n' +
        '"1","Test 1","False","no","1","True","jan.kueting@innershed.com"\r\n' +
        '"2","Test 2","True","yes","2","False","jan.kueting@innershed.com"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterAcceptFormattedEmailsTestCase, self).setUp()
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title',
            'enabled',
            'enabled_display',
            'address_type',
            'is_company',
            'email'
        ]


    def tearDown(self):
        super(ModelsDataImporterAcceptFormattedEmailsTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.cols


    def test_importer_should_read_formatted_email_addresses(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_EMAIL, self.EXPECTED_CSV_DATA_EMAIL)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterForeignKeyTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_FOREIGN_KEY = (
        '"id","title","enabled","address_type","user"\r\n' +
        '"1","Test 1","False","1","admin"\r\n' +
        '"2","Test 2","True","2",""\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterForeignKeyTestCase, self).setUp()
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title',
            'enabled',
            'address_type',
            'user'
        ]


    def tearDown(self):
        super(ModelsDataImporterForeignKeyTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.cols


    def test_importer_should_process_foreign_keys(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_FOREIGN_KEY, self.CSV_DATA_FOREIGN_KEY)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterChoicesConverterFunctionTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_CHOICES = (
        '"id","title","enabled","address_type"\r\n' +
        '"1","Test 1","False","business"\r\n' +
        '"2","Test 2","True","home"\r\n'
    )


    EXPECTED_CSV_DATA_CHOICES = (
        '"id","title","enabled","address_type"\r\n' +
        '"1","Test 1","False","1"\r\n' +
        '"2","Test 2","True","2"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterChoicesConverterFunctionTestCase, self).setUp()
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title',
            'enabled',
            'address_type',
        ]
        def import_address_type(cls, v):
            return 1 if v == 'business' else 2
        TestModelImportExport.import_address_type = classmethod(import_address_type)


    def tearDown(self):
        super(ModelsDataImporterChoicesConverterFunctionTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.cols
        delattr(TestModelImportExport, 'import_address_type')


    def test_importer_should_use_converter_function_for_choices_if_present(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_CHOICES, self.EXPECTED_CSV_DATA_CHOICES)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterSkipBlankLinesTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_BLANK_LINES = (
        '"id","title","enabled","address_type"\r\n' +
        '"1","Test 1","False","1"\r\n' +
        '"","","",""\r\n' +
        '\r\n' +
        '"2","Test 2","True","2"\r\n'
    )


    EXPECTED_CSV_DATA_BLANK_LINES = (
        '"id","title","enabled","address_type"\r\n' +
        '"1","Test 1","False","1"\r\n' +
        '"2","Test 2","True","2"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterSkipBlankLinesTestCase, self).setUp()
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title',
            'enabled',
            'address_type',
        ]


    def tearDown(self):
        super(ModelsDataImporterSkipBlankLinesTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.cols


    def test_importer_should_skip_blank_or_empty_lines(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_BLANK_LINES, self.EXPECTED_CSV_DATA_BLANK_LINES)
        self._assert_no_form_errors(request)


@CubaneTestCase.complex()
class ModelsDataImporterFieldDidNotValidateTestCase(CubaneModelsDataTestCaseBase):
    CSV_DATA_INVALID_DATA = (
        '"id","title","enabled","address_type"\r\n' +
        '"1","Test 1","False","foo"\r\n' +
        '"2","Test 2","True","2"\r\n'
    )


    EXPECTED_CSV_DATA_INVALID_DATA = (
        '"id","title","enabled","address_type"\r\n' +
        '"2","Test 2","True","2"\r\n'
    )


    def setUp(self):
        super(ModelsDataImporterFieldDidNotValidateTestCase, self).setUp()
        self.cols = TestModelImportExport.Listing.data_columns
        TestModelImportExport.Listing.data_columns = [
            'id',
            'title',
            'enabled',
            'address_type',
        ]


    def tearDown(self):
        super(ModelsDataImporterFieldDidNotValidateTestCase, self).tearDown()
        TestModelImportExport.Listing.data_columns = self.cols


    def test_importer_should_present_invalid_data_error_message(self):
        request = self._create_request()
        self._assert_import(request, self.CSV_DATA_INVALID_DATA, self.EXPECTED_CSV_DATA_INVALID_DATA)
        self._assert_form_error(request, 'Field <em>address_type</em> with the value <em>\'foo\'</em> did not validate: <ul class="errorlist"><li>Select a valid choice. foo is not one of the available choices.</li></ul>')