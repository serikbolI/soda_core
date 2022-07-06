from soda.execution.schema_check import SchemaCheck
from tests.helpers.common_test_tables import customers_test_table
from tests.helpers.data_source_fixture import DataSourceFixture
from tests.helpers.utils import format_checks


def test_required_columns_indexes_pass(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()

    checks_str = format_checks(
        [("id", "0"), ("sizeTxt", "2"), ("distance", "3")],
        indent=15,
        data_source=data_source_fixture.data_source,
    )
    scan.add_sodacl_yaml_str(
        f"""
      checks for {table_name}:
        - schema:
            fail:
              when wrong column index:
{checks_str}
    """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_required_columns_indexes_fail(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)
    default_casify_column_name = data_source_fixture.data_source.default_casify_column_name
    checks_str = format_checks(
        [("id", "6"), ("sizeTxt", "3"), ("distance", "4")],
        indent=15,
        data_source=data_source_fixture.data_source,
    )

    scan = data_source_fixture.create_test_scan()
    scan.add_sodacl_yaml_str(
        f"""
      checks for {table_name}:
        - schema:
            fail:
              when wrong column index:
{checks_str}
    """
    )
    scan.execute()

    scan.assert_all_checks_fail()
    check: SchemaCheck = scan._checks[0]
    assert check.schema_column_index_mismatches == {
        default_casify_column_name("distance"): {
            "actual_index": 3,
            "column_on_expected_index": default_casify_column_name("pct"),
            "expected_index": 4,
        },
        default_casify_column_name("id"): {
            "actual_index": 0,
            "column_on_expected_index": default_casify_column_name("country"),
            "expected_index": 6,
        },
        default_casify_column_name("sizeTxt"): {
            "actual_index": 2,
            "column_on_expected_index": default_casify_column_name("distance"),
            "expected_index": 3,
        },
    }


def test_required_columns_indexes_warn(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)
    default_casify_column_name = data_source_fixture.data_source.default_casify_column_name
    checks_str = format_checks(
        [("id", "6"), ("sizeTxt", "3"), ("distance", "4")],
        indent=15,
        data_source=data_source_fixture.data_source,
    )

    scan = data_source_fixture.create_test_scan()
    scan.add_sodacl_yaml_str(
        f"""
      checks for {table_name}:
        - schema:
            warn:
              when wrong column index:
{checks_str}
    """
    )
    scan.execute()

    scan.assert_all_checks_warn()
    check: SchemaCheck = scan._checks[0]
    assert check.schema_column_index_mismatches == {
        default_casify_column_name("distance"): {
            "actual_index": 3,
            "column_on_expected_index": default_casify_column_name("pct"),
            "expected_index": 4,
        },
        default_casify_column_name("id"): {
            "actual_index": 0,
            "column_on_expected_index": default_casify_column_name("country"),
            "expected_index": 6,
        },
        default_casify_column_name("sizeTxt"): {
            "actual_index": 2,
            "column_on_expected_index": default_casify_column_name("distance"),
            "expected_index": 3,
        },
    }
