from app.services.score import (
    calc_bpm_score,
    calc_key_score,
    calc_energy_score,
    calc_total_score
)


def test_bpm_exact():

    score, diff = calc_bpm_score(128, 128)

    assert score == 100


def test_bpm_small_diff():

    score, diff = calc_bpm_score(128, 130)

    assert score >= 90


def test_key_exact():

    score = calc_key_score("8A", "8A")

    assert score == 100


def test_key_neighbor():

    score = calc_key_score("8A", "9A")

    assert score >= 80


def test_energy_small_diff():

    score = calc_energy_score(5, 6)

    assert score >= 80


def test_total_score():

    base = {
        "bpm": 128,
        "key": "8A",
        "energy": 6
    }

    target = {
        "bpm": 128,
        "key": "8A",
        "energy": 6
    }

    result = calc_total_score(base, target)

    assert result["total_score"] >= 90