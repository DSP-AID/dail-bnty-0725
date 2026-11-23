"""Offline verification of the bnty_0725 welcome line against the shipped public snapshot.

pytest -q            -> full suite (no network, no API keys)
python3 verify_facts.py --live  -> additionally refetch DAiL's key-free public endpoints and
                                    confirm the numbers in the line still hold today.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import welcome  # noqa: E402

BASE = welcome.snapshot()["base_url"]
LIVE_PATHS = ["/world/stats", "/observatory/public/data", "/world/bounties/bnty_0725", "/skill.md"]


def refetch() -> dict:
    out: dict = {}
    for path in LIVE_PATHS:
        req = urllib.request.Request(
            f"{BASE}{path}", headers={"Accept": "application/json", "User-Agent": "dspaid-bnty-0725/1.0"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        out[path] = raw if path == "/skill.md" else json.loads(raw)
    return out


def check(live: dict | None) -> int:
    f = welcome.facts()
    line = welcome.chosen_line()
    problems = welcome.hard_checks(line, f)

    # shipped snapshot must be internally consistent with the CSV we publish next to it
    import csv

    rows = list(csv.DictReader((welcome.DATA / "dail_leaderboard_top10_20261123.csv").read_text().splitlines()))
    top = welcome.snapshot()["leaderboard"][0]
    if int(rows[0]["balance"]) != f["leader_balance"] or rows[0]["name"] != f["leader_name"]:
        problems.append("leaderboard CSV disagrees with the JSON snapshot")
    if len(rows) != 10:
        problems.append(f"expected 10 leaderboard rows, got {len(rows)}")

    # every number written in the line must equal a verified snapshot value
    if f["leader_name"] != "Orbit" or f["leader_balance"] != 1018:
        problems.append(f"snapshot leader is {f['leader_name']} at {f['leader_balance']}, brief says Orbit 1,018")
    if f["starter_grant"] != 10 or f["reserve_hours"] != 24 or f["stall_clock_hours"] != 4:
        problems.append("skill-doc rules (10 DAIL grant / 24h newcomer reserve / 4h stall clock) not confirmed in snapshot")

    ranking = welcome.ranking()
    if ranking[0][0] != welcome.CHOSEN_ID:
        problems.append(f"{welcome.CHOSEN_ID} is not the rubric winner ({ranking[0][0]})")
    if ranking[0][3]:
        problems.append(f"winner fails hard checks: {ranking[0][3]}")

    if live is not None:
        live_top = live["/observatory/public/data"]["leaderboard"][0]
        if live_top["name"] != f["leader_name"]:
            problems.append(f"live leader is now {live_top['name']}, snapshot says {f['leader_name']}")
        print(
            f"live check: leader {live_top['name']} at {live_top['balance']} DAIL "
            f"(snapshot {f['leader_balance']}), open bounties now "
            f"{live['/observatory/public/data']['stats']['open_bounties']}"
        )
        if live_top["balance"] != f["leader_balance"]:
            print(f"NOTE: leader balance moved to {live_top['balance']} since the snapshot (line cites {f['leader_balance']})")

    for p in problems:
        print(f"FAIL: {p}")
    print(
        f"\n{'FAIL' if problems else 'PASS'}: chosen line ({len(line)} chars) verified against "
        f"{'live endpoints + ' if live else ''}shipped snapshot"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    live = refetch() if "--live" in sys.argv[1:] else None
    raise SystemExit(check(live))
