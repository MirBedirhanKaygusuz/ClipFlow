"""Tests for the progress tracker (app/services/progress_tracker.py)."""

import time

import pytest


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker():
    """Return a fresh ProgressTracker instance for each test."""
    from app.services.progress_tracker import ProgressTracker  # noqa: PLC0415
    return ProgressTracker(job_id="test-job-001")


# ---------------------------------------------------------------------------
# Tests — basic state
# ---------------------------------------------------------------------------

def test_initial_status_is_queued(tracker):
    """A newly created tracker starts in 'queued' status."""
    assert tracker.status == "queued"


def test_initial_progress_is_zero(tracker):
    """A newly created tracker has 0 % progress."""
    assert tracker.progress == 0


def test_update_step_sets_current_step(tracker):
    """update_step records the step name."""
    tracker.update_step("silence_detection")
    assert tracker.current_step == "silence_detection"


def test_update_progress_within_bounds(tracker):
    """update_step with a progress value stores it correctly."""
    tracker.update_step("transcription", progress=42)
    assert tracker.progress == 42


def test_status_becomes_processing_on_first_update(tracker):
    """Status transitions to 'processing' once update_step is called."""
    tracker.update_step("scene_detection", progress=10)
    assert tracker.status == "processing"


# ---------------------------------------------------------------------------
# Tests — complete / fail
# ---------------------------------------------------------------------------

def test_complete_sets_status_done(tracker):
    """complete() sets status to 'done' and progress to 100."""
    tracker.update_step("render", progress=80)
    tracker.complete()

    assert tracker.status == "done"
    assert tracker.progress == 100


def test_complete_records_output_file_id(tracker):
    """complete() stores the output_file_id when provided."""
    tracker.complete(output_file_id="out-abc123")
    assert tracker.output_file_id == "out-abc123"


def test_fail_sets_status_failed(tracker):
    """fail() sets status to 'failed'."""
    tracker.update_step("ffmpeg_encode", progress=55)
    tracker.fail(reason="FFmpeg exited with code 1")

    assert tracker.status == "failed"


def test_fail_stores_error_reason(tracker):
    """fail() stores a human-readable error reason."""
    tracker.fail(reason="Out of disk space")
    assert "disk" in tracker.error.lower()


def test_fail_does_not_alter_last_progress(tracker):
    """Progress percentage at the point of failure is preserved."""
    tracker.update_step("upload", progress=33)
    tracker.fail(reason="Network error")
    assert tracker.progress == 33


# ---------------------------------------------------------------------------
# Tests — substep / history tracking
# ---------------------------------------------------------------------------

def test_substep_history_is_empty_initially(tracker):
    """No substeps are recorded before any update."""
    assert tracker.history == []


def test_substep_appended_on_each_update(tracker):
    """Each update_step call appends an entry to history."""
    tracker.update_step("step_a", progress=10)
    tracker.update_step("step_b", progress=50)

    assert len(tracker.history) == 2
    names = [entry["step"] for entry in tracker.history]
    assert names == ["step_a", "step_b"]


def test_substep_history_contains_progress(tracker):
    """Each history entry records the progress at the time of the call."""
    tracker.update_step("ingest", progress=5)
    tracker.update_step("analyse", progress=40)

    assert tracker.history[0]["progress"] == 5
    assert tracker.history[1]["progress"] == 40


def test_substep_history_contains_timestamp(tracker):
    """Each history entry has a numeric timestamp."""
    tracker.update_step("encode", progress=70)
    entry = tracker.history[0]
    assert "timestamp" in entry
    assert isinstance(entry["timestamp"], float)


# ---------------------------------------------------------------------------
# Tests — ETA calculation
# ---------------------------------------------------------------------------

def test_eta_is_none_before_any_update(tracker):
    """ETA cannot be estimated before any progress has been made."""
    assert tracker.eta_seconds is None


def test_eta_is_none_at_zero_progress(tracker):
    """ETA is None when progress is still 0 after a step update."""
    tracker.update_step("init", progress=0)
    assert tracker.eta_seconds is None


def test_eta_is_positive_during_processing(tracker):
    """ETA is a positive number when there is measurable progress."""
    # Simulate elapsed time by back-dating the start time
    tracker.update_step("encode", progress=1)  # triggers status → processing
    tracker._start_time = time.monotonic() - 5.0  # pretend 5 s have passed
    tracker.update_step("encode", progress=25)

    assert tracker.eta_seconds is not None
    assert tracker.eta_seconds > 0


def test_eta_decreases_as_progress_increases(tracker):
    """ETA shrinks as the job makes more progress."""
    tracker.update_step("render", progress=1)
    tracker._start_time = time.monotonic() - 10.0

    tracker.update_step("render", progress=20)
    eta_early = tracker.eta_seconds

    tracker._start_time = time.monotonic() - 20.0
    tracker.update_step("render", progress=80)
    eta_late = tracker.eta_seconds

    assert eta_late < eta_early


def test_eta_is_none_after_complete(tracker):
    """ETA is None once the job is done (no remaining work)."""
    tracker.update_step("render", progress=99)
    tracker.complete()
    assert tracker.eta_seconds is None
