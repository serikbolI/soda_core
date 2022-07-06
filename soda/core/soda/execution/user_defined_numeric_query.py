from soda.execution.metric import Metric
from soda.execution.query import Query


class UserDefinedNumericQuery(Query):
    def __init__(
        self,
        data_source_scan: "DataSourceScan",
        check_name: str,
        sql: str,
        metric: Metric,
    ):
        super().__init__(
            data_source_scan=data_source_scan,
            unqualified_query_name=f"user_defined_query[{check_name}]",
        )
        self.sql: str = sql
        self.metric = metric

    def execute(self):
        self.fetchone()
        if self.row is not None:
            for index in range(len(self.description)):
                metric_value = float(self.row[index])
                self.metric.set_value(metric_value)
