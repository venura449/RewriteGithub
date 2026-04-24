#!/usr/bin/env python3
"""
====================================================
  Git Auto-Commit Tool  —  Educational Use Only
====================================================
Reads config.json and automatically commits random
chunks of a project to GitHub over a simulated
time range, with random authors and commit times.

Usage:
  python auto_commit.py              # uses config.json in same folder
  python auto_commit.py my_cfg.json  # custom config path
"""

import os
import sys
import json
import random
import fnmatch
import subprocess
import shutil
import string
from datetime import datetime, timedelta
from pathlib import Path


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(cmd: list, cwd: str, env: dict = None, check: bool = True, input_text: str = None):
    """Run a subprocess command and return its output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        input=input_text,
        capture_output=True,
        text=True
    )
    if check and result.returncode != 0:
        print(f"  [ERROR] Command failed: {' '.join(cmd)}")
        print(f"  {result.stderr.strip()}")
        raise SystemExit(1)
    return result


def git_cmd(project_dir: str, *args: str) -> list:
    """
    Build a git command that trusts the target repository even when it is
    owned by a different Windows user account.
    """
    safe_dir = Path(project_dir).as_posix()
    return ["git", "-c", f"safe.directory={safe_dir}", *args]


def should_ignore(path: str, patterns: list) -> bool:
    name = os.path.basename(path)
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
        if pat in path.replace("\\", "/"):
            return True
    return False


def collect_files(project_dir: str, ignore_patterns: list) -> list:
    """Recursively collect all files, excluding ignored paths."""
    all_files = []
    for root, dirs, files in os.walk(project_dir):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs
                   if not should_ignore(os.path.join(root, d), ignore_patterns)]
        for f in files:
            full_path = os.path.join(root, f)
            if not should_ignore(full_path, ignore_patterns):
                rel_path = os.path.relpath(full_path, project_dir).replace("\\", "/")
                all_files.append(rel_path)
    return all_files


def load_gitignore_patterns(project_dir: str) -> list:
    """
    Load simple ignore entries from the repo's .gitignore so local scanning
    matches the repository's own ignore rules.
    """
    gitignore_path = os.path.join(project_dir, ".gitignore")
    if not os.path.isfile(gitignore_path):
        return []

    patterns = []
    with open(gitignore_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            patterns.append(line)
    return patterns


def generate_schedule(cfg: dict) -> list:
    """
    Generate a list of (datetime, author) tuples spread randomly
    across the configured date range.
    """
    sched_cfg = cfg["schedule"]
    start = datetime.strptime(sched_cfg["start_date"], "%Y-%m-%d")
    end   = datetime.strptime(sched_cfg["end_date"],   "%Y-%m-%d")
    members = cfg["github"]["members"]

    commits_per_day_min = sched_cfg.get("commits_per_day_min", 1)
    commits_per_day_max = sched_cfg.get("commits_per_day_max", 3)
    hour_start = sched_cfg.get("active_hours_start", 9)
    hour_end   = sched_cfg.get("active_hours_end", 22)

    schedule = []
    current = start
    while current <= end:
        n_commits = random.randint(commits_per_day_min, commits_per_day_max)
        for _ in range(n_commits):
            hour   = random.randint(hour_start, hour_end - 1)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts = current.replace(hour=hour, minute=minute, second=second)
            author = random.choice(members)
            schedule.append((ts, author))
        current += timedelta(days=1)

    schedule.sort(key=lambda x: x[0])
    return schedule


def pick_commit_message(template: str, files: list) -> str:
    """Fill a message template with a random filename from the batch."""
    sample = random.choice(files)
    basename = os.path.basename(sample)
    return template.replace("{filename}", basename)


def git_date_format(dt: datetime) -> str:
    """Format datetime as Git author/committer date string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def slugify_branch_part(value: str) -> str:
    """Convert a string into a Git branch-friendly slug."""
    safe = []
    for ch in value.lower():
        if ch.isalnum():
            safe.append(ch)
        elif safe and safe[-1] != "-":
            safe.append("-")
    slug = "".join(safe).strip("-")
    return slug or "branch"


def random_branch_name(author: dict, timestamp: datetime, used: set) -> str:
    """
    Create a short-lived branch name with a conventional prefix and a random
    suffix so each batch gets a distinct branch.
    """
    prefixes = ["feature", "fix", "chore", "refactor", "hotfix", "experiment"]
    prefix = random.choice(prefixes)
    author_part = slugify_branch_part(author["name"])
    date_part = timestamp.strftime("%Y%m%d")
    alphabet = string.ascii_lowercase + string.digits

    while True:
        suffix = "".join(random.choice(alphabet) for _ in range(4))
        branch = f"{prefix}/{author_part}-{date_part}-{suffix}"
        if branch not in used:
            used.add(branch)
            return branch


# ─────────────────────────────────────────────
#  Core logic
# ─────────────────────────────────────────────

def init_repo(project_dir: str, repo_url: str, branch: str):
    """Init git repo, add remote, set up initial state."""
    git_dir = os.path.join(project_dir, ".git")

    if not os.path.isdir(git_dir):
        print("  Initialising git repository...")
        run(git_cmd(project_dir, "init"), cwd=project_dir)
        run(git_cmd(project_dir, "checkout", "-b", branch), cwd=project_dir)
    else:
        print("  Git repo already exists, continuing.")
        run(git_cmd(project_dir, "checkout", branch), cwd=project_dir)

    # Check if remote exists
    result = run(git_cmd(project_dir, "remote"), cwd=project_dir, check=False)
    if "origin" not in result.stdout:
        print(f"  Adding remote: {repo_url}")
        run(git_cmd(project_dir, "remote", "add", "origin", repo_url), cwd=project_dir)
    else:
        print("  Remote 'origin' already configured.")


def do_commit(
    project_dir: str,
    files_to_add: list,
    author: dict,
    timestamp: datetime,
    message: str,
    commit_number: int,
    total_commits: int
):
    """Create the commit on the current branch with a fake timestamp."""
    env = os.environ.copy()
    date_str   = git_date_format(timestamp)

    env["GIT_AUTHOR_NAME"]     = author["name"]
    env["GIT_AUTHOR_EMAIL"]    = author["email"]
    env["GIT_AUTHOR_DATE"]     = date_str
    env["GIT_COMMITTER_NAME"]  = author["name"]
    env["GIT_COMMITTER_EMAIL"] = author["email"]
    env["GIT_COMMITTER_DATE"]  = date_str

    # Commit
    run(
        git_cmd(project_dir, "commit", "-m", message, "--allow-empty-message", "--allow-empty"),
        cwd=project_dir,
        env=env
    )

    print(
        f"  [{commit_number}/{total_commits}] "
        f"{timestamp.strftime('%Y-%m-%d %H:%M')}  "
        f"{author['name']:20s}  \"{message}\"  "
        f"({len(files_to_add)} file{'s' if len(files_to_add) != 1 else ''})"
    )


def merge_branch(
    project_dir: str,
    base_branch: str,
    topic_branch: str,
    author: dict,
    timestamp: datetime
):
    """Merge a short-lived branch back into the base branch."""
    env = os.environ.copy()
    date_str = git_date_format(timestamp)

    env["GIT_AUTHOR_NAME"]     = author["name"]
    env["GIT_AUTHOR_EMAIL"]    = author["email"]
    env["GIT_AUTHOR_DATE"]     = date_str
    env["GIT_COMMITTER_NAME"]  = author["name"]
    env["GIT_COMMITTER_EMAIL"] = author["email"]
    env["GIT_COMMITTER_DATE"]  = date_str

    run(git_cmd(project_dir, "checkout", base_branch), cwd=project_dir, env=env)
    run(
        git_cmd(
            project_dir,
            "merge",
            "--no-ff",
            "-m",
            f"Merge branch '{topic_branch}'",
            topic_branch
        ),
        cwd=project_dir,
        env=env
    )
    run(git_cmd(project_dir, "branch", "-d", topic_branch), cwd=project_dir, env=env, check=False)


def stage_files(project_dir: str, files_to_add: list, env: dict):
    """Stage the files for the current branch."""
    for f in files_to_add:
        run(git_cmd(project_dir, "add", f), cwd=project_dir, env=env)


def push_all(project_dir: str, branch: str):
    print("\n  Pushing all commits to GitHub...")
    run(git_cmd(project_dir, "push", "-u", "origin", branch, "--force"), cwd=project_dir)
    print("  Done! All commits pushed.")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    if not os.path.isfile(config_path):
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)

    print("\n" + "=" * 56)
    print("   Git Auto-Commit Tool  —  Educational Use Only")
    print("=" * 56)

    cfg = load_config(config_path)

    project_dir = os.path.abspath(cfg["project_dir"])
    repo_url    = cfg["github"]["repo_url"]
    branch      = cfg["github"].get("branch", "main")
    ignore_pats = cfg.get("ignore", [])
    commit_cfg  = cfg.get("commit", {})
    messages    = commit_cfg.get("messages", ["Update files"])
    files_min   = commit_cfg.get("files_per_commit_min", 1)
    files_max   = commit_cfg.get("files_per_commit_max", 5)
    repo_ignore = load_gitignore_patterns(project_dir)
    if repo_ignore:
        ignore_pats = list(dict.fromkeys(ignore_pats + repo_ignore))

    if not os.path.isdir(project_dir):
        print(f"[ERROR] Project directory not found: {project_dir}")
        sys.exit(1)

    print(f"\n  Project   : {project_dir}")
    print(f"  Repo URL  : {repo_url}")
    print(f"  Branch    : {branch}")
    print(f"  Authors   : {', '.join(m['name'] for m in cfg['github']['members'])}")
    print(f"  Period    : {cfg['schedule']['start_date']} → {cfg['schedule']['end_date']}")

    # Step 1: collect all files
    print("\n  Scanning project files...")
    all_files = collect_files(project_dir, ignore_pats)
    if not all_files:
        print("[ERROR] No files found in project directory.")
        sys.exit(1)

    print(f"  Found {len(all_files)} files.")

    # Step 2: generate schedule
    schedule = generate_schedule(cfg)
    print(f"  Generated {len(schedule)} scheduled commits.")

    # Step 3: init repo
    print("\n  Setting up git repository...")
    init_repo(project_dir, repo_url, branch)

    # Step 4: distribute files across commits
    # Shuffle files so each commit gets a random slice
    files_pool = all_files.copy()
    random.shuffle(files_pool)

    # We'll spread the files across all commits so every file is committed exactly once
    # Build batches first
    batches = []
    idx = 0
    for i, (ts, author) in enumerate(schedule):
        if idx >= len(files_pool):
            break  # all files committed
        # how many files this commit takes
        remaining = len(files_pool) - idx
        slots_left = len(schedule) - i
        # Don't exceed remaining files or config max, but ensure we finish
        max_take = min(files_max, remaining)
        if slots_left == 1:
            max_take = remaining  # dump all remaining on last slot
        n = random.randint(min(files_min, max_take), max_take)
        batch = files_pool[idx: idx + n]
        idx += n
        batches.append((ts, author, batch))

    # If there are more schedule slots than needed, they're skipped
    total = len(batches)
    print(f"  Distributing {len(all_files)} files across {total} commits.\n")

    # Step 5: perform commits
    used_branch_names = set()
    for i, (ts, author, batch) in enumerate(batches, 1):
        msg_template = random.choice(messages)
        msg = pick_commit_message(msg_template, batch)
        topic_branch = random_branch_name(author, ts, used_branch_names)
        print(f"  Creating branch: {topic_branch}")

        env = os.environ.copy()
        date_str = git_date_format(ts)
        env["GIT_AUTHOR_NAME"]     = author["name"]
        env["GIT_AUTHOR_EMAIL"]    = author["email"]
        env["GIT_AUTHOR_DATE"]     = date_str
        env["GIT_COMMITTER_NAME"]  = author["name"]
        env["GIT_COMMITTER_EMAIL"] = author["email"]
        env["GIT_COMMITTER_DATE"]  = date_str

        run(git_cmd(project_dir, "checkout", "-b", topic_branch, branch), cwd=project_dir, env=env)
        stage_files(project_dir, batch, env)
        do_commit(
            project_dir=project_dir,
            files_to_add=batch,
            author=author,
            timestamp=ts,
            message=msg,
            commit_number=i,
            total_commits=total
        )

        merge_author = random.choice(cfg["github"]["members"])
        merge_timestamp = ts + timedelta(minutes=1)
        merge_branch(
            project_dir=project_dir,
            base_branch=branch,
            topic_branch=topic_branch,
            author=merge_author,
            timestamp=merge_timestamp
        )

    # Step 6: push
    push_all(project_dir, branch)

    print("\n" + "=" * 56)
    print("   All done! Your project is on GitHub.")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    main()
