import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.memory import backup_memory, load_memory, save_memory  # noqa: E402


def main() -> None:
    backup_path = backup_memory()
    data = load_memory()
    save_memory(data)
    print(f"history migrated; backup={backup_path}")


if __name__ == "__main__":
    main()
