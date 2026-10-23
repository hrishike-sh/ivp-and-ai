"""Resource configuration only: these tests never load a model or spawn a worker."""
from types import SimpleNamespace

import pytest

from ivp import performance


def test_affinity_limits_available_threads(monkeypatch):
    monkeypatch.setattr(performance.os, 'sched_getaffinity', lambda pid: {2, 3, 7}, raising=False)
    monkeypatch.setattr(performance.os, 'cpu_count', lambda: 20)
    assert performance.available_cpu_threads() == 3


@pytest.mark.parametrize('count, expected', [(16, 16), (20, 20), (1, 1), (None, 1), (0, 1)])
def test_windows_uses_detected_logical_processors(monkeypatch, count, expected):
    monkeypatch.delattr(performance.os, 'sched_getaffinity', raising=False)
    monkeypatch.setattr(performance.os, 'cpu_count', lambda: count)
    assert performance.available_cpu_threads() == expected


@pytest.mark.parametrize('failure', [OSError, NotImplementedError])
def test_unavailable_affinity_falls_back(monkeypatch, failure):
    def unavailable(pid):
        raise failure()
    monkeypatch.setattr(performance.os, 'sched_getaffinity', unavailable, raising=False)
    monkeypatch.setattr(performance.os, 'cpu_count', lambda: 16)
    assert performance.available_cpu_threads() == 16
