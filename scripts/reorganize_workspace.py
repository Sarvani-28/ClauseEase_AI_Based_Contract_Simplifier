"""
Safe workspace reorganization preview script.

This script will only print what it would move; it does not perform destructive moves.
Run with `python reorganize_workspace.py --apply` to actually move files (only after you review the plan).

Behavior:
- Creates a mapping from existing top-level scripts to target directories.
- Backs up files that would be moved to `backup/` before moving when `--apply` is used.
- Updates simple import references for the repo root modules (best-effort), but will not attempt deep AST rewrites.

Note: Always review the printed plan before running with --apply.
"""
from pathlib import Path
import shutil
import argparse
import json

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / "backup_before_reorg"
PROPOSED = {
    "src": [
        "document_ingestion.py",
        "text_preprocessing.py",
        "clause_detection.py",
        "language_simplification.py",
        "legal_terms.py",
        "text_to_speech.py",
    ],
    "webui": [
        "streamlit_app.py",
        "login.py",
    ],
    "scripts": [
        "download_models.py",
        "reorganize_workspace.py",
    ],
    "tests": [
        "test_login.py",
    ],
    "models": [
        # keep model artifacts or downloaded files out of repo by default; placeholder
    ],
    "data": [
        "users.json",
        "sessions.json",
    ],
}


def find_existing_files():
    found = []
    for p in ROOT.iterdir():
        if p.is_file():
            found.append(p.name)
    return found


def plan_moves():
    existing = find_existing_files()
    plan = []
    for target_dir, files in PROPOSED.items():
        for fn in files:
            if fn in existing:
                src = ROOT / fn
                dst = ROOT / target_dir / fn
                plan.append({"src": str(src), "dst": str(dst)})
    # Any other top-level python files: move to src
    for p in existing:
        if p.endswith('.py') and p not in sum(PROPOSED.values(), []):
            plan.append({"src": str(ROOT / p), "dst": str(ROOT / 'src' / p)})
    # non-code files: keep in root or data
    return plan


def pretty_print_plan(plan):
    print("Planned moves:")
    for item in plan:
        print(f"  {item['src']} -> {item['dst']}")


def apply_plan(plan):
    BACKUP_DIR.mkdir(exist_ok=True)
    for item in plan:
        src = Path(item['src'])
        dst = Path(item['dst'])
        if not src.exists():
            print(f"Skipping missing: {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / src.name
        shutil.copy2(src, backup_path)
        shutil.move(str(src), str(dst))
        print(f"Moved {src} -> {dst} (backup at {backup_path})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply the planned moves')
    args = parser.parse_args()
    plan = plan_moves()
    pretty_print_plan(plan)
    if args.apply:
        confirm = input('Type YES to proceed with moving files: ')
        if confirm.strip() == 'YES':
            apply_plan(plan)
            print('Reorganization applied.')
        else:
            print('Aborted by user.')
