# BPM を Float 対応にして、推薦の除外しきい値を 10 → 6 に厳格化

## なぜ

実際に DJ セットを組むのに使ってて2点気になった：

- BPM が整数しか扱えない。rekordbox の書き出しは `128.5` みたいな小数が普通なのに、`int` キャストで情報が落ちてた。
- 「BPM 差 10 以上で除外」だと甘すぎ。**差 6 を超えた時点で繋ぐのがしんどい** ので、推薦に出てきてほしくない。

## 何をした

- `calc_bpm_score` を `int / float` 両対応にして、**差 > 6.0 で `None` を返す**ように変更（推薦対象外を明示）。
- `calc_total_score` も BPM 除外時は `None` を返す。`recommend` ルートと `set_generator` の貪欲法ループで `None` をフィルタ。
- `Track.bpm` を `Integer` → `Float` に変更し、**冪等な追加マイグレーション** (`002_bpm_float.py`) を新設。SQLite / PostgreSQL / MySQL それぞれの方言に対応。
- フォーム入力 (`step="0.1"`)、CSV インポート、API すべて float を素通しするように更新。

## テスト

境界値（差 6.0 はギリ通る／6.5 で除外）と float 入力のケースを追加。**全 132 件 PASS**。

## Breaking

- `calc_total_score` の返り値が `dict | None` に。
- 既存環境は `python scripts/migrate.py` を実行する必要あり。
