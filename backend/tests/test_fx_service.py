"""
Exchange rate service.

The failure this file exists to prevent already happened once: the old
Frankfurter primary could never return LKR (the ECB does not publish it),
so every call fell through to the hard-coded constant and the dashboard
showed a stale number while looking healthy. Nothing caught it because
nothing asserted that the live path ever worked.

So each path is pinned here with a stubbed transport: a success, a 429, a
network error, and an out-of-range rate.
"""

import json
import sys
import time
from pathlib import Path

import pytest
import requests

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from services import fx_service as fx  # noqa: E402

GOOD_BODY = {
    "result": "success",
    "time_last_update_utc": "Thu, 09 Oct 2026 00:02:31 +0000",
    "rates": {"LKR": 302.4567, "INR": 88.1234, "EUR": 0.92},
}


class FakeResponse:
    def __init__(self, status_code=200, body=None, raises=False):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._body


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Point the persisted rate at a temp file so tests never touch data/."""
    monkeypatch.setattr(fx, "STATE_PATH", str(tmp_path / "fx_last.json"))
    return tmp_path / "fx_last.json"


def stub(monkeypatch, **kwargs):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        if kwargs.get("network_error"):
            raise requests.ConnectionError("dns failure")
        return FakeResponse(status_code=kwargs.get("status", 200),
                            body=kwargs.get("body", GOOD_BODY),
                            raises=kwargs.get("bad_json", False))

    monkeypatch.setattr(fx.requests, "get", fake_get)
    return calls


# ------------------------------------------------------------------ success

def test_success_uses_the_provider_rate_and_its_own_date(isolated_state, monkeypatch):
    calls = stub(monkeypatch)
    out = fx.get_fx_rates()

    assert len(calls) == 1 and calls[0] == fx.API_URL
    assert out["source"] == "exchangerate-api"
    assert out["rate"] == pytest.approx(302.4567)
    assert out["usd_lkr"] == pytest.approx(302.4567)
    assert out["usd_inr"] == pytest.approx(88.1234)
    # rate_date is the provider's timestamp, not now()
    assert out["rate_date"] == "2026-10-09T00:02:31Z"
    assert out["as_of"] == out["rate_date"]
    assert out["fetched_at"] and out["fetched_at"] != out["rate_date"]
    assert out["provider_url"] == "https://www.exchangerate-api.com"


def test_success_is_persisted_and_survives_a_restart(isolated_state, monkeypatch):
    stub(monkeypatch)
    fx.get_fx_rates()
    assert isolated_state.is_file()
    saved = json.loads(isolated_state.read_text())
    assert saved["usd_lkr"] == pytest.approx(302.4567)

    # A later process with no network at all still serves the saved rate.
    stub(monkeypatch, network_error=True)
    monkeypatch.setattr(fx, "CACHE_TTL_SECONDS", 0)
    monkeypatch.setattr(fx, "MIN_SECONDS_BETWEEN_CALLS", 0)
    out = fx.get_fx_rates()
    assert out["source"] == "cached"
    assert out["rate"] == pytest.approx(302.4567)


# -------------------------------------------------------------------- 429

def test_rate_limited_keeps_the_last_good_rate(isolated_state, monkeypatch):
    stub(monkeypatch)
    fx.get_fx_rates()                                   # seed a good rate

    monkeypatch.setattr(fx, "CACHE_TTL_SECONDS", 0)     # force a re-fetch attempt
    monkeypatch.setattr(fx, "MIN_SECONDS_BETWEEN_CALLS", 0)
    stub(monkeypatch, status=429)
    out = fx.get_fx_rates()

    assert out["source"] == "cached"
    assert out["rate"] == pytest.approx(302.4567)
    assert out["source"] != "fallback", "a 429 must not discard a known-good rate"


def test_rate_limited_with_no_history_falls_back(isolated_state, monkeypatch):
    stub(monkeypatch, status=429)
    out = fx.get_fx_rates()
    assert out["source"] == "fallback"
    assert out["rate"] == pytest.approx(fx.FALLBACK_USD_LKR)
    assert out["fetched_at"] is None


# ---------------------------------------------------------- network error

def test_network_error_falls_back_when_nothing_cached(isolated_state, monkeypatch):
    stub(monkeypatch, network_error=True)
    out = fx.get_fx_rates()
    assert out["source"] == "fallback"
    assert out["rate"] == pytest.approx(fx.FALLBACK_USD_LKR)


def test_non_json_body_is_a_failure(isolated_state, monkeypatch):
    stub(monkeypatch, bad_json=True)
    assert fx.get_fx_rates()["source"] == "fallback"


def test_result_error_is_a_failure_even_on_http_200(isolated_state, monkeypatch):
    stub(monkeypatch, body={"result": "error", "error-type": "unsupported-code"})
    assert fx.get_fx_rates()["source"] == "fallback"


def test_missing_lkr_is_a_failure(isolated_state, monkeypatch):
    """Exactly the Frankfurter case: a 200 with every currency but LKR."""
    stub(monkeypatch, body={"result": "success", "time_last_update_utc": "",
                            "rates": {"INR": 88.1, "EUR": 0.92}})
    assert fx.get_fx_rates()["source"] == "fallback"


# ------------------------------------------------------------ out of range

@pytest.mark.parametrize("bad_rate", [3.025, 30.25, 3024.5, 0.0, -302.0, 249.9, 450.1])
def test_out_of_range_rate_is_rejected(isolated_state, monkeypatch, bad_rate):
    body = dict(GOOD_BODY, rates={"LKR": bad_rate, "INR": 88.1})
    stub(monkeypatch, body=body)
    out = fx.get_fx_rates()
    assert out["source"] == "fallback", f"{bad_rate} should not have been accepted"
    assert out["rate"] == pytest.approx(fx.FALLBACK_USD_LKR)


@pytest.mark.parametrize("ok_rate", [250.0, 302.45, 450.0])
def test_in_range_rate_is_accepted(isolated_state, monkeypatch, ok_rate):
    stub(monkeypatch, body=dict(GOOD_BODY, rates={"LKR": ok_rate, "INR": 88.1}))
    assert fx.get_fx_rates()["rate"] == pytest.approx(ok_rate)


def test_out_of_range_does_not_overwrite_a_good_saved_rate(isolated_state, monkeypatch):
    stub(monkeypatch)
    fx.get_fx_rates()
    monkeypatch.setattr(fx, "CACHE_TTL_SECONDS", 0)
    monkeypatch.setattr(fx, "MIN_SECONDS_BETWEEN_CALLS", 0)
    stub(monkeypatch, body=dict(GOOD_BODY, rates={"LKR": 3.02, "INR": 88.1}))
    out = fx.get_fx_rates()
    assert out["source"] == "cached"
    assert out["rate"] == pytest.approx(302.4567)


# --------------------------------------------------------------- throttling

def test_cache_serves_without_calling(isolated_state, monkeypatch):
    calls = stub(monkeypatch)
    fx.get_fx_rates()
    for _ in range(5):
        out = fx.get_fx_rates()
    assert len(calls) == 1, "within the TTL the provider must not be called again"
    assert out["source"] == "cached"


def test_never_calls_more_than_once_an_hour_after_a_failure(isolated_state, monkeypatch):
    """A failing upstream must not be retried on every request."""
    monkeypatch.setattr(fx, "CACHE_TTL_SECONDS", 0)
    calls = stub(monkeypatch, network_error=True)
    for _ in range(5):
        fx.get_fx_rates()
    assert len(calls) == 1, f"expected one call in the hour window, made {len(calls)}"

    # Once the hour has passed, it tries again.
    state = json.loads(Path(fx.STATE_PATH).read_text())
    state["last_attempt_epoch"] = time.time() - fx.MIN_SECONDS_BETWEEN_CALLS - 1
    Path(fx.STATE_PATH).write_text(json.dumps(state))
    fx.get_fx_rates()
    assert len(calls) == 2


def test_frankfurter_is_gone():
    src = (BACKEND / "services" / "fx_service.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert "frankfurter" not in code.lower().split('"""')[-1], \
        "Frankfurter must not be called; the ECB does not publish LKR"
    assert fx.API_URL == "https://open.er-api.com/v6/latest/USD"


def test_to_lkr_uses_the_rate():
    assert fx.to_lkr(10.0, {"usd_lkr": 302.4567}) == pytest.approx(3024.57)
