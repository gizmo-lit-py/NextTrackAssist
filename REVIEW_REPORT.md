# NextTrackAssist コードレビュー・現状分析レポート

**作成日:** 2026-03-24
**対象:** NextTrackAssist 全コードベース
**評価基準:** 未経験エンジニアの就活ポートフォリオ提出品質

---

## 1. 現状サマリー

全体として、Flask アプリとしての基本骨格はしっかり組まれている。App Factory パターン、Blueprint による分離、Service 層への推薦ロジック切り出し、`@login_required` デコレータによる認証制御など、「動くだけ」を超えた設計意識が見える。推薦スコアの重み配分（BPM 0.70 / Energy 0.20 / Key 0.10）も依頼通りに実装されており、DJ の実務感を反映した設計になっている。

ただし、**就活ポートフォリオとして提出するには未完成の箇所が複数ある**。特にテストの薄さ、README の不十分さ、マイグレーション周りの不整合、genre フィールドの未実装など、「レビューされたときにツッコまれる箇所」が残っている。

---

## 2. 実装済み機能（コード確認済み）

### 認証系
- ユーザー登録（`POST /register`）：メール + パスワード（8文字以上）、`werkzeug` によるハッシュ化
- ログイン（`POST /login`）：セッションベース認証、`session["user_id"]` 管理
- ログアウト（`GET /logout`）：セッション全クリア
- `@login_required` デコレータ：`g.current_user` へのユーザー格納

### トラック CRUD
- 一覧表示（`GET /`）：ログインユーザーのトラックのみ、ID降順
- 新規作成（`GET /tracks/new`, `POST /tracks`）：フォームバリデーション付き
- 詳細表示（`GET /tracks/<id>`）：所有権チェック付き
- 編集（`GET /tracks/<id>/edit`, `POST /tracks/<id>/update`）
- 削除（`POST /tracks/<id>/delete`）

### 推薦機能
- `GET /tracks/<id>/recommend`：基準曲に対する推薦候補を最大10件表示
- BPM スコア：差分 0〜10 の段階評価（0-2 で 100、10+ で 0）
- Key スコア：Camelot Wheel ベースの harmonic compatibility 判定（完全一致 100、隣接同Letter 95、同Number異Letter 90、隣接異Letter 80、その他 30）
- Energy スコア：差分 0〜6+ の段階評価
- 加重平均：BPM 0.70、Energy 0.20、Key 0.10（`DEFAULT_WEIGHTS` で定義）
- Transition Tip：BPM差分・Energy変化に基づく日本語アドバイス文

### データ分離
- `_find_user_track()` で `track_id` AND `user_id` の二重フィルタ
- 他ユーザーのトラックへのアクセスは 404 を返す

### インフラ
- Dockerfile（Python 3.11 + gunicorn）
- docker-compose.yml（PostgreSQL 15 + Flask + nginx）
- nginx リバースプロキシ設定
- pytest.ini + conftest.py + テスト 9 件

### DB 制約
- BPM：`CheckConstraint` で 40〜250
- Energy：`CheckConstraint` で 1〜10
- User.email：unique + index
- Track.user_id：ForeignKey with cascade delete

---

## 3. 未実装 / 不十分な箇所

### 3-1. 明確に未実装

| 項目 | 状態 | 備考 |
|------|------|------|
| `genre` カラム | **未実装** | 依頼書に「任意」とあるが、Track モデルに存在しない。ポートフォリオ的には「あるけど optional」の方が印象が良い |
| マイグレーションランナー | **欠落** | `docker-compose.yml` が `python scripts/migrate.py` を参照しているが、`scripts/migrate.py` が存在しない。`001_initial.py` はあるが実行手段がない |
| 推薦理由の詳細表示 | **不十分** | `transition_tip` は実装済みだが、BPM/Key/Energy 各スコアの「なぜこのスコアか」の理由文（「差分1 → ほぼ一致」等）が未実装。テンプレート上では `bpm_diff` と `total_score` は表示されるが、個別スコアの理由文は出ていない |
| ページネーション | **未実装** | トラック一覧・推薦結果ともにページネーションなし |
| CSRF 対策 | **未実装** | Flask-WTF 未使用、フォームに CSRF トークンなし |
| レート制限 | **未実装** | ログイン試行回数制限なし |
| パスワードリセット | **未実装** | 最低限の認証機能のみ |

### 3-2. 仮実装・不完全

| 項目 | 状態 | 備考 |
|------|------|------|
| テストファイル名 | **typo** | `tests/test_app,py`（カンマ）→ `test_app.py`（ドット）に修正必要。pytest の discovery には影響しない可能性があるが、レビューで確実に指摘される |
| テストカバレッジ | **薄い** | スコア計算 6 件 + アプリ 3 件 = 計 9 件のみ。CRUD 操作、バリデーション失敗ケース、エッジケースのテストがない |
| `SECRET_KEY` | **ハードコードのフォールバック** | `os.getenv("SECRET_KEY", "dev-secret-key")` — `.env` がないとデフォルト値が使われる。本番環境では重大なセキュリティリスク |
| `create_app` 内のテーブル自動作成 | **開発用コード残留** | `Base.metadata.create_all(bind=engine)` が本番でも毎回実行される。マイグレーションと矛盾する |
| README | **内容不十分** | 存在はするが、ポートフォリオとして見せるには情報が足りない可能性が高い（後述） |

---

## 4. 設計上の問題

### 4-1. セッション管理が手動すぎる

**現状：** 各ルートで毎回 `SessionLocal()` を作成し、`try/except/finally` で `db.close()` している。

```python
db = SessionLocal()
try:
    # ...
    db.commit()
except IntegrityError:
    db.rollback()
finally:
    db.close()
```

**問題点：**
- 全ルートに同じボイラープレートが繰り返されている
- `db.close()` の書き忘れリスク
- Flask の `@app.teardown_appcontext` や `scoped_session` を使っていない

**改善案：** リクエストスコープのセッション管理を導入する。`@app.teardown_appcontext` でセッションを自動クローズするか、ミドルウェアでラップする。

### 4-2. Blueprint の URL 設計に軽微な不統一

- `tracks_bp` の `url_prefix="/"` が設定されているため、トップページ（`/`）がトラック一覧になっている
- auth 系は `/login`, `/register`, `/logout` で prefix なし
- RESTful な統一感がもう少しほしい（例：`/tracks` にまとめる）

### 4-3. `_validate_track_form` と `_find_user_track` がルートファイル内のプライベート関数

**現状：** `routes/tracks.py` にバリデーションとクエリヘルパーが同居している。

**問題点：** 責務分離の観点で「ルーティング」と「バリデーション」が混在。テストもしにくい。

**改善案：**
- バリデーションは `app/validators/track.py` や `app/services/track_service.py` に切り出す
- DB アクセスヘルパーも service 層に移動する

### 4-4. エラーハンドリングが flash メッセージ頼り

**現状：** バリデーションエラーやDBエラーは全て `flash()` + リダイレクトで処理。

**問題点：**
- カスタムエラーページ（404, 500）が未定義
- API 的なエラーレスポンス（JSON）に対応していない
- `abort(404)` 時に Flask デフォルトのエラーページが出る

**改善案：** `@app.errorhandler(404)` と `@app.errorhandler(500)` でカスタムエラーテンプレートを追加。実装コストは低いが印象は大きく改善する。

### 4-5. テンプレートディレクトリの配置

**現状：** `templates/` がプロジェクトルート直下にあり、`app/__init__.py` でパス解決している。

```python
template_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../templates")
)
```

**問題点：** Flask の規約（`app/templates/`）から外れている。パス解決のハックが必要になっている。

**改善案：** `templates/` を `app/templates/` に移動すれば、パス解決コードが不要になる。

---

## 5. ポートフォリオとして弱い点

### 5-1. テストが圧倒的に足りない（最大の弱点）

スコア計算 6 件 + アプリ 3 件 = **計 9 件**。これは就活ポートフォリオとしては致命的に少ない。

**不足しているテスト：**
- CRUD 操作の正常系・異常系
- バリデーション失敗ケース（BPM 範囲外、Key 不正フォーマット等）
- 未ログイン状態でのアクセス制御
- 推薦ロジックのエッジケース（候補 0 件、全曲同一 BPM、等）
- Camelot Key の循環（12A → 1A の隣接判定）

**採用側の視点：** 「テストを書く習慣があるか」は未経験者の評価で重視される。9 件では「テスト書けます」と言うには弱い。最低でも 20〜30 件は欲しい。

### 5-2. README が就活ポートフォリオ品質ではない

README はプロジェクトの「顔」。採用担当が最初に見るファイル。以下が必要：

- プロジェクト概要と動機（DJ 経験とのつながり）
- 技術スタック一覧
- 推薦ロジックの概要説明（BPM 最重視の設計思想）
- スクリーンショット or GIF
- セットアップ手順（ローカル / Docker）
- テスト実行方法
- ER 図 or DB 設計
- ディレクトリ構成図
- 今後の展望

### 5-3. UI/UX が最小限すぎる

**現状：** `base.html` 内の `<style>` タグで最低限のスタイリング。レスポンシブ対応は不十分。

**採用側の視点：** バックエンド志望でも「見た目がひどいアプリ」はマイナス印象。最低限のCSSフレームワーク（Tailwind や Bootstrap）を入れるだけで大幅改善。

### 5-4. CSRF 対策がない

フォームに CSRF トークンが一切ない。Flask-WTF を使っていないため。セキュリティ意識を問われたときに説明できない。

### 5-5. 推薦理由の表示が不十分

依頼書にある「差分1 → ほぼ一致」「差分3 → 許容範囲」のような人間向けの理由文が未実装。`transition_tip` はあるが、各スコア（BPM / Key / Energy）の個別理由文がない。ここはドメイン知識を見せるチャンスなので、実装しないのは損。

### 5-6. デプロイの証拠がない

Docker + nginx + gunicorn の構成は整っているが、「実際に動いている URL」がないと「設定ファイルを書いただけでは？」と見られる可能性がある。AWS EC2 へのデプロイを完了し、URL を README に記載できるとベスト。

### 5-7. `genre` が存在しない

依頼書に「任意」とあるが、DJ アプリで genre がないのは不自然。nullable なカラムとして追加するだけで「実務を考慮している」印象になる。

---

## 6. 次にやるべき優先順位

以下、**ポートフォリオ評価への影響度**と**実装コスト**のバランスで並べる。

### Priority 1：今すぐ直すべき（評価直結 × 低コスト）

| # | タスク | 理由 | 工数目安 |
|---|--------|------|----------|
| 1 | テストファイル名の typo 修正 | `test_app,py` → `test_app.py`。1秒で直せるが、放置すると「雑」に見える | 1分 |
| 2 | カスタムエラーページ（404 / 500） | テンプレート 2 枚 + `errorhandler` 2 行。低コストで品質感が上がる | 30分 |
| 3 | `scripts/migrate.py` の作成 | docker-compose.yml が参照しているのに存在しない。起動時エラーの原因 | 30分 |
| 4 | CSRF 対策の導入 | `Flask-WTF` 導入 + フォームに `{{ csrf_token() }}`。セキュリティ意識を示せる | 1-2時間 |
| 5 | 推薦理由文の実装 | BPM / Key / Energy 各スコアに理由テキストを付与。ドメイン知識の見せ場 | 1-2時間 |

### Priority 2：早めに対応（評価直結 × 中コスト）

| # | タスク | 理由 | 工数目安 |
|---|--------|------|----------|
| 6 | テスト拡充（20件以上に） | CRUD正常系/異常系、バリデーション、推薦エッジケース、認証テスト | 3-4時間 |
| 7 | README の大幅強化 | スクショ、設計説明、セットアップ手順、推薦ロジック解説 | 2-3時間 |
| 8 | `genre` カラムの追加 | nullable で追加。フォーム・テンプレート・推薦表示に反映 | 1-2時間 |
| 9 | セッション管理のリファクタ | `@app.teardown_appcontext` でセッション自動管理。ボイラープレート除去 | 2-3時間 |
| 10 | バリデーションの service 層切り出し | `_validate_track_form` を `app/services/` に移動。テスタビリティ向上 | 1-2時間 |

### Priority 3：仕上げフェーズ（品質向上 × 中〜高コスト）

| # | タスク | 理由 | 工数目安 |
|---|--------|------|----------|
| 11 | UI の改善（CSS フレームワーク導入） | Bootstrap or Tailwind で見た目を整える | 3-5時間 |
| 12 | `templates/` を `app/templates/` に移動 | Flask 規約に合わせる。パス解決ハック除去 | 1時間 |
| 13 | ページネーション | トラック一覧、推薦結果 | 2-3時間 |
| 14 | AWS EC2 デプロイ完了 + URL 記載 | 「動いている証拠」が README にあると説得力が違う | 半日〜1日 |
| 15 | `SECRET_KEY` のフォールバック除去 | `.env.example` を用意し、本番で dev 値が使われない仕組みに | 30分 |

### Priority 4：余裕があれば（加点要素）

| # | タスク | 理由 | 工数目安 |
|---|--------|------|----------|
| 16 | CI/CD（GitHub Actions） | テスト自動実行。「開発プロセスを理解している」アピール | 2-3時間 |
| 17 | ログ出力の整備 | `logging` モジュール導入。本番運用意識 | 1-2時間 |
| 18 | API エンドポイント追加 | JSON レスポンス版の推薦 API。フロントエンド分離への拡張性 | 3-4時間 |
| 19 | Docker の multi-stage build | イメージサイズ削減。インフラ知識アピール | 1時間 |

---

## 7. 具体的な修正方針

### 7-1. 今すぐ直すべきもの

**テストファイル名修正：**
```bash
mv tests/test_app,py tests/test_app.py
```

**カスタムエラーページ：**
`app/__init__.py` に以下を追加し、`templates/errors/404.html` と `500.html` を作成。
```python
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500
```

**`scripts/migrate.py` 作成：**
```python
from app.extensions import engine, Base
from app.models.user import User
from app.models.track import Track

def migrate():
    Base.metadata.create_all(bind=engine)
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
```

**推薦理由文の実装例（`services/score.py` に追加）：**
```python
def bpm_reason(diff: int) -> str:
    if diff <= 2:
        return "ほぼ一致 — ロングミックス向き"
    elif diff <= 5:
        return "許容範囲 — 軽いピッチ調整で対応可"
    elif diff <= 8:
        return "やや離れている — カットインやブレイク推奨"
    else:
        return "大きくズレている — テンポチェンジ向き"
```

### 7-2. 後回しでいいもの

- ページネーション（曲数が少ないうちは不要だが、拡張性として言及できる）
- API エンドポイント（ポートフォリオの範囲では Web UI で十分）
- i18n 対応（日本語で統一されていれば問題なし）
- パスワードリセット（認証の基本ができていれば未実装でも許容）

### 7-3. ポートフォリオ評価に直結するもの

1. **テスト件数の拡充** — 最もインパクトが大きい。「テストを書ける人」と認識されるかどうかの分かれ目。
2. **README の充実** — 採用担当が最初に読む。ここが薄いと中身を見てもらえない。
3. **推薦理由文** — ドメイン知識×実装力を同時に示せる稀有なポイント。
4. **CSRF 対策** — セキュリティ意識を1行で示せる。

### 7-4. 実装コストが低いのに見栄えが良くなるもの

1. **カスタムエラーページ** — テンプレート 2 枚で「ちゃんとしてる」感が出る
2. **`.env.example` ファイル** — 環境変数の一覧を示すだけ。セットアップの親切さ
3. **`genre` カラム追加** — nullable で追加するだけ。DJ アプリとしての説得力が上がる
4. **Docker multi-stage build** — Dockerfile 数行の変更でイメージサイズ半減
5. **テストファイル名修正** — 1秒。でも放置は致命的

---

## 総合評価

**現時点の完成度：65〜70%（就活ポートフォリオ基準）**

良い点：
- App Factory + Blueprint の構成は適切
- 推薦ロジックが Service 層に分離されている
- BPM 最重視の重み設計が一貫している
- ユーザーデータ分離が正しく実装されている
- Docker / nginx / gunicorn の構成が揃っている
- テストが（少ないながらも）存在し、データ分離のテストまで書いている

足りない点：
- テストが 9 件は少なすぎる
- README がポートフォリオの顔として機能していない
- CSRF なし、カスタムエラーページなし
- 推薦の「理由文」が依頼書の期待に未到達
- migrate スクリプト欠落で Docker 起動に支障
- UI が CSS フレームワークなしの素の HTML

**Priority 1 の 5 項目を片付ければ、75〜80% まで引き上げられる。**
**Priority 2 まで完了すれば、85〜90% に到達し、提出可能なレベルになる。**
