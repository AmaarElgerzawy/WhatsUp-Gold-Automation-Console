from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path



class RouterCommandService:
    def __init__(
        self,
        router_scripts_dir: Path,
        log_dir: Path,
        config_router_interactive_dir: Path,
        config_router_simple_dir: Path,
        default_encoding: str,
        log_collector,
        log_writer,
        activity_logger,
        env_wug_routers: str,
        env_wug_tasks: str,
        env_wug_ssh_user: str,
        env_wug_ssh_pass: str,
        env_wug_ssh_enable: str,
        config_prefix_interactive: str,
        config_prefix_simple: str,
        log_file_prefix_interactive: str,
        log_file_prefix_simple: str,
        activity_interactive_commands: str,
        activity_interactive_commands_error: str,
        activity_simple_commands: str,
    ) -> None:
        self._router_scripts_dir = router_scripts_dir
        self._log_dir = log_dir
        self._config_router_interactive_dir = config_router_interactive_dir
        self._config_router_simple_dir = config_router_simple_dir
        self._default_encoding = default_encoding
        self._log_collector = log_collector
        self._log_writer = log_writer
        self._activity_logger = activity_logger
        self._env_wug_routers = env_wug_routers
        self._env_wug_tasks = env_wug_tasks
        self._env_wug_ssh_user = env_wug_ssh_user
        self._env_wug_ssh_pass = env_wug_ssh_pass
        self._env_wug_ssh_enable = env_wug_ssh_enable
        self._config_prefix_interactive = config_prefix_interactive
        self._config_prefix_simple = config_prefix_simple
        self._log_file_prefix_interactive = log_file_prefix_interactive
        self._log_file_prefix_simple = log_file_prefix_simple
        self._activity_interactive_commands = activity_interactive_commands
        self._activity_interactive_commands_error = activity_interactive_commands_error
        self._activity_simple_commands = activity_simple_commands

    def run_interactive(
        self,
        routers: str,
        device_type_default: str,
        tasks_json: str,
        username: str,
        password: str,
        enable_password: str,
        config_name: str,
        log_name: str,
        current_user: dict,
        filename_service,
    ):
        env = os.environ.copy()
        env[self._env_wug_routers] = routers
        env[self._env_wug_tasks] = tasks_json
        env[self._env_wug_ssh_user] = username
        env[self._env_wug_ssh_pass] = password
        env[self._env_wug_ssh_enable] = enable_password or password
        env["WUG_DEVICE_TYPE_DEFAULT"] = (device_type_default or "").strip() or "cisco_ios"

        try:
            proc = subprocess.run(
                ["python", "-m", "wug_backend.runners.router_interactive"],
                capture_output=True,
                text=True,
                env=env,
            )

            # No longer collecting script-side logs; behavior preserved by returning stdout/stderr like before.

            self._log_writer.save_log(self._log_file_prefix_interactive, proc.stdout, proc.stderr, proc.returncode, log_name)

            router_count = len([r for r in routers.splitlines() if r.strip()])
            self._activity_logger(
                current_user["id"],
                self._activity_interactive_commands,
                f"Ran Tasks on {router_count} router(s)",
                "routers",
            )

            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except Exception as e:
            self._activity_logger(
                current_user["id"],
                self._activity_interactive_commands_error,
                f"Error: {str(e)}",
                "routers",
            )
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
            }

    def run_simple(
        self,
        routers: str,
        config: str,
        device_type_default: str,
        username: str,
        password: str,
        enable_password: str,
        config_name: str,
        log_name: str,
        current_user: dict,
        filename_service,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            routers_file = os.path.join(tmp, "routers.txt")
            config_file = os.path.join(tmp, "config.txt")

            with open(routers_file, "w", encoding=self._default_encoding) as f:
                f.write(routers)

            with open(config_file, "w", encoding=self._default_encoding) as f:
                f.write(config)

            env = os.environ.copy()
            env["WUG_ROUTERS_FILE"] = routers_file
            env["WUG_CONFIG_FILE"] = config_file
            env["WUG_SSH_USER"] = username
            env["WUG_SSH_PASS"] = password
            env["WUG_SSH_ENABLE"] = enable_password or password
            env["WUG_DEVICE_TYPE_DEFAULT"] = (device_type_default or "").strip() or "cisco_ios"

            proc = subprocess.run(
                ["python", "-m", "wug_backend.runners.router_simple"],
                capture_output=True,
                text=True,
                env=env,
            )

            config_filename = filename_service.generate_filename(self._config_prefix_simple, "txt", config_name)
            saved_cfg = self._config_router_simple_dir / config_filename
            import shutil
            shutil.copy(config_file, saved_cfg)

            self._log_writer.save_log(self._log_file_prefix_simple, proc.stdout, proc.stderr, proc.returncode, log_name)

            router_count = len([r for r in routers.splitlines() if r.strip()])
            self._activity_logger(
                current_user["id"],
                self._activity_simple_commands,
                f"Ran simple config on {router_count} router(s)",
                "routers",
            )

            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }

