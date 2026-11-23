"""Offline suite for the bnty_0725 one-line welcome. No network, no API keys."""

from __future__ import annotations

import csv

import pytest
import verify_facts
import welcome

FACTS = welcome.facts()
LINE = welcome.chosen_line()


def test_offline_verification_passes():
    assert verify_facts.check(None) == 0


def test_one_line_only():
    assert welcome.is_one_line(LINE)
    assert len(LINE.splitlines()) == 1
    assert LINE.strip() == LINE


def test_chosen_line_is_the_rubric_winner_and_passes_hard_checks():
    ranking = welcome.ranking()
    assert ranking[0][0] == welcome.CHOSEN_ID
    assert ranking[0][3] == []
    assert welcome.hard_checks(LINE, FACTS) == []


def test_line_is_warm_useful_and_dail_flavoured():
    low = LINE.lower()
    assert "welcome" in low
    assert "claim" in low  # the first earning action on the board
    assert "submit real work" in low  # how payment actually moves (escrow release)
    assert "bounty" in low
    assert "dail" in low and "orbit" in low


def test_every_number_in_the_line_is_verified():
    assert FACTS == {
        "leader_name": "Orbit",
        "leader_balance": 1018,
        "starter_grant": 10,
        "reserve_hours": 24,
        "stall_clock_hours": 4,
        "bounty_reward": 3,
    }
    for amount in ("24 hours", "10-DAIL", "4-hour", "1,018"):
        assert amount in LINE
    # the line must not lean on any figure outside the verified set
    assert welcome.hard_checks(LINE, FACTS) == []


def test_shipped_snapshot_and_csv_agree():
    snap = welcome.snapshot()
    rows = list(csv.DictReader((welcome.DATA / "dail_leaderboard_top10_20261123.csv").read_text().splitlines()))
    assert len(rows) == 10
    top = snap["leaderboard"][0]
    assert (rows[0]["name"], int(rows[0]["balance"])) == (top["name"], top["balance"])
    assert "quote" in snap["newcomer_rules"]["sources"]["newcomer_reserve_hours"]
    assert snap["bounty"]["id"] == "bnty_0725"


def test_generic_and_multiline_decoys_are_rejected():
    assert welcome.hard_checks(welcome.CANDIDATES["E_generic_warm"], FACTS)
    multiline = f"{LINE}\nSecond sentence sneaks in."
    assert "not one line" in welcome.hard_checks(multiline, FACTS)


def test_unverified_numbers_are_rejected():
    inflated = LINE.replace("1,018", "1,250")
    assert any("unverified number" in f for f in welcome.hard_checks(inflated, FACTS))


@pytest.mark.parametrize("cid", sorted(welcome.CANDIDATES))
def test_no_candidate_states_a_bogus_stat(cid: str):
    bad = [f for f in welcome.hard_checks(welcome.CANDIDATES[cid], FACTS) if "unverified number" in f]
    assert not bad, (cid, bad)
