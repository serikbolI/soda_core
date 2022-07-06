from tests.helpers.common_test_tables import customers_test_table
from tests.helpers.data_source_fixture import DataSourceFixture


def test_freshness_without_table_filter(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables({"NOW": "2020-06-24 01:00:00"})
    scan.add_sodacl_yaml_str(
        f"""
          checks for {table_name}:
            - freshness(ts) < 1d
        """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_freshness_timezones_input_no_tz(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables({"NOW": "2020-06-25 00:00:00"})  # NOW overrides default "now" variable in scan.
    scan.add_sodacl_yaml_str(
        f"""
          checks for {table_name}:
            - freshness(ts) < 1d
            - freshness(ts_with_tz) < 1d
        """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_freshness_timezones_input_with_tz(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables({"NOW": "2020-06-25 01:00:00+01:00"})  # NOW overrides default "now" variable in scan.
    scan.add_sodacl_yaml_str(
        f"""
          checks for {table_name}:
            - freshness(ts) < 1d
            - freshness(ts_with_tz) < 1d
        """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_freshness_timezones_no_input(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    # Using silly values for the checks as runtime of running the test will be used for comparison.
    scan.add_sodacl_yaml_str(
        f"""
          checks for {table_name}:
            - freshness(ts) < 10000d
            - freshness(ts_with_tz) < 10000d
        """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_fail_freshness_timezones_input_user_var(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables({"CUSTOM_USER_VAR": "2020-06-25 02:00:00+01:00"})
    scan.add_sodacl_yaml_str(
        f"""
          checks for {table_name}:
            - freshness(ts, CUSTOM_USER_VAR) < 1d
            - freshness(ts_with_tz, CUSTOM_USER_VAR) < 1d
        """
    )
    scan.execute()

    scan.assert_all_checks_fail()


def test_freshness_warning(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables({"NOW": "2020-06-25 00:00:00"})  # NOW overrides default "now" variable in scan.
    scan.add_sodacl_yaml_str(
        f"""
      checks for {table_name}:
        - freshness(ts):
            warn: when > 6h
            fail: when > 24h
    """
    )
    scan.execute()

    scan.assert_check_warn()


def test_freshness_with_table_filter(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables(
        {
            "START_TIME": "2020-06-23 00:00:00",
            "END_TIME": "2020-06-24 00:00:00",
        }
    )
    scan.add_sodacl_yaml_str(
        f"""
          filter {table_name} [daily]:
            where: TIMESTAMP '${{START_TIME}}' <= ts AND ts < TIMESTAMP '${{END_TIME}}'

          checks for {table_name} [daily]:
            - freshness(ts, END_TIME) < 24h
        """
    )
    scan.execute()

    scan.assert_all_checks_pass()


def test_freshness_no_rows(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_variables(
        {
            "START_TIME": "2020-06-23 00:00:00",
            "END_TIME": "2020-06-24 00:00:00",
        }
    )
    scan.add_sodacl_yaml_str(
        f"""
          filter {table_name} [empty]:
            where: 'FALSE'

          checks for {table_name} [empty]:
            - freshness(ts, END_TIME) < 24h
        """
    )
    scan.execute()

    scan.assert_all_checks_fail()


def test_fail_freshness_var_missing(data_source_fixture: DataSourceFixture):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    scan = data_source_fixture.create_test_scan()
    scan.add_sodacl_yaml_str(
        f"""
      checks for {table_name}:
        - freshness(ts, CUSTOM_USER_VAR) < 1d
    """
    )
    scan.execute(allow_error_warning=True)

    scan.assert_all_checks_fail()
    scan.assert_log_error("variable not found")
