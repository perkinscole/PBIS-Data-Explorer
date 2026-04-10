import json
from pathlib import Path

ALERTS_FILE = "_alerts.json"


def load_alerts(data_dir):
    path = Path(data_dir) / ALERTS_FILE
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def save_alerts(data_dir, alerts):
    path = Path(data_dir) / ALERTS_FILE
    Path(data_dir).mkdir(exist_ok=True)
    path.write_text(json.dumps(alerts, indent=2))


def check_alerts(alerts, current_pcts):
    """Check alerts against current percentages.
    current_pcts: dict of {indicator_name: pct_value}
    Returns list of (alert, fired: bool, current_value)."""
    results = []
    for alert in alerts:
        indicator = alert["indicator"]
        threshold = alert["threshold"]
        direction = alert["direction"]  # "below" or "above"

        current = current_pcts.get(indicator)
        if current is None:
            results.append((alert, None, None))
            continue

        if direction == "below":
            fired = current < threshold
        else:
            fired = current > threshold

        results.append((alert, fired, current))

    return results
