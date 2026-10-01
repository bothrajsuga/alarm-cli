import re
import sys
from datetime import datetime, timedelta

from scheduler import AlarmScheduler

TIME_RE = re.compile(r"^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$")

HELP = """\
Commands:
  set HH:MM [label]   Set an alarm (24h clock). Past times roll to tomorrow.
  list                 List all active alarms.
  cancel <id>          Cancel an alarm by id.
  help                 Show this message.
  exit                 Quit (pending alarms are cancelled).
"""


def parse_time_to_datetime(time_str: str, now: datetime) -> datetime:
    """Convert "HH:MM" to the next occurrence of that time from `now`.

    Raises ValueError on bad input. If the time has already passed today,
    schedules it for tomorrow instead.
    """
    match = TIME_RE.match(time_str.strip())
    if not match:
        raise ValueError(f"invalid time '{time_str}', expected HH:MM (24h)")
    hour, minute = int(match.group(1)), int(match.group(2))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    current_minute = now.replace(second=0, microsecond=0)
    if candidate < current_minute:
        candidate += timedelta(days=1)
    return candidate


def print_alarm_banner(alarm):
    print(f"\a\n*** ALARM {alarm.id} *** {alarm.label or '(no label)'} — "
          f"it's {alarm.fire_at.strftime('%H:%M')}! ***\n> ", end="", flush=True)


def format_alarm(alarm) -> str:
    remaining = alarm.fire_at - datetime.now()
    minutes_left = max(0, int(remaining.total_seconds() // 60))
    label = f" - {alarm.label}" if alarm.label else ""
    return f"  [{alarm.id}] {alarm.fire_at.strftime('%Y-%m-%d %H:%M')}{label} (in {minutes_left} min)"


def run():
    scheduler = AlarmScheduler(on_trigger=print_alarm_banner)
    scheduler.start()
    print("Alarm Clock CLI. Type 'help' for commands.")

    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                continue

            parts = line.split(maxsplit=2)
            command = parts[0].lower()

            try:
                if command == "exit":
                    break

                elif command == "help":
                    print(HELP)

                elif command == "set":
                    if len(parts) < 2:
                        print("usage: set HH:MM [label]")
                        continue
                    time_str = parts[1]
                    label = parts[2] if len(parts) > 2 else ""
                    try:
                        fire_at = parse_time_to_datetime(time_str, datetime.now())
                    except ValueError as exc:
                        print(f"error: {exc}")
                        continue
                    alarm = scheduler.add(fire_at, label)
                    print(f"Alarm {alarm.id} set for {fire_at.strftime('%Y-%m-%d %H:%M')}.")

                elif command == "list":
                    alarms = scheduler.list_active()
                    if not alarms:
                        print("No active alarms.")
                    else:
                        for alarm in alarms:
                            print(format_alarm(alarm))

                elif command == "cancel":
                    if len(parts) < 2 or not parts[1].isdigit():
                        print("usage: cancel <id>")
                        continue
                    if scheduler.cancel(int(parts[1])):
                        print(f"Alarm {parts[1]} cancelled.")
                    else:
                        print(f"No active alarm with id {parts[1]}.")

                else:
                    print(f"unknown command '{command}'. Type 'help' for commands.")
            except Exception as exc:
                print(f"error: {exc}")

    except KeyboardInterrupt:
        print()
    finally:
        print("Shutting down...")
        scheduler.stop()


if __name__ == "__main__":
    sys.exit(run() or 0)
