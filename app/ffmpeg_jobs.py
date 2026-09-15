"""P2 first slice - the ffmpeg subprocess lifecycle.

A transcode runs for minutes, so it cannot use the subprocess.run shape the probe and the subtitle
extractor use (app/media_probe.py, app/subtitle_tracks.py). Each job owns a Popen, a destination
file and a heartbeat. A job nobody has asked about for IDLE_SECONDS is abandoned and killed; one
that outlives MAX_SECONDS is killed too. Nothing here decides WHAT to run -- app/transcode.py does
that -- and nothing here serves the result."""

from __future__ import annotations

import logging
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path

from app import config

log = logging.getLogger(__name__)

# A player that is still watching asks for status; one that has gone away stops asking.
IDLE_SECONDS = 120
# A ceiling for something that is polled forever but will never finish.
MAX_SECONDS = 6 * 3600


class Job:
    """One ffmpeg run, and what is known about it."""

    def __init__(self, source: str, dest: str, args: list[str], mode: str) -> None:
        self.id = secrets.token_urlsafe(12)
        self.source = source
        self.dest = dest
        self.args = args
        self.mode = mode  # remux | transcode
        self.process = None  # type: ignore[assignment]
        self.started = time.monotonic()
        self.touched = time.monotonic()
        self.duration_ms = 0  # filled by the caller when it knows the source duration
        self.out_time_ms = 0
        self.returncode: int | None = None
        self.error: str | None = None
        self.stopped = False  # a deliberate kill is not a failure
        self.tail: list[str] = []
        self._lock = threading.Lock()

    @property
    def finished(self) -> bool:
        return self.returncode is not None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.error is None

    @property
    def progress(self) -> float | None:
        """0..1 through the source, or None while the source length is unknown."""
        if not self.duration_ms:
            return None
        return max(0.0, min(1.0, self.out_time_ms / self.duration_ms))

    def snapshot(self) -> dict:
        """A copy for a JSON response, so a caller never holds the live lock."""
        with self._lock:
            return {
                "id": self.id, "mode": self.mode, "finished": self.finished, "ok": self.ok,
                "progress": self.progress, "out_time_ms": self.out_time_ms,
                "error": self.error, "seconds": round(time.monotonic() - self.started, 1),
            }


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()


def _reader(job: Job) -> None:
    """Drain ffmpeg's progress stream, keeping the last few lines for a failure message.

    ffmpeg writes key=value lines to stdout with -progress pipe:1; the interesting one is
    out_time_ms, which is how far through the source it has got."""
    stream = job.process.stdout
    if stream is None:
        return
    try:
        for raw in stream:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("out_time_ms="):
                value = line.split("=", 1)[1].strip()
                if value.isdigit():
                    with job._lock:
                        job.out_time_ms = int(value) // 1000
            elif line:
                with job._lock:
                    job.tail.append(line)
                    del job.tail[:-8]
    except (OSError, ValueError):
        pass


def _stderr_reader(job: Job) -> None:
    """Keep the tail of stderr, which is where ffmpeg explains a failure."""
    stream = job.process.stderr
    if stream is None:
        return
    try:
        for raw in stream:
            line = raw.decode("utf-8", "replace").strip()
            if line:
                with job._lock:
                    job.tail.append(line)
                    del job.tail[:-8]
    except (OSError, ValueError):
        pass


def _wait(job: Job) -> None:
    """Reap the process and record how it ended. Runs in its own thread so the request path
    never blocks on ffmpeg."""
    try:
        job.process.wait()
    finally:
        code = job.process.returncode
        with job._lock:
            job.returncode = code if code is not None else -1
            if job.returncode != 0 and job.error is None:
                job.error = (job.tail[-1] if job.tail else f"ffmpeg exited {job.returncode}")
        if job.returncode != 0 and not job.stopped:
            log.warning("ffmpeg job %s (%s) failed: %s", job.id, job.mode, job.error)
        elif job.returncode == 0:
            log.info("ffmpeg job %s (%s) finished in %.1fs", job.id, job.mode, time.monotonic() - job.started)


def start(source: str, dest: str, args: list[str], mode: str, duration_ms: int = 0) -> Job | None:
    """Run one ffmpeg job. Returns None when the process could not be started at all."""
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    job = Job(source, dest, args, mode)
    job.duration_ms = duration_ms
    try:
        job.process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        log.warning("could not start ffmpeg for %s: %s", source, exc)
        return None
    with _jobs_lock:
        _jobs[job.id] = job
    threading.Thread(target=_reader, args=(job,), daemon=True).start()
    threading.Thread(target=_stderr_reader, args=(job,), daemon=True).start()
    threading.Thread(target=_wait, args=(job,), daemon=True).start()
    return job


def touch(job_id: str) -> None:
    """Mark a job as still wanted. The routes call this whenever they serve its result."""
    job = get(job_id)
    if job is not None:
        job.touched = time.monotonic()


def get(job_id: str) -> Job | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def find(dest: str) -> Job | None:
    """A running job already writing this destination, if there is one. Asking twice must join
    the first conversion rather than start a second ffmpeg on the same file."""
    for job in list(_jobs.values()):
        if job.dest == dest and not job.finished:
            return job
    return None


def stop(job_id: str) -> None:
    """Kill a job and forget it. Its partial output is removed, because a half-written file
    would look playable and fail in the middle."""
    job = get(job_id)
    if job is None:
        return
    job.stopped = True
    if job.process is not None and job.process.poll() is None:
        job.process.kill()
    with _jobs_lock:
        _jobs.pop(job_id, None)
    _discard(job.dest)


def _discard(dest: str) -> None:
    try:
        os.unlink(dest)
    except OSError:
        pass


def reap() -> int:
    """Kill abandoned and over-long jobs, and drop the finished ones from memory. Called on a
    timer rather than from a request, so a request never waits on someone else's cleanup."""
    now = time.monotonic()
    killed = 0
    for job_id, job in list(_jobs.items()):
        if job.finished:
            with _jobs_lock:
                _jobs.pop(job_id, None)
            continue
        if now - job.touched > IDLE_SECONDS or now - job.started > MAX_SECONDS:
            log.info("reaping idle ffmpeg job %s (%.0fs)", job_id, now - job.touched)
            stop(job_id)
            killed += 1
    return killed


def active() -> list[dict]:
    """Snapshots of the jobs still running, for an admin view."""
    return [job.snapshot() for job in list(_jobs.values()) if not job.finished]
