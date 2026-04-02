from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from constants import (
    CSV_NAMES,
    ENCODING_UTF8_SIG,
    ERROR_INVALID_OPERATION,
)


class BulkOperationService:
    def __init__(
        self,
        device_repo,
        config_dir,
        filename_service,
        output_sanitizer,
        log_writer,
        activity_logger,
        config_prefix_bulk: str,
        activity_bulk_operation: str,
    ) -> None:
        self._device_repo = device_repo
        self._config_dir = config_dir
        self._filename_service = filename_service
        self._output_sanitizer = output_sanitizer
        self._log_writer = log_writer
        self._activity_logger = activity_logger
        self._config_prefix_bulk = config_prefix_bulk
        self._activity_bulk_operation = activity_bulk_operation

    def run_bulk(self, operation: str, upload_file, config_name: str, log_name: str, current_user: dict):
        from constants import SCRIPTS

        if operation not in SCRIPTS:
            # caller maps this to HTTPException to preserve existing behavior/message
            raise ValueError(ERROR_INVALID_OPERATION)

        df = pd.read_excel(upload_file.file)
        device_types = self._device_repo.load_device_types()
        device_groups = self._device_repo.load_device_groups()

        if operation == "add":
            df["DeviceType"] = df["DeviceType"].apply(lambda v: device_types.get(str(v).strip()))
            df["DeviceGroup"] = df["DeviceGroup"].apply(lambda v: device_groups.get(str(v).strip()))
        elif operation == "update":
            if "DeviceType" in df:
                df["DeviceType"] = df["DeviceType"].apply(
                    lambda v: device_types.get(str(v).strip()) if pd.notna(v) else v
                )
            if "GroupName" in df:
                df["GroupName"] = df["GroupName"].apply(
                    lambda v: device_groups.get(str(v).strip()) if pd.notna(v) else v
                )
            if "NewDeviceGroup" in df:
                df["NewDeviceGroup"] = df["NewDeviceGroup"].apply(
                    lambda v: device_groups.get(str(v).strip()) if pd.notna(v) else v
                )

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / CSV_NAMES[operation]
            df.to_csv(csv_path, index=False, encoding=ENCODING_UTF8_SIG)

            config_filename = self._filename_service.generate_filename(self._config_prefix_bulk, "csv", config_name)
            saved_cfg = self._config_dir / f"bulk_{operation}" / config_filename
            df.to_csv(saved_cfg, index=False, encoding=ENCODING_UTF8_SIG)

            proc = subprocess.run(
                ["python", "-m", SCRIPTS[operation], str(csv_path)],
                capture_output=True,
                text=True,
            )

            clean_stdout = self._output_sanitizer.sanitize_output(proc.stdout)
            clean_stderr = self._output_sanitizer.sanitize_output(proc.stderr)

            self._log_writer.save_log("bulk_operation", clean_stdout, clean_stderr, proc.returncode, log_name)

            self._activity_logger(
                current_user["id"],
                self._activity_bulk_operation,
                f"Executed {operation} operation with {len(df)} devices",
                "bulk",
            )

            return {
                "returncode": proc.returncode,
                "stdout": clean_stdout,
                "stderr": clean_stderr,
            }

