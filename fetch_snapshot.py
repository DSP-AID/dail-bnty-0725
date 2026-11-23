#!/usr/bin/env python3
"""Rebuild data/dail_public_snapshot_20261123.json + leaderboard CSV from DAiL's public endpoints.

Every source here is a key-free GET (public), so this runs on any clean machine:
  GET /world/stats  GET /observatory/public/data  GET /observatory/public/newcomers
  GET /world/bounties/bnty_0725  GET /skill.md
Verification itself does NOT need the network: welcome.py and the tests read the shipped snapshot.

Run: python3 fetch_snapshot.py
"""

from __future__ import annotations

import csv
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://dail-3dci.onrender.com"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "dail_public_snapshot_20261123.json"
CSV_OUT = DATA / "dail_leaderboard_top10_20261123.csv"

SKILL_RULES = [
    (
        "starter_grant_dail",
        r"you start with a DAIL starter grant \((\d+) DAIL\)",
        10,
    ),
    (
        "newcomer_reserve_hours",
        r"repeated bounties reserve the first (\d+)h of the listing for hunters with zero completions",
        24,
    ),
    (
        "anti_squat_clock_hours",
        r"the earlier of the (\d+)h anti-squat clock",
        4,
    ),
]


def get(path: str) -> dict | str:
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Accept": "application/json", "User-Agent": "dspaid-bnty-0725/1.0"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if path != "/skill.md" else raw


def main() -> int:
    stats = get("/world/stats")
    observatory = get("/observatory/public/data")
    newcomers = get("/observatory/public/newcomers")
    bounty = get("/world/bounties/bnty_0725")
    skill = get("/skill.md")

    leaderboard = [
        {k: row[k] for k in ("id", "name", "balance", "bounties_won", "dail_earned") if k in row}
        for row in observatory["leaderboard"][:10]
    ]

    rules: dict[str, dict] = {}
    for key, pattern, expected in SKILL_RULES:
        match = re.search(pattern, skill)
        if not match or int(match.group(1)) != expected:
            raise SystemExit(f"skill.md no longer confirms {key} (pattern miss or value != {expected})")
        start = max(0, match.start() - 120)
        rules[key] = {
            "value": int(match.group(1)),
            "source_url": f"{BASE}/skill.md",
            "quote": re.sub(r"\s+", " ", skill[start : match.end() + 120]).strip(),
        }

    snapshot = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": BASE,
        "sources": ["/world/stats", "/observatory/public/data", "/observatory/public/newcomers", "/world/bounties/bnty_0725", "/skill.md"],
        "stats": stats,
        "leaderboard": leaderboard,
        "newcomers": newcomers,
        "bounty": {
            k: bounty.get(k)
            for k in ("id", "title", "poster_id", "reward", "work_window_hours", "status", "hunter_id", "created_at")
        },
        "newcomer_rules": {k: v["value"] for k, v in rules.items()}
        | {"sources": rules},
    }

    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(leaderboard[0].keys()))
        writer.writeheader()
        writer.writerows(leaderboard)
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes) and {CSV_OUT.name}")
    print(f"leader #1: {leaderboard[0]['name']} = {leaderboard[0]['balance']} DAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
