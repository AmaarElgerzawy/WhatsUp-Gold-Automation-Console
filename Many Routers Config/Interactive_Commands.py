from netmiko import ConnectHandler
from pathlib import Path
from datetime import datetime
from getpass import getpass
import json
import os
import sys

# ---------- SETTINGS ----------
base_dir = os.path.dirname(os.path.abspath(__file__))
ROUTER_LIST_FILE = os.environ.get("WUG_ROUTERS")
TASKS_FILE = os.environ.get("WUG_TASKS")
LOG_DIR = Path(os.path.join(base_dir, "bulk_sequence_logs"))
LOG_DIR.mkdir(exist_ok=True)


# ---------- GENERIC INTERACTIVE HELPER ----------

def run_interactive_command(conn, command, steps, context=None, max_rounds=10):
    """
    Run an interactive EXEC command on a Netmiko connection.

    conn    : Netmiko connection
    command : initial command, e.g. "copy running-config tftp:"
    steps   : list of dicts: { "prompt": "...", "answer": "..." }
              'answer' can use .format(**context), e.g. "{tftp_ip}"
    context : dict of variables for formatting answers
    max_rounds : safety limit to avoid infinite loops

    Returns: full concatenated output (string)
    """
    if context is None:
        context = {}

    output = conn.send_command_timing(
        command, strip_prompt=False, strip_command=False
    )
    full_output = output

    for _ in range(max_rounds):
        matched = False

        for step in steps:
            prompt = step["prompt"].replace(r'\r\n', '').replace(r'\n', '').strip()
            raw_answer = step.get("answer", "")

            if prompt in output:
                # Fill variables in answer (e.g. {hostname}, {ip}, {custom})
                answer = raw_answer.format(**context) if raw_answer else ""
                output = conn.send_command_timing(
                    answer + "\n", strip_prompt=False, strip_command=False
                )
                full_output += output
                matched = True
                break  # restart scanning steps on the new output

        if not matched:
            # No known prompt found in the last chunk -> assume done
            break

    return full_output


# ---------- LOAD ROUTER IPs ----------

ips = []

if not ROUTER_LIST_FILE:
    sys.stderr.write("No routers data provided\n")
    raise SystemExit(1)

for line in ROUTER_LIST_FILE.splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        ips.append(line)

if not ips:
    sys.stderr.write(f"No router IPs found in {ROUTER_LIST_FILE}")
    raise SystemExit(1)

sys.stdout.write(f"Found {len(ips)} router(s)\n")
# ---------- LOAD TASKS (ORDERED SEQUENCE) ----------

if not TASKS_FILE:
    sys.stderr.write("No tasks data provided\n")
    raise SystemExit(1)

try:
    tasks = json.loads(TASKS_FILE)
except Exception as e:
    sys.stderr.write(f"Could not parse tasks JSON: {e}\n")
    raise SystemExit(1)

if not isinstance(tasks, list):
    sys.stderr.write(f"{TASKS_FILE} must contain a JSON list.")
    raise SystemExit(1)

sys.stdout.write(f"Loaded {len(tasks)} task(s) from {TASKS_FILE}\n")


# ---------- CREDENTIALS ----------
username = os.environ.get("WUG_SSH_USER")
password = os.environ.get("WUG_SSH_PASS")
enable_password = os.environ.get("WUG_SSH_ENABLE", password)

if not username or not password:
    sys.stderr.write("Missing SSH credentials\n")
    raise SystemExit(1)

timestamp_global = datetime.now().strftime("%Y%m%d-%H%M%S")
# ---------- MAIN LOOP PER ROUTER ----------

for ip in ips:
    sys.stdout.write(f"\n=== Connecting to {ip} ===\n")

    device = {
        "device_type": "cisco_ios",   # change if needed
        "ip": ip,
        "username": username,
        "password": password,
        "secret": enable_password,
    }

    log_file = LOG_DIR / f"{ip}_sequence_{timestamp_global}.log"
    log_output = ""

    try:
        conn = ConnectHandler(**device)
        conn.enable()

        prompt = conn.find_prompt()
        hostname = prompt.strip("#>").strip()
        sys.stdout.write(f"Connected to {hostname} ({ip})\n")

        # Base context available to all tasks
        base_context = {
            "hostname": hostname,
            "ip": ip,
            "timestamp": timestamp_global,
        }

        # ---- EXECUTE TASKS IN ORDER ----
        for idx, task in enumerate(tasks, start=1):
            ttype = task.get("type")
            name = task.get("name", f"task_{idx}")

            log_output += f"\n=== TASK {idx}: {name} (type={ttype}) ===\n"
            sys.stdout.write(f"Running task {idx}: {name} (type={ttype}) on {hostname}\n")

            if ttype == "config":
                # commands: list of config lines
                commands = task.get("commands", [])
                if isinstance(commands, str):
                    commands = [commands]
                if not commands:
                    log_output += "No commands defined.\n"
                    continue

                out = conn.send_config_set(commands)
                log_output += out + "\n"

            elif ttype == "exec":
                # command: single exec command
                command = task.get("command")
                if not command:
                    log_output += "No command defined.\n"
                    continue

                out = conn.send_command(command)
                log_output += out + "\n"

            elif ttype == "interactive_exec":
                # command + steps + (optional) context
                command = task.get("command")
                steps = task.get("steps", [])
                extra_context = task.get("context", {})

                if not command or not steps:
                    log_output += "No command or steps defined.\n"
                    continue

                context = base_context.copy()
                context.update(extra_context)

                out = run_interactive_command(
                    conn,
                    command=command,
                    steps=steps,
                    context=context,
                )
                log_output += out + "\n"

            elif ttype == "write_memory":
                # convenience type
                out = conn.send_command("write memory")
                log_output += out + "\n"

            else:
                msg = f"Unknown task type: {ttype}"
                sys.stderr.write(msg)
                log_output += msg + "\n"

        conn.disconnect()
        sys.stdout.write(log_output)
        sys.stdout.write(f"Done with {hostname} ({ip})\n")

    except Exception as e:
        err_msg = f"ERROR on {ip}: {e}"
        sys.stderr.write(err_msg)
        log_output += "\n" + err_msg + "\n"

    # Save log
    # log_file.write_text(log_output, encoding="utf-8")
    sys.stdout.write(f"Log File saved")
