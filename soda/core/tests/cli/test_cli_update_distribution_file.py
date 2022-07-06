from textwrap import dedent

import pytest
from tests.cli.run_cli import run_cli
from tests.helpers.common_test_tables import customers_test_table
from tests.helpers.data_source_fixture import DataSourceFixture
from tests.helpers.fixtures import test_data_source
from tests.helpers.mock_file_system import MockFileSystem


@pytest.mark.skipif(
    test_data_source != "postgres",
    reason="Run for postgres only as nothing data source specific is tested.",
)
def test_cli_update_distribution_file(data_source_fixture: DataSourceFixture, mock_file_system: MockFileSystem):
    table_name = data_source_fixture.ensure_test_table(customers_test_table)

    user_home_dir = mock_file_system.user_home_dir()

    mock_file_system.files = {
        f"{user_home_dir}/configuration.yml": data_source_fixture.create_test_configuration_yaml_str(),
        f"{user_home_dir}/customers_distribution_reference.yml": dedent(
            f"""
                table: {table_name}
                column: size
                method: continuous
            """
        ),
    }

    run_cli(
        [
            "update-dro",
            "-c",
            "configuration.yml",
            "-d",
            data_source_fixture.data_source.data_source_name,
            f"{user_home_dir}/customers_distribution_reference.yml",
        ]
    )

    print(mock_file_system.files[f"{user_home_dir}/customers_distribution_reference.yml"])
