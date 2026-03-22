# NextTrackAssist

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![pytest](https://img.shields.io/badge/tested%20with-pytest-yellow?logo=pytest)

**NextTrackAssist** は、DJの次曲選択を支援するスコアリング型Webアプリケーションです。

DJの選曲は経験や感覚に依存する部分が大きく、BPM・Key・Energy の流れが崩れるとセット全体の一体感が失われます。  
NextTrackAssist はその判断を数値化し、次曲候補を定量的にサポートします。

> **Motivation:** DJとして活動する中で「次の曲どうする？」という判断をロジックで補えないかと思ったのが開発のきっかけです。  
> BPM / Key / Energy の3要素をスコアリングすることで、感覚だけに頼らない選曲をサポートします。

---

## Quick Start

```bash
git clone https://github.com/gizmo-lit-py/NextTrackAssist.git
cd NextTrackAssist
docker-compose up --build
```

ブラウザで `http://localhost:8000/login` を開いてください。

1. `Register` でアカウント作成（パスワード8文字以上）
2. `Add Track` から2曲以上登録
3. Track詳細の `Recommend Next Track` で次曲候補を確認

---

## Features

- 楽曲の登録 / 編集 / 削除
- BPM / Camelot Key / Energy に基づく次曲スコアリング
- 次曲候補の提示
- ユーザー登録 / ログイン / ログアウト
- `login_required` によるアクセス制御
- Service Layer に分離したスコアリングロジック
- pytest による score モジュールの単体テスト

---

## Tech Stack

| カテゴリ | 技術 |
|---|---|
| Backend | Python / Flask / SQLAlchemy |
| Database | PostgreSQL |
| Infrastructure | Docker / docker-compose / Gunicorn |
| Test | pytest |
| Frontend | HTML / Jinja2 |

---

## Architecture

責務分離を意識した構成を採用しています。

```
app/
├── config.py
├── extensions.py
├── __init__.py
├── models/
│   ├── track.py
│   └── user.py
├── routes/
│   ├── auth.py
│   └── tracks.py
├── services/
│   └── score.py       ← スコアリングロジックをRoute層から分離
└── utils/
    └── auth.py
```

- **Route Layer** — HTTPリクエストの処理と画面遷移
- **Service Layer** — スコアリングロジックをビジネスロジックとして独立管理
- **Model Layer** — SQLAlchemy モデルで Track / User を定義

---

## Scoring Logic

次曲候補を以下の3軸で評価し、重み付きスコアを算出します。

| 要素 | 重み | 説明 |
|---|---|---|
| BPM | 0.7 | テンポ差（ミックスの違和感に最も直結するため高重み） |
| Energy | 0.2 | 1〜10 の盛り上がり値の差分 |
| Camelot Key | 0.1 | ハーモニックミキシング理論に基づく互換性判定 |

**Key 判定の4段階：**
- 完全一致 / 隣接キー / 相対長短 / 非互換

---

## Database Schema

`tracks` テーブル

| カラム | 型 | 制約 |
|---|---|---|
| id | integer | PK |
| title | string | - |
| artist | string | - |
| bpm | integer | 40〜250 |
| key | string | Camelot Key 形式 |
| energy | integer | 1〜10 |

異常データの登録を防ぐため、BPM・Energy・Key 形式に CHECK 制約を設定しています。

---

## Authentication

- ユーザー登録 / ログイン / ログアウト
- session による認証管理
- `login_required` デコレータによるアクセス制御

---

## Test

score モジュールに対して単体テストを実装しています。

```bash
docker-compose run --rm app pytest
```

主なテスト対象：BPM差分 / Camelot Key判定 / Energy差分 / total_score

---

## Future Improvements

| 項目 | 背景・理由 |
|---|---|
| rekordbox CSV import | 手動入力を不要にし、実際のDJ環境に近づけるため |
| セット最適化アルゴリズム | 1曲ずつではなくセット全体を最適化するロジックへ拡張 |
| ユーザーごとのトラック管理 | 複数DJが同一環境を利用できるマルチユーザー対応 |
| AWS EC2 へのデプロイ | 実際の本番環境を想定したインフラ構築の学習も兼ねて |
| RDS への移行 | クラウドネイティブなDB構成への移行 |
