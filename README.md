# NextTrackAssist

NextTrackAssist は、DJの次曲選択を支援するスコアリング型アプリケーションです。

DJの選曲は経験や感覚に依存する部分が大きく、  
BPM・Key・Energy の流れが崩れるとセット全体の一体感が失われます。

NextTrackAssist は以下の3要素を数値化し、次曲候補を提示することで  
DJセットの流れを定量的にサポートします。

- BPM
- Camelot Key
- Energy

---

# Quick Start

```
docker-compose up --build
```

- ブラウザで `http://localhost:8000/login` を開く
- `Register` でアカウント作成（パスワード8文字以上）
- `Add Track` から2曲以上登録
- Track詳細の `Recommend Next Track` で次曲候補を確認

---

# Features

- 楽曲登録 / 編集 / 削除
- BPM / Camelot Key / Energy に基づくスコアリング
- 次曲候補の提示
- ユーザー登録 / ログイン / ログアウト
- login_required による認証制御
- Service Layer に分離したスコアロジック
- scoreモジュールの単体テスト

---

# Scoring Logic

NextTrackAssist では以下の3軸で次曲候補を評価します。

| 要素 | 説明 |
|---|---|
| BPM | テンポ差 |
| Camelot Key | ハーモニックミキシング |
| Energy | 曲の盛り上がり |

重みは以下の通りです。

```
BPM    : 0.7
Energy : 0.2
Key    : 0.1
```

### BPM
テンポ差はミックスの違和感に直結するため、最も高い重みを設定しています。

### Camelot Key
Camelot Wheel の理論をもとに

- 完全一致
- 隣接キー
- 相対長短
- 非互換

を判定しています。

### Energy
楽曲の盛り上がりを 1〜10 の値で管理し、  
差分が小さいほど高く評価します。

---

# Tech Stack

## Backend

- Python
- Flask
- SQLAlchemy

## Database

- PostgreSQL

## Infrastructure

- Docker
- docker-compose
- Gunicorn

## Test

- pytest

---

# Architecture

本アプリでは責務分離を意識した構成を採用しています。

```
app
├ config.py
├ extensions.py
├ __init__.py
├ models
│   ├ track.py
│   └ user.py
├ routes
│   ├ auth.py
│   └ tracks.py
├ services
│   └ score.py
└ utils
    └ auth.py
```

### Route Layer

HTTPリクエストを処理し、画面遷移を担当します。

### Service Layer

スコアリングロジックを routes から分離し、  
ビジネスロジックを独立させています。

### Model Layer

SQLAlchemy モデルとして Track / User を定義しています。

---

# Database

tracks テーブル

| column | type |
|---|---|
| id | integer |
| title | string |
| artist | string |
| bpm | integer |
| key | string |
| energy | integer |

### Constraints

- BPM : 40〜250
- Energy : 1〜10
- Camelot Key 形式チェック

異常データの登録を防ぐため CHECK 制約を設定しています。

---

# Authentication

- ユーザー登録
- ログイン
- ログアウト
- session による認証管理
- login_required によるアクセス制御

---

# Test

score モジュールに対して単体テストを実装しています。

主なテスト対象

- BPM差分
- Camelot Key 判定
- Energy差分
- total_score

---

# Local Development

## Clone

```
git clone <repository>
cd NextTrackAssist
```

## Run with Docker

```
docker-compose up --build
```

---

# Future Improvements

- rekordbox CSV import
- セット最適化アルゴリズム
- ユーザーごとのトラック管理
- AWS EC2 へのデプロイ
- RDS への移行

---

# Motivation

DJとして活動する中で、次曲選択は経験や感覚に依存する部分が大きいと感じました。

NextTrackAssist はその判断を  
「BPM / Key / Energy」という3つの要素で定量化し、  
次曲候補を提示することでセット構築をサポートすることを目的としています。
