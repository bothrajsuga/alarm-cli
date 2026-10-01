# Alarm Clock CLI

A multi-alarm alarm clock as an interactive command-line application. Built as a timed Senior Software Engineer assessment exercise.

## 1. Overview

Start the app, set one or more alarms by time of day, keep working in the same session (list/cancel alarms, run other commands), and get a console notification + terminal bell when an alarm fires — without the CLI ever blocking while it waits.

## 2. Requirements

- Python 3.9+ (uses `dict[int, Alarm]`-style built-in generic type hints; 3.12 used in development)
- No third-party runtime dependencies — standard library only (`threading`, `datetime`, `re`)
- `pytest` only if you want to run the test suite via `pytest` instead of `unittest`

## 3. Architecture

Three responsibilities, kept deliberately separate:

- **`models.py`** — `Alarm` dataclass. Pure data, no behavior.
- **`scheduler.py`** — `AlarmScheduler`. Owns alarm state and a single background thread that polls for due alarms roughly once per second. All state access goes through one `threading.Lock`.
- **`alarm_cli.py`** — the interactive command loop. Owns input parsing, time-string → `datetime` conversion (including next-day rollover), and how a triggered alarm is displayed. Calls into the scheduler; never touches its internals.

**Why polling over `threading.Timer` per alarm:** a single thread that asks "what's due now?" against an injectable clock is trivial to unit test deterministically (pass a fixed `datetime`, no real waiting) and trivial to reason about with many alarms. Cancellation becomes a boolean flip instead of killing/tracking N timer objects.

**Responsiveness:** the scheduler runs on a daemon background thread; the CLI's `input()` loop is never blocked by alarm waiting. A ~1 second poll interval is the only latency cost.

## 4. Project Structure

```
alarm_cli.py              # CLI entry point, command loop, time parsing
scheduler.py               # AlarmScheduler: state + background polling thread
models.py                  # Alarm dataclass
tests/
  test_scheduler.py         # pytest-style tests
  test_alarm_unittest.py    # unittest-style tests (10 required scenarios)
README.md
```

## 5. Installation / Setup

```bash
# clone or copy the project directory, then:
cd "Alarm CLI"
# no dependencies to install for the app itself
pip install pytest   # optional, only needed to run tests/test_scheduler.py via pytest
```

## 6. How to Run

```bash
python alarm_cli.py
```

Type `help` inside the session for the command list. Exit with `exit` or Ctrl+C — either stops the background thread cleanly before the process ends.

## 7. CLI Commands

| Command | Example | Notes |
|---|---|---|
| `set HH:MM [label]` | `set 07:30 wake up` | 24h clock. If the time has already passed today, it's scheduled for tomorrow. |
| `list` | `list` | Shows active (not fired, not cancelled) alarms, soonest first. |
| `cancel <id>` | `cancel 2` | No-op with a clear message if the id doesn't exist or already fired. |
| `help` | `help` | Shows the command list. |
| `exit` | `exit` | Cancels the background thread and quits. |

Example session:

```
> set 09:00 standup
Alarm 1 set for 2026-06-16 09:00.
> set 18:30 gym
Alarm 2 set for 2026-06-15 18:30.
> list
  [2] 2026-06-15 18:30 - gym (in 95 min)
  [1] 2026-06-16 09:00 - standup (in 1035 min)
> cancel 2
Alarm 2 cancelled.
> list
  [1] 2026-06-16 09:00 - standup (in 1035 min)
> exit
Shutting down...
```

When an alarm fires, it prints a banner (and rings the terminal bell `\a`) directly into the active session, then is removed from `list` output.

## 8. Testing

Two test files, same logic covered from two angles:

```bash
python -m pytest tests/ -v        # pytest style
python -m unittest tests.test_alarm_unittest -v   # unittest style
```

22 tests, all passing as of this writing. Covers: valid alarm creation, invalid HH:MM/hour/minute input, past-time → next-day rollover (including a same-minute edge case, see below), cancellation (including unknown id and already-fired id), multiple independent alarms, due-alarm detection, no double-firing, and empty-list handling.

**All time-dependent tests use a fixed, explicitly-passed `datetime` — none depend on the real wall clock or `sleep()`.** This is possible because `AlarmScheduler.check_due(now)` and `parse_time_to_datetime(time_str, now)` both take "now" as an explicit argument rather than calling `datetime.now()` internally.

## 9. Engineering Decisions

- **Absolute `datetime`, not time-of-day string, as the stored alarm time.** Rollover-to-tomorrow logic runs once at creation time; the scheduler only ever compares two datetimes. This avoids the usual class of midnight-rollover bugs that come from doing arithmetic on `HH:MM` strings.
- **One lock, one background thread, no per-alarm thread/timer.** Simpler concurrency story, and cancellation is just a flag flip the next poll tick naturally skips.
- **Trigger callback passed into the scheduler** (`on_trigger`), rather than the scheduler printing directly. Keeps display/I-O concerns out of the scheduling logic, and makes the scheduler testable without capturing stdout.
- **Scheduler filters `fired`/`cancelled` state internally** (`list_active()`), under the same lock that mutates those fields — added after a review pass caught the CLI reading those flags after the lock had already been released.
- **Same-minute comparison, not same-second.** `parse_time_to_datetime` compares at minute granularity (`now` truncated to the minute) rather than exact-second, otherwise a few seconds of processing delay between typing a command and it being evaluated could wrongly push a "set it for right now" alarm a full day forward. Caught and fixed during manual smoke testing; a regression test (`test_current_minute_not_rolled_despite_elapsed_seconds`) locks it in.

## 10. Trade-offs

- **~1 second trigger latency** from the polling interval — acceptable for a desk alarm clock, would need a different mechanism (e.g. a min-heap + single next-wakeup sleep) for sub-second precision.
- **Linear scan over all alarms each tick** rather than a heap keyed by next-fire-time. Simpler code; fine at realistic alarm counts (tens), would need revisiting at very large scale.
- **Cancel can lose a narrow race** if issued in the same ~1s window the alarm is about to fire — inherent to polling, not fixed, since fixing it would mean a materially different (more complex) scheduling design for a benefit that doesn't matter at this scale.
- **`AlarmScheduler.list_active()` / `check_due()` return live `Alarm` objects**, not copies. No current caller mutates them, so this was left as-is rather than adding defensive copying speculatively.

## 11. Assumptions

- "Trigger" means a console banner + terminal bell (`\a`) — no audio file playback or OS-level notification.
- Alarms are same-day/next-day only; no recurring (daily/weekday) alarms.
- Single interactive session, single user, local system clock — no timezone handling beyond whatever `datetime.now()` returns.
- Time input is `HH:MM` 24-hour only (no seconds, no 12-hour AM/PM format).
- No persistence is expected or wanted between runs — state is in-memory only, by design (no database per the exercise constraints).

## 12. Limitations

- Alarms don't survive process restart — there is no save/load.
- Fired and cancelled alarms stay in memory for the life of the process (never pruned) — not an issue at CLI-session scale, but would leak slowly over a very long-running session.
- No repeat/snooze.
- Output from a firing alarm can interleave somewhat unpredictably with the terminal's own input prompt line, since it's printed from a background thread while the main thread may be mid-`input()`. Cosmetic only — never a correctness issue — and considered acceptable for a terminal application.

## 13. Future Improvements

- Swap the linear scan for a min-heap on `fire_at` if alarm counts were ever expected to be large.
- Optional snooze/repeat (daily, weekdays) if the scope ever grows beyond this exercise.
- Optional persistence (e.g. a flat JSON file) if alarms need to survive restarts — deliberately out of scope here per the "no database" constraint, and arguably unnecessary complexity for a CLI exercise.
- Prune fired/cancelled alarms after some retention window if the process were meant to run indefinitely.

## 14. How AI Was Used

This project was built with Claude Code (Anthropic) as a pair-programming collaborator, in a deliberately staged process:

1. Requirements and scoping (functional/non-functional requirements, MVP scope, edge cases) were drafted by AI, reviewed and accepted by the engineer before any code was written.
2. Architecture (module boundaries, scheduler design, testability seam) was proposed by AI and reviewed before implementation — including explicitly rejecting a `threading.Timer`-per-alarm approach in favor of the polling design, for testability reasons.
3. Implementation was AI-generated against that agreed design.
4. The implementation was then put through an explicit AI-driven code review pass (looking for race conditions, thread-safety issues, incorrect datetime handling, poor separation of concerns, etc.), which surfaced one real thread-safety issue (unsynchronized read of `fired`/`cancelled`) and one error-handling gap — both fixed.
5. A `unittest`-based test suite was added covering the required scenarios, with explicit attention to determinism (no test depends on real wall-clock time).
6. A manual smoke test against the actual running process (not just unit tests) surfaced a second, more subtle bug — a same-minute rollover edge case — which was root-caused, fixed, covered with a regression test, and re-verified against both the test suite and a fresh smoke test run.

All test runs and smoke test output referenced in this README and during development were actually executed, not assumed — including the bug found and fixed in step 6.
