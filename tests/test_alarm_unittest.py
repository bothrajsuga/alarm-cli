import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import AlarmScheduler
from alarm_cli import parse_time_to_datetime

FIXED_NOW = datetime(2026, 6, 15, 10, 0, 0)


class TestParseTime(unittest.TestCase):
    """Time parsing is deterministic: every case passes an explicit `now`,
    never the real wall clock."""

    def test_valid_alarm_creation(self):
        result = parse_time_to_datetime("14:30", FIXED_NOW)
        self.assertEqual(result, datetime(2026, 6, 15, 14, 30))

    def test_invalid_hhmm_format(self):
        with self.assertRaises(ValueError):
            parse_time_to_datetime("not-a-time", FIXED_NOW)

    def test_invalid_hour(self):
        with self.assertRaises(ValueError):
            parse_time_to_datetime("24:00", FIXED_NOW)

    def test_invalid_minute(self):
        with self.assertRaises(ValueError):
            parse_time_to_datetime("10:60", FIXED_NOW)

    def test_past_time_rolls_to_next_day(self):
        # FIXED_NOW is 10:00; 09:00 has already passed today.
        result = parse_time_to_datetime("09:00", FIXED_NOW)
        self.assertEqual(result, datetime(2026, 6, 16, 9, 0))

    def test_future_time_same_day_not_rolled(self):
        result = parse_time_to_datetime("23:00", FIXED_NOW)
        self.assertEqual(result, datetime(2026, 6, 15, 23, 0))

    def test_current_minute_not_rolled_despite_elapsed_seconds(self):
        # Regression: seconds already elapsed within the target minute
        # (e.g. command processed a few seconds into "10:30") must not
        # cause a same-minute alarm to roll to tomorrow.
        now = FIXED_NOW.replace(minute=30, second=45)
        result = parse_time_to_datetime("10:30", now)
        self.assertEqual(result, datetime(2026, 6, 15, 10, 30, 0))


class TestAlarmScheduler(unittest.TestCase):
    """All time-dependent behavior is driven via explicit `now` values
    passed to `check_due`, never the real clock, and the background
    thread is never started."""

    def setUp(self):
        self.triggered = []
        self.scheduler = AlarmScheduler(on_trigger=self.triggered.append)

    def test_alarm_cancellation(self):
        alarm = self.scheduler.add(fire_at=FIXED_NOW + timedelta(minutes=5))
        self.assertTrue(self.scheduler.cancel(alarm.id))
        self.assertEqual(self.scheduler.check_due(FIXED_NOW + timedelta(minutes=5)), [])

    def test_cancel_unknown_id_returns_false(self):
        self.assertFalse(self.scheduler.cancel(12345))

    def test_cancel_already_fired_alarm_returns_false(self):
        alarm = self.scheduler.add(fire_at=FIXED_NOW)
        self.scheduler.check_due(FIXED_NOW)
        self.assertTrue(alarm.fired)
        self.assertFalse(self.scheduler.cancel(alarm.id))

    def test_multiple_alarms_tracked_independently(self):
        a1 = self.scheduler.add(fire_at=FIXED_NOW + timedelta(minutes=5), label="first")
        a2 = self.scheduler.add(fire_at=FIXED_NOW + timedelta(minutes=10), label="second")
        active = self.scheduler.list_active()
        self.assertEqual({a.id for a in active}, {a1.id, a2.id})
        self.assertNotEqual(a1.id, a2.id)

    def test_due_alarm_detection(self):
        alarm = self.scheduler.add(fire_at=FIXED_NOW + timedelta(minutes=5))
        # Not yet due.
        self.assertEqual(self.scheduler.check_due(FIXED_NOW), [])
        # Exactly due.
        due = self.scheduler.check_due(FIXED_NOW + timedelta(minutes=5))
        self.assertEqual(due, [alarm])

    def test_alarm_not_triggered_twice(self):
        self.scheduler.add(fire_at=FIXED_NOW)
        first_pass = self.scheduler.check_due(FIXED_NOW)
        second_pass = self.scheduler.check_due(FIXED_NOW + timedelta(minutes=1))
        self.assertEqual(len(first_pass), 1)
        self.assertEqual(second_pass, [])

    def test_empty_alarm_list_handled_cleanly(self):
        self.assertEqual(self.scheduler.list_active(), [])
        self.assertEqual(self.scheduler.check_due(FIXED_NOW), [])
        self.assertFalse(self.scheduler.cancel(1))


if __name__ == "__main__":
    unittest.main()
