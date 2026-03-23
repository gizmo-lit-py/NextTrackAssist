# NextTrackAssist

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![pytest](https://img.shields.io/badge/tested%20with-pytest-yellow?logo=pytest)

**NextTrackAssist** は、DJの次曲選択を支援するスコアリング型Webアプリケーションです。

DJの選曲は経験や感覚に依存する部分が大きく、BPM・Key・Energy の流れが崩れるとセット全体の一体感が失われます。
NextTrackAssist はその判断を数値化し、次曲候補を定量的にスコアリングして提示します。

> **Motivation:** DJとして活動する中で「次の曲どうする？」という判断をロジックで補えないかと思ったのが開発のきっかけです。
> BPM / Key / Energy の3要素をスコアリングすることで、感覚だけに頼らない選曲をサポートします。

---

## 目次

- [機能一覧](#機能一覧)
- [推薦ロジック](#推薦ロジック)
- [技術スタック](#技術スタック)
- [DB設計](#db設計)
- [ディレクトリ構成](#ディレクトリ構成)
- [セットアップ（Docker）](#セットアップdocker)
- [セットアップ（ローカル）](#セットアップローカル)
- [テスト実行](#テスト実行)
- [今後の展望](#今後の展望)

---

## 機能一覧

| 機能 | 説明 |
|------|------|
| ユーザー登録 / ログイン | メールアドレス + パスワード認証（セッション管理） |
| トラック一覧 | ログインユーザーの登録曲を一覧表示 |
| トラック登録 | BPM・Key（Camelot形式）・Energy を含む曲情報を登録 |
| トラック編集 / 削除 | 自分のトラックのみ操作可能（所有権チェック済み） |
| 次曲推薦 | 選択した曲を基準に、相性スコア順で上位10曲を提示 |
| 推薦理由の表示 | BPM / Key / Energy それぞれの評価理由を日本語で表示 |

---

## 推薦ロジック

推薦スコアは3つの指標を **加重平均** で算出します。

```
総合スコア = BPMスコア × 0.70 + Energyスコア × 0.20 + Keyスコア × 0.10
```

**BPM を最優先（weight: 0.70）** としているのは、DJミックスにおいてテンポのズレが最も致命的だからです。

### BPMスコア（weight: 0.70）

| BPM差分 | スコア | 評価 |
|---------|--------|------|
| 0〜2    | 100    | ほぼ一致 → ロングミックス向き |
| 3       | 90     | 許容範囲 → 軽いピッチ調整で対応可 |
| 4       | 80     | 〃 |
| 5       | 70     | 〃 |
| 6       | 60     | やや離れている → ブレイク・カットイン推奨 |
| 7       | 40     | 〃 |
| 8       | 20     | 〃 |
| 9       | 5      | 大きくズレている → テンポチェンジ向き |
| 10+     | 0      | 〃 |

### Keyスコア（weight: 0.10） ― Camelot Wheel 準拠

| 関係 | スコア | 例 |
|------|--------|----|
| 完全一致 | 100 | 8A → 8A |
| 隣接・同Letter | 95 | 8A → 9A（循環: 12A → 1A） |
| 同Number・相対調 | 90 | 8A → 8B |
| 隣接・異Letter | 80 | 8A → 9B |
| 非関連 | 30 | それ以外 |

### Energyスコア（weight: 0.20）

| Energy差分 | スコア |
|------------|--------|
| 0 | 100 |
| 1 | 95 |
| 2 | 85 |
| 3 | 70 |
| 4 | 50 |
| 5 | 30 |
| 6+ | 10 |

---

## 技術スタック

| カテゴリ | 技術 |
|----------|------|
| 言語 | Python 3.11 |
| Webフレームワーク | Flask 3.x（App Factory + Blueprint） |
| ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL 15 |
| 認証 | Flask セッション + Werkzeug パスワードハッシュ |
| セキュリティ | Flask-WTF（CSRF保護） |
| コンテナ | Docker / Docker Compose |
| Webサーバー | Gunicorn + Nginx（リバースプロキシ） |
| テスト | pytest（SQLite インメモリDB） |
| クラウド | AWS EC2（デプロイ予定） |



---

## DB設計

### ER図（概念）

```
users
├── id          INTEGER  PK
├── email       VARCHAR(255)  UNIQUE / INDEX
├── password_hash VARCHAR(255)
└── created_at  TIMESTAMPTZ

tracks
├── id          INTEGER  PK
├── user_id     INTEGER  FK → users.id  (CASCADE DELETE) / INDEX
├── title       VARCHAR(255)
├── artist      VARCHAR(255)
├── bpm         INTEGER  CHECK(40 <= bpm <= 250)
├── key         VARCHAR(3)   Camelot形式 例: 8A, 11B
└── energy      INTEGER  CHECK(1 <= energy <= 10)
```

### 制約の設計意図

- `bpm BETWEEN 40 AND 250`：実際の楽曲のBPM帯をカバーする現実的な範囲
- `energy BETWEEN 1 AND 10`：DJツールの一般的なエネルギースケールに合わせた設計
- `key` はCamelot記法（1A〜12B）に統一：Mixkey / Rekordbox との互換性を意識
- `CASCADE DELETE`：ユーザー削除時にトラックも連動削除し、孤立レコードを防ぐ

---

## ディレクトリ構成

```
NextTrackAssist/
├── app/
│   ├── __init__.py          # App Factory・エラーハンドラー
│   ├── config.py            # 設定（SECRET_KEY, DATABASE_URL）
│   ├── extensions.py        # SQLAlchemy エンジン・セッション定義
│   ├── models/
│   │   ├── user.py          # User モデル
│   │   └── track.py         # Track モデル（DB制約含む）
│   ├── routes/
│   │   ├── auth.py          # 認証ルート（register / login / logout）
│   │   └── tracks.py        # トラック CRUD + 推薦ルート
│   ├── services/
│   │   └── score.py         # 推薦スコアリングロジック（ドメイン層）
│   └── utils/
│       └── auth.py          # @login_required デコレータ
├── templates/
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── tracks/
│   │   ├── index.html
│   │   ├── new.html
│   │   ├── detail.html
│   │   ├── edit.html
│   │   └── recommend.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
├── migrations/
│   └── 001_initial.py       # 初回テーブル作成マイグレーション
├── scripts/
│   ├── migrate.py           # Docker起動時マイグレーション実行スクリプト
│   └── init_db.py           # DB接続確認スクリプト
├── tests/
│   ├── conftest.py          # pytest フィクスチャ（SQLite インメモリ）
│   ├── test_app.py          # アプリ全体・データ分離テスト
│   ├── test_auth.py         # 認証テスト
│   ├── test_tracks.py       # トラック CRUD・推薦テスト
│   └── test_score.py        # スコアリングロジック単体テスト
├── nginx/
│   └── nginx.conf           # Nginx リバースプロキシ設定
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

### 設計上の意図

- **App Factory パターン**（`create_app()`）：テスト時に異なる設定でアプリを生成可能
- **Blueprint 分離**（`auth_bp` / `tracks_bp`）：責務ごとにルートを整理
- **Service 層**（`services/score.py`）：推薦ロジックをルートから分離し、単体テスト可能に
- **`@login_required` デコレータ**：`g.current_user` にユーザーを格納し、各ルートで再取得不要
- **`_find_user_track()`**：`track_id AND user_id` の二重フィルタで所有権を担保

---

## セットアップ（Docker）

```bash
git clone https://github.com/your-username/NextTrackAssist.git
cd NextTrackAssist

# 起動（DB作成 + マイグレーション + サーバー起動まで自動）
docker-compose up --build
```

ブラウザで `http://localhost` にアクセスしてください。

### 環境変数

| 変数 | 説明 | デフォルト（dev） |
|------|------|------------------|
| `SECRET_KEY` | Flask セッション暗号化キー | `dev-secret-key`（**本番では必ず変更**） |
| `DATABASE_URL` | PostgreSQL 接続URL | `docker-compose.yml` 内で設定済み |
| `WTF_CSRF_ENABLED` | CSRF保護の有効/無効 | `True`（テスト時のみ `False`） |

---

## セットアップ（ローカル）

```bash
# 1. 仮想環境の作成・有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. 環境変数の設定（.envファイルを作成）
cp .env.example .env
# .env の DATABASE_URL と SECRET_KEY を編集

# 4. DB作成（PostgreSQL が起動済みであること）
python scripts/migrate.py

# 5. 開発サーバー起動
flask --app "app:create_app()" run
```

---

## テスト実行

テストは SQLite インメモリDBを使用するため、PostgreSQL の起動は不要です。

```bash
pytest tests/ -v
```

```
tests/test_app.py     ...   # データ分離・スコープテスト
tests/test_auth.py    ......  # 認証テスト
tests/test_score.py   ...............  # スコアリングロジック単体テスト
tests/test_tracks.py  ..............  # CRUD・推薦・バリデーションテスト
```

---

## 今後の展望

- [ ] UI改善（CSSフレームワーク導入）
- [ ] ページネーション（トラック一覧・推薦結果）
- [ ] `genre` カラムの追加
- [ ] AWS EC2 への本番デプロイ
- [ ] GitHub Actions による CI/CD
- [ ] API エンドポイント（JSON レスポンス版）の追加


## 開発メモ

本プロジェクトの一部はAIアシスタント（Claude）を活用してリファクタリングを行いました。
ロジックの設計・テスト設計・コードレビューの観点出しに使用しています。