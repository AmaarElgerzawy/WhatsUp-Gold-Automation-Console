from __future__ import annotations

import shutil
from pathlib import Path


class LogCollector:
    def collect_logs(self, src_dir: Path, dest_dir: Path) -> None:
        if not src_dir.exists():
            return
        for file in src_dir.glob("*.log"):
            shutil.copy(file, dest_dir / file.name)


class OutputSanitizer:
    def __init__(
        self,
        router_scripts_dir: Path,
        bulk_scripts_dir: Path,
        backup_scripts_dir: Path,
        reporting_scripts_dir: Path,
        workdir_placeholder: str,
    ) -> None:
        self._router_scripts_dir = router_scripts_dir
        self._bulk_scripts_dir = bulk_scripts_dir
        self._backup_scripts_dir = backup_scripts_dir
        self._reporting_scripts_dir = reporting_scripts_dir
        self._workdir_placeholder = workdir_placeholder

    def sanitize_output(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace(str(self._router_scripts_dir), self._workdir_placeholder)
        text = text.replace(str(self._bulk_scripts_dir), self._workdir_placeholder)
        text = text.replace(str(self._backup_scripts_dir), self._workdir_placeholder)
        text = text.replace(str(self._reporting_scripts_dir), self._workdir_placeholder)
        return text


class LogWriter:
    def __init__(
        self,
        log_dir: Path,
        default_encoding: str,
        filename_service,
        log_prefix_exit_code: str,
        log_prefix_stdout: str,
        log_prefix_stderr: str,
    ) -> None:
        self._log_dir = log_dir
        self._default_encoding = default_encoding
        self._filename_service = filename_service
        self._log_prefix_exit_code = log_prefix_exit_code
        self._log_prefix_stdout = log_prefix_stdout
        self._log_prefix_stderr = log_prefix_stderr

    def save_file(self, path: Path, content: str) -> None:
        with open(path, "w", encoding=self._default_encoding) as f:
            f.write(content)

    def save_log(self, name: str, stdout: str, stderr: str, code: int, log_name: str | None = None) -> None:
        """Save log file with optional custom name."""
        if log_name and log_name.strip():
            filename = self._filename_service.generate_filename("log", "log", log_name)
        else:
            filename = f"{self._filename_service.timestamp()}_{name}.log"
        path = self._log_dir / filename
        self.save_file(
            path,
            f"{self._log_prefix_exit_code} {code}\n\n{self._log_prefix_stdout}\n{stdout}\n\n{self._log_prefix_stderr}\n{stderr}",
        )

