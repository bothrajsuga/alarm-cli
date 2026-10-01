from __future__ import annotations

import threading
from datetime import datetime

from models import Alarm


class AlarmScheduler:
    """Owns alarm state and a background thread that fires due alarms.

    `clock` and `tick_interval` are injectable so tests can control "now"
    and drive `check_due()` directly without real waiting or threading.
    """

    def __init__(self, on_trigger, clock=datetime.now, tick_interval=1.0):
        self._on_trigger = on_trigger
        self._clock = clock
        self._tick_interval = tick_interval
        self._alarms: dict[int, Alarm] = {}
        self._lock = threading.Lock()
        self._next_id = 1
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def add(self, fire_at: datetime, label: str = "") -> Alarm:
        with self._lock:
            alarm = Alarm(id=self._next_id, fire_at=fire_at, label=label)
            self._alarms[alarm.id] = alarm
            self._next_id += 1
            return alarm

    def cancel(self, alarm_id: int) -> bool:
        with self._lock:
            alarm = self._alarms.get(alarm_id)
            if alarm is None or alarm.fired or alarm.cancelled:
                return False
            alarm.cancelled = True
            return True

    def list_active(self) -> list[Alarm]:
        """Active alarms (not fired, not cancelled), filtered under the lock
        so callers never read `fired`/`cancelled` while the background
        thread might be writing them."""
        with self._lock:
            active = [a for a in self._alarms.values() if not a.fired and not a.cancelled]
            return sorted(active, key=lambda a: a.fire_at)

    def check_due(self, now: datetime) -> list[Alarm]:
        """Pure-ish step: marks due alarms fired and returns them.

        Exposed separately from `_run` so tests can call it directly with
        a synthetic `now`, with no thread or real time involved.
        """
        with self._lock:
            due = [
                a
                for a in self._alarms.values()
                if not a.fired and not a.cancelled and a.fire_at <= now
            ]
            for a in due:
                a.fired = True
        return due

    def _run(self):
        while not self._stop_event.is_set():
            due = self.check_due(self._clock())
            for alarm in due:
                self._on_trigger(alarm)
            self._stop_event.wait(self._tick_interval)
