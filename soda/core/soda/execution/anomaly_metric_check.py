from __future__ import annotations

from datetime import timezone

from soda.execution.check_outcome import CheckOutcome
from soda.execution.column import Column
from soda.execution.data_source_scan import DataSourceScan
from soda.execution.metric import Metric
from soda.execution.metric_check import MetricCheck
from soda.execution.partition import Partition
from soda.soda_cloud.historic_descriptor import (
    HistoricCheckResultsDescriptor,
    HistoricMeasurementsDescriptor,
)
from soda.sodacl.metric_check_cfg import MetricCheckCfg

KEY_HISTORIC_MEASUREMENTS = "historic_measurements"
KEY_HISTORIC_CHECK_RESULTS = "historic_check_results"


class AnomalyMetricCheck(MetricCheck):
    def __init__(
        self,
        check_cfg: MetricCheckCfg,
        data_source_scan: DataSourceScan,
        partition: Partition | None = None,
        column: Column | None = None,
    ):

        try:
            super().__init__(
                check_cfg=check_cfg,
                data_source_scan=data_source_scan,
                partition=partition,
                column=column,
            )

            self.skip_anomaly_check = False
            metric_check_cfg: MetricCheckCfg = self.check_cfg
            if not metric_check_cfg.fail_threshold_cfg and not metric_check_cfg.warn_threshold_cfg:
                self.skip_anomaly_check = True
            metric_name = metric_check_cfg.metric_name
            metric = self.metrics[metric_name]

            self.historic_descriptors[KEY_HISTORIC_MEASUREMENTS] = HistoricMeasurementsDescriptor(
                metric_identity=metric.identity,
                limit=1000,
            )
            self.historic_descriptors[KEY_HISTORIC_CHECK_RESULTS] = HistoricCheckResultsDescriptor(
                check_identity=self.create_identity(), limit=3
            )
            self.diagnostics = {}
            self.cloud_check_type = "anomalyDetection"
        except Exception as e:
            data_source_scan.scan._logs.error(
                f"""An error occurred during the initialization of AnomalyMetricCheck""", exception=e
            )

    def evaluate(self, metrics: dict[str, Metric], historic_values: dict[str, object]):
        if self.skip_anomaly_check:
            error_message = (
                "Anomaly detection was not given a threshold. You might want to check if the parser returned errors"
            )
            self.add_outcome_reason(outcome_type="parserFailed", message=error_message, severity="error")
            return

        # TODO Review the data structure and see if we still need the KEY_HISTORIC_*
        historic_measurements = historic_values.get(KEY_HISTORIC_MEASUREMENTS, {}).get("measurements", {})
        historic_check_results = historic_values.get(KEY_HISTORIC_CHECK_RESULTS, {}).get("check_results", {})

        if not historic_measurements:
            self.logs.warning(f"This is the first time that we derive {metrics[self.name]} metric")
            historic_measurements["results"] = []

        # Append current results
        historic_measurements.get("results", []).append(
            {
                "id": 61,  # Placeholder number that will be overwritten
                "identity": metrics[self.name].identity,
                "value": self.get_metric_value(),
                "dataTime": (
                    self.data_source_scan.scan._data_timestamp.replace(tzinfo=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                ),
            }
        )

        # TODO test for module installation and set check status to is_skipped if the module is not installed
        from soda.scientific.anomaly_detection.anomaly_detector import AnomalyDetector

        anomaly_detector = AnomalyDetector(historic_measurements, historic_check_results, self.logs)
        level, diagnostics = anomaly_detector.evaluate()
        assert isinstance(diagnostics, dict), f"Anomaly diagnostics should be a dict. Got a {type(diagnostics)} instead"

        if diagnostics["anomalyErrorCode"] == "not_enough_measurements":
            self.add_outcome_reason(
                outcome_type=diagnostics["anomalyErrorCode"],
                message="Anomaly detection needs at least 5 measurements",
                severity=diagnostics["anomalyErrorSeverity"],
            )
            self.diagnostics = diagnostics
            if self.diagnostics["value"] is None:
                self.diagnostics["value"] = self.get_metric_value()
            return

        assert isinstance(
            diagnostics["anomalyProbability"], float
        ), f"Anomaly probability must be a float but it is {type(diagnostics['anomalyProbability'])}"
        self.check_value = diagnostics["anomalyProbability"]
        self.outcome = CheckOutcome(level)
        self.diagnostics = diagnostics
        if diagnostics["anomalyErrorCode"]:
            self.add_outcome_reason(
                outcome_type=diagnostics["anomalyErrorCode"],
                message=diagnostics["anomalyErrorMessage"],
                severity=diagnostics["anomalyErrorSeverity"],
            )

    def get_cloud_diagnostics_dict(self) -> dict:
        cloud_diagnostics = super().get_cloud_diagnostics_dict()
        return {**cloud_diagnostics, **self.diagnostics}

    def get_log_diagnostic_dict(self) -> dict:
        log_diagnostics = super().get_log_diagnostic_dict()
        if self.historic_diff_values:
            log_diagnostics.update(self.diagnostics)
        return log_diagnostics
