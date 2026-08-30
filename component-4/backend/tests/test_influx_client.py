import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_influx_disabled_by_default(monkeypatch):
    monkeypatch.setenv("INFLUXDB_ENABLED", "false")
    monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")

    import services.influx_client as influx_client
    importlib.reload(influx_client)

    assert influx_client.INFLUXDB_ENABLED is False
    assert influx_client._client() is None
