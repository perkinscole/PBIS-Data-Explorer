import json
from pathlib import Path

GOALS_FILE = "_goals.json"


def load_goals(data_dir):
    """Load goals from JSON file."""
    goals_path = Path(data_dir) / GOALS_FILE
    if goals_path.exists():
        try:
            return json.loads(goals_path.read_text())
        except Exception:
            pass
    return []


def save_goals(data_dir, goals):
    """Save goals to JSON file."""
    goals_path = Path(data_dir) / GOALS_FILE
    Path(data_dir).mkdir(exist_ok=True)
    goals_path.write_text(json.dumps(goals, indent=2))


def compute_goal_progress(goal, rams_pcts_by_period):
    """Compute progress for a single goal across survey periods.
    rams_pcts_by_period: dict of {period: {category_or_question: pct}}
    Returns dict with current_pct, history, status."""
    target = goal["target_pct"]
    indicator = goal["indicator"]

    history = []
    current_pct = None
    for period, pcts in rams_pcts_by_period.items():
        if indicator in pcts:
            val = pcts[indicator]
            history.append({"period": period, "pct": val})
            current_pct = val

    if current_pct is None:
        status = "no_data"
    elif current_pct >= target:
        status = "achieved"
    elif current_pct >= target - 5:
        status = "close"
    else:
        status = "behind"

    return {
        "current_pct": current_pct,
        "target_pct": target,
        "history": history,
        "status": status,
        "gap": round(current_pct - target, 1) if current_pct is not None else None,
    }
