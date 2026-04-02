from __future__ import annotations

from dataclasses import dataclass

from netmiko import ConnectHandler

from constants import SSH_ENABLE_PASSWORD, SSH_PASSWORD, SSH_USERNAME
from wug_backend.routers.simple import RouterListParser, RouterTarget


@dataclass(frozen=True)
class InteractiveStep:
    prompt: str
    answer: str = ""


class InteractiveCommandRunner:
    def run_interactive_command(self, conn, command, steps, context=None, max_rounds=10):
        if context is None:
            context = {}

        output = conn.send_command_timing(command, strip_prompt=False, strip_command=False)
        full_output = output

        for _ in range(max_rounds):
            matched = False
            for step in steps:
                prompt = step["prompt"].replace(r"\r\n", "").replace(r"\n", "").strip()
                raw_answer = step.get("answer", "")

                if prompt in output:
                    answer = raw_answer.format(**context) if raw_answer else ""
                    output = conn.send_command_timing(answer + "\n", strip_prompt=False, strip_command=False)
                    full_output += output
                    matched = True
                    break

            if not matched:
                break

        return full_output

    def execute_tasks(self, router: RouterTarget, tasks: list, device_type_default: str, timestamp_global: str) -> str:
        ip = router.ip
        device_type = (router.device_type or device_type_default).strip() or device_type_default
        print(f"\n=== Connecting to {ip} ({device_type}) ===")

        device = {
            "device_type": device_type,
            "ip": ip,
            "username": SSH_USERNAME,
            "password": SSH_PASSWORD,
            "secret": SSH_ENABLE_PASSWORD,
        }

        log_output = ""
        conn = ConnectHandler(**device)
        try:
            conn.enable()
            prompt = conn.find_prompt()
            hostname = prompt.strip("#>").strip()
            print(f"Connected to {hostname} ({ip})")

            base_context = {"hostname": hostname, "ip": ip, "timestamp": timestamp_global}

            for idx, task in enumerate(tasks, start=1):
                ttype = task.get("type")
                name = task.get("name", f"task_{idx}")

                log_output += f"\n=== TASK {idx}: {name} (type={ttype}) ===\n"
                print(f"Running task {idx}: {name} (type={ttype}) on {hostname}")

                if ttype == "config":
                    commands = task.get("commands", [])
                    if isinstance(commands, str):
                        commands = [commands]
                    if not commands:
                        log_output += "No commands defined.\n"
                        continue
                    out = conn.send_config_set(commands)
                    log_output += out + "\n"

                elif ttype == "exec":
                    command = task.get("command")
                    if not command:
                        log_output += "No command defined.\n"
                        continue
                    out = conn.send_command(command, expect_string=r"#", read_timeout=60)
                    log_output += out + "\n"

                elif ttype == "interactive_exec":
                    command = task.get("command")
                    steps = task.get("steps", [])
                    extra_context = task.get("context", {})

                    if not command or not steps:
                        log_output += "No command or steps defined.\n"
                        continue

                    context = base_context.copy()
                    context.update(extra_context)
                    out = self.run_interactive_command(conn, command=command, steps=steps, context=context)
                    log_output += out + "\n"

                elif ttype == "write_memory":
                    out = conn.send_command("write memory")
                    log_output += out + "\n"
                else:
                    msg = f"ERROR: Unknown task type: {ttype}"
                    import sys

                    print(msg, file=sys.stderr)
                    log_output += msg + "\n"

            conn.disconnect()
            return log_output
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

