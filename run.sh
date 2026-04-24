#!/bin/bash
# ================================================
#   Git Auto-Commit Tool  — Mac/Linux Launcher
# ================================================

set -e

echo ""
echo "================================================"
echo "  Git Auto-Commit Tool  |  Educational Use"
echo "================================================"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3 from https://python.org"
    exit 1
fi

# Check Git
if ! command -v git &>/dev/null; then
    echo "[ERROR] git not found. Install Git from https://git-scm.com"
    exit 1
fi

CONFIG="${1:-config.json}"

if [ ! -f "$CONFIG" ]; then
    echo "[ERROR] Config file not found: $CONFIG"
    echo ""
    echo "Create a config.json file next to this script."
    exit 1
fi

echo "Using config: $CONFIG"
echo ""

python3 auto_commit.py "$CONFIG"
