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


def update_memory(reviewer_output, security_output):
    memory = load_memory()

    memory["total_scans"] += 1

    # ✅ FIXED LOOP (proper indentation + no duplicate check)
    for item in reviewer_output + security_output:
        issue = item["issue"]

        if issue not in memory["common_issues"]:
            memory["common_issues"][issue] = 0

        memory["common_issues"][issue] += 1

    # ✅ history should be OUTSIDE the loop
    memory["history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "review_issues": len(reviewer_output),
        "security_issues": len(security_output)
    })

    # keep last 50 runs
    memory["history"] = memory["history"][-50:]

    save_memory(memory)


def get_insights():
    memory = load_memory()

    top_issues = sorted(
        memory["common_issues"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return {
        "total_scans": memory["total_scans"],
        "top_issues": top_issues
    }