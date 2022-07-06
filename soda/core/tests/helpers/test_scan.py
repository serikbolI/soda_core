from __future__ import annotations

import logging
import os
import textwrap
from textwrap import dedent

from soda.common.log import LogLevel
from soda.execution.check import Check
from soda.execution.check_outcome import CheckOutcome
from soda.execution.data_source import DataSource
from soda.sampler.log_sampler import LogSampler
from soda.scan import Scan
from tests.helpers.mock_sampler import MockSampler
from tests.helpers.mock_soda_cloud import MockSodaCloud, TimeGenerator

logger = logging.getLogger(__name__)


class TestScan(Scan):

    __test__ = False

    # The main data_source (and the main data_source connection) is reused throughout the whole
    # test suite execution. (See @pytest.fixture(scope="session") below in the fixture)
    def __init__(self, data_source: DataSource | None = None):
        super().__init__()

        self.check_index = 0

        test_name = os.environ.get("PYTEST_CURRENT_TEST")
        if test_name:
            scan_definition_name = test_name[test_name.rfind("/") + 1 : -7]
        else:
            scan_definition_name = "test-scan-definition"

        self.set_scan_definition_name(scan_definition_name)

        self._configuration.sampler = LogSampler()
        self.set_verbose()

        if data_source:
            self.set_data_source_name(data_source.data_source_name)
            self._data_source_manager.data_sources[data_source.data_source_name] = data_source
            self._data_source_manager.data_source_properties_by_name[data_source.data_source_name] = {}

        if os.environ.get("WESTMALLE"):
            from tests.helpers.mock_soda_cloud import MockSodaCloud

            self._configuration.soda_cloud = MockSodaCloud(self)

    def _parse_sodacl_yaml_str(self, sodacl_yaml_str: str, file_path: str = None):
        dedented_sodacl_yaml_str = dedent(sodacl_yaml_str).strip()
        checks_yaml_log_str = dedented_sodacl_yaml_str
        checks_yaml_log_str = textwrap.indent(
            text=checks_yaml_log_str,
            prefix="  # ",
            predicate=lambda line: True,
        )
        self._logs.info(f"Adding {file_path} with YAML:")
        self._logs.debug(checks_yaml_log_str)
        super()._parse_sodacl_yaml_str(sodacl_yaml_str=sodacl_yaml_str, file_path=file_path)

    def mock_historic_values(self, metric_identity: str, metric_values: list, time_generator=TimeGenerator()):
        """
        To learn the metric_identity: fill in any string, check the error log and capture the metric_identity from there
        """
        self.enable_mock_soda_cloud()

        self._configuration.soda_cloud.mock_historic_values(metric_identity, metric_values, time_generator)

    def enable_mock_soda_cloud(self) -> MockSodaCloud:
        if not isinstance(self._configuration.soda_cloud, MockSodaCloud):
            self._configuration.soda_cloud = MockSodaCloud(self)
        return self._configuration.soda_cloud

    def enable_mock_sampler(self) -> MockSampler:
        if not isinstance(self._configuration.sampler, MockSampler):
            self._configuration.sampler = MockSampler()
        return self._configuration.sampler

    def execute(self, allow_error_warning: bool = False, allow_warnings_only: bool = False):
        super().execute()

        if not allow_error_warning:
            if not allow_warnings_only:
                self.assert_no_error_nor_warning_logs()
            else:
                self.assert_no_error_logs()
        if allow_warnings_only:
            self.assert_no_error_logs()

    def execute_unchecked(self):
        super().execute()

    def _close(self):
        # Because we want to recycle the main data_source connection, we cannot finish the scan and hence
        # we must manually close all connections except the one in self.data_source
        datasource_name = self._data_source_name
        data_source = self._data_source_manager.data_sources[datasource_name]
        reused_data_source_connection = data_source.connection

        for (
            connection_name,
            connection,
        ) in self._data_source_manager.connections.items():
            if connection is not reused_data_source_connection:
                try:
                    connection.close()
                except BaseException as e:
                    self._logs.error(f"Could not close connection {connection_name}: {e}", exception=e)

    def assert_log_warning(self, message):
        self.assert_log(message, LogLevel.WARNING)

    def assert_log_error(self, message):
        self.assert_log(message, LogLevel.ERROR)

    def assert_log(self, message, level: LogLevel):
        if not any([log.level == level and message in log.message for log in self._logs.logs]):
            raise AssertionError(f"{level.name} not found: {message}")

    def assert_all_checks_pass(self):
        self.assert_all_checks(CheckOutcome.PASS)

    def assert_all_checks_fail(self):
        self.assert_all_checks(CheckOutcome.FAIL)

    def assert_all_checks_warn(self):
        self.assert_all_checks(CheckOutcome.WARN)

    def assert_all_checks(self, expected_outcome):
        if len(self._checks) == 0:
            raise AssertionError("Expected at least 1 check result")
        error_messages = []
        for i in range(0, len(self._checks)):
            error_message = self.__get_error_message(expected_outcome)
            if error_message:
                error_messages.append(error_message)
        if error_messages:
            raise AssertionError("\n\n" + ("\n".join(error_messages)))

    def assert_check_pass(self):
        self.assert_check(CheckOutcome.PASS)

    def assert_check_fail(self):
        self.assert_check(CheckOutcome.FAIL)

    def assert_check_warn(self):
        self.assert_check(CheckOutcome.WARN)

    def assert_check(self, expected_outcome):
        error_message = self.__get_error_message(expected_outcome)
        if error_message:
            raise AssertionError(error_message)

    def __get_error_message(self, expected_outcome) -> str | None:
        """
        Returns None if the next check result has the expected_outcome, otherwise an assertion error message.
        """
        error_message = None

        if len(self._checks) <= self.check_index:
            raise AssertionError(f"No more check results. {len(self._checks)} check results in total")
        check: Check = self._checks[self.check_index]

        log_diagnostic_lines = check.get_log_diagnostic_lines()
        diagnostic_text = "\n".join([f"  {line}" for line in log_diagnostic_lines])

        if check.outcome != expected_outcome:
            error_message = (
                f"Check[{self.check_index}]: {check.check_cfg.source_line} \n"
                f"  Expected {expected_outcome.value}, but was {check.outcome} \n"
                # f'  Expected {expected_outcome}, but was {check.outcome} \n'
                f"{diagnostic_text}"
            )

        self.check_index += 1

        return error_message

    # class Scanner:
    #     def __init__(self, data_source: DataSource):
    #         self.data_source = data_source
    #         self.test_table_manager = data_source.create_test_table_manager()
    #         self.test_table_manager._initialize_schema()
    #
    #     def drop_schema(self):
    #         # create_schema is done directly from the TestTableManager constructor
    #         self.test_table_manager._drop_schema_if_exists()
    #
    #     def ensure_test_table(self, test_table: TestTable) -> str:
    #         return self.test_table_manager.ensure_test_table(test_table)
    #
    #     def create_test_scan(self) -> TestScan:
    #         return TestScan(data_source=self.data_source)
    #
    #     def execute_query(self, sql):
    #         data_source = self.data_source
    #         cursor = data_source.connection.cursor()
    #         try:
    #             indented_sql = textwrap.indent(text=sql, prefix="  #   ")
    #             logging.debug(f"  # Query: \n{indented_sql}")
    #             cursor.execute(sql)
    #             return cursor.fetchone()
    #         finally:
    #             cursor.close()

    def casify_data_type(self, data_type: str) -> str:
        data_source_type = self.data_source.get_sql_type_for_schema_check(data_type)
        return self.data_source.default_casify_column_name(data_source_type)

    def casify_column_name(self, test_column_name: str) -> str:
        return self.data_source.default_casify_column_name(test_column_name)
