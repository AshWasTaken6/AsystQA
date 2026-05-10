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


def update_memory(reviewer_output, security_output, language: str):
    memory = load_memory()

    memory["total_scans"] += 1

    for item in reviewer_output + security_output:
        issue = item.get("issue", "Unknown issue")

        memory["common_issues"][issue] = memory["common_issues"].get(issue, 0) + 1

    memory["history"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "language": language,
        "review_issues": len(reviewer_output),
        "security_issues": len(security_output),
        "issue_total": len(reviewer_output) + len(security_output),
    })

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