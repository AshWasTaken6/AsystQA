import json
import os
from datetime import datetime

MEMORY_FILE = "memory/history.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {
            "total_scans": 0,
            "common_issues": {},
            "history": []
        }

    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(data):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def update_memory(bugs, security):
    memory = load_memory()

    memory["total_scans"] += 1

    # Track common issues
    for issue in bugs + security:
        key = issue if isinstance(issue, str) else issue.get("issue", "unknown")

        if key not in memory["common_issues"]:
            memory["common_issues"][key] = 0

        memory["common_issues"][key] += 1

    # Save short history snapshot
    memory["history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "bugs_count": len(bugs),
        "security_count": len(security)
    })

    # Keep history small (last 50 runs)
    memory["history"] = memory["history"][-50:]

    save_memory(memory)

    return memory


def get_insights():
    memory = load_memory()

    most_common = sorted(
        memory["common_issues"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return {
        "total_scans": memory["total_scans"],
        "top_issues": most_common
    }