import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import AlarmScheduler
from alarm_cli import parse_time_to_datetime


def test_check_due_fires_only_when_time_reached():
    fired = []
    scheduler = AlarmScheduler(on_trigger=fired.append)
    now = datetime(2026, 1, 1, 7, 0)
    alarm = scheduler.add(fire_at=now + timedelta(minutes=5))

    assert scheduler.check_due(now) == []
    due = scheduler.check_due(now + timedelta(minutes=5))
    assert due == [alarm]
    assert alarm.fired is True


def test_check_due_does_not_refire():
    fired = []
    scheduler = AlarmScheduler(on_trigger=fired.append)
    now = datetime(2026, 1, 1, 7, 0)
    scheduler.add(fire_at=now)

    first = scheduler.check_due(now)
    second = scheduler.check_due(now + timedelta(minutes=1))
    assert len(first) == 1
    assert second == []


def test_cancelled_alarm_never_fires():
    scheduler = AlarmScheduler(on_trigger=lambda a: None)
    now = datetime(2026, 1, 1, 7, 0)
    alarm = scheduler.add(fire_at=now)

    assert scheduler.cancel(alarm.id) is True
    assert scheduler.check_due(now) == []


def test_cancel_unknown_id_returns_false():
    scheduler = AlarmScheduler(on_trigger=lambda a: None)
    assert scheduler.cancel(999) is False


def test_multiple_alarms_fire_independently():
    fired = []
    scheduler = AlarmScheduler(on_trigger=fired.append)
    now = datetime(2026, 1, 1, 7, 0)
    a1 = scheduler.add(fire_at=now)
    a2 = scheduler.add(fire_at=now + timedelta(minutes=10))

    due = scheduler.check_due(now)
    assert due == [a1]
    due = scheduler.check_due(now + timedelta(minutes=10))
    assert due == [a2]


def test_parse_time_rolls_to_tomorrow_when_passed():
    now = datetime(2026, 1, 1, 10, 0)
    result = parse_time_to_datetime("09:00", now)
    assert result == datetime(2026, 1, 2, 9, 0)


def test_parse_time_same_day_when_future():
    now = datetime(2026, 1, 1, 10, 0)
    result = parse_time_to_datetime("23:00", now)
    assert result == datetime(2026, 1, 1, 23, 0)


def test_parse_time_rejects_invalid_format():
    now = datetime(2026, 1, 1, 10, 0)
    try:
        parse_time_to_datetime("25:99", now)
        assert False, "expected ValueError"
    except ValueError:
        pass
