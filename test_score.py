from score import calc_key_score, calc_bpm_score, calc_energy_score, calc_total_score

def run_tests():

    # Keyテスト
    assert calc_key_score("8A", "8A")[0] == 100
    assert calc_key_score("8A", "7A")[0] == 90
    assert calc_key_score("8A", "8B")[0] == 85
    assert calc_key_score("8A", "9B")[0] == 40

    # BPMテスト
    assert calc_bpm_score(120, 121)[0] == 100
    assert calc_bpm_score(120, 124)[0] == 80
    assert calc_bpm_score(120, 130)[0] == 50
    assert calc_bpm_score(120, 150)[0] == 20

    # Energyテスト
    assert calc_energy_score(5, 6)[0] == 100
    assert calc_energy_score(5, 7)[0] == 70
    assert calc_energy_score(5, 9)[0] == 40

    # Totalテスト
    total = calc_total_score(100, 100, 100)
    assert total == 100

    print("全テスト通過")

if __name__ == "__main__":
    run_tests()
