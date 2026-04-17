# NextTrackAssist 全ファイル詳細解説（面接対策用）

---

## 0. プロジェクト全体像

**NextTrackAssist**は、DJが次にかける曲を選ぶときの判断を数値で補助するWebアプリ。

DJは普段「BPM（テンポ）」「Key（調）」「Energy（盛り上がり度）」を感覚で判断して曲をつなぐけど、このアプリはそれを**スコアリング（点数化）**して「この曲の次にはこの曲が合いますよ」と提案してくれる。

### 技術スタック一覧

| カテゴリ | 使っている技術 | 一言で言うと |
|---------|-------------|-----------|
| 言語 | Python 3.11 | サーバーサイドの言語 |
| Webフレームワーク | Flask 3.x | 軽量なWebフレームワーク。Djangoより小さくてシンプル |
| ORM | SQLAlchemy 2.0 | PythonからSQLを直接書かずにDBを操作できるライブラリ |
| DB | PostgreSQL 15 | 本番用のリレーショナルDB |
| テスト用DB | SQLite（インメモリ） | テスト時だけメモリ上にDB作って高速に実行 |
| 認証 | Flaskセッション + Werkzeug | パスワードのハッシュ化とセッション管理 |
| CSRF保護 | Flask-WTF | フォームの不正送信を防ぐ仕組み |
| コンテナ | Docker / Docker Compose | 開発環境を一発で立ち上げる仕組み |
| Webサーバー | Gunicorn + Nginx | Gunicornがアプリを動かし、Nginxがリバースプロキシ |
| テスト | pytest | Pythonの定番テストフレームワーク |

### アーキテクチャの設計思想

このアプリは**App Factoryパターン**と**Blueprint**を使った構成になっている。

- **App Factory（`create_app()`）**: アプリのインスタンスを関数で作る。テスト時に違う設定（SQLiteとか）で別のアプリを作れるのがメリット。
- **Blueprint**: URLのルーティングを機能ごとに分けて管理する仕組み。`auth_bp`（認証系）と`tracks_bp`（曲管理系）の2つに分かれている。
- **Service層の分離**: スコアリングのロジックを`services/score.py`に切り出していて、ルートの処理（HTTPリクエストの処理）とビジネスロジック（スコア計算）を分離している。これによって単体テストが書きやすくなる。

---

## 1. app/__init__.py（アプリケーションのエントリーポイント）

```
役割: Flaskアプリケーションを生成する「App Factory」
```

### コード解説

```python
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
import os
```

- `Flask`: Webフレームワーク本体のクラス
- `render_template`: HTMLテンプレートを描画する関数（Jinja2テンプレートエンジンを使用）
- `CSRFProtect`: **CSRF（Cross-Site Request Forgery）保護**。悪意のあるサイトからフォームを勝手に送信される攻撃を防ぐ
- `os`: 環境変数やファイルパスの操作に使う標準ライブラリ

```python
csrf = CSRFProtect()
```
CSRFProtectのインスタンスをモジュールレベルで作成。`init_app()`で後からアプリに紐づける（これを**遅延初期化**と言う）。

```python
def create_app():
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../templates")
    )
    app = Flask(__name__, template_folder=template_dir)
```
- `create_app()`が**App Factoryパターン**の本体。この関数を呼ぶたびに新しいFlaskアプリが生成される。
- `template_dir`: テンプレートフォルダの絶対パスを計算。`app/`ディレクトリの1つ上の`templates/`を指す。
- `os.path.dirname(__file__)`: このファイル自身のディレクトリ（`app/`）を取得
- `os.path.join(..., "../templates")`: そこから相対パスで`templates/`を指定
- `os.path.abspath(...)`: 相対パスを絶対パスに変換

```python
    app.config.from_object(Config)
```
`Config`クラスの属性をアプリの設定として読み込む。`SECRET_KEY`や`DATABASE_URL`などがここで設定される。

```python
    csrf.init_app(app)
```
CSRF保護をアプリに適用。以降、すべてのPOSTフォームに`csrf_token`が必要になる。

```python
    Base.metadata.create_all(bind=engine)
```
- `Base.metadata`: SQLAlchemyのモデル定義（UserやTrack）から生成されたテーブル情報
- `create_all()`: テーブルが存在しない場合だけ作成する（既存テーブルは触らない）
- **開発時の利便性のため**の処理。本番ではマイグレーションスクリプトを使う。

```python
    app.register_blueprint(auth_bp)
    app.register_blueprint(tracks_bp)
```
2つのBlueprintをアプリに登録。これで`/register`や`/login`（auth_bp）、`/tracks`（tracks_bp）のURLが使えるようになる。

```python
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500
```
- **カスタムエラーハンドラー**: 404（ページが見つからない）や500（サーバーエラー）のときに、自前のHTMLページを返す。
- 第2引数の`404`や`500`はHTTPステータスコード。これを指定しないとデフォルトの200（成功）が返ってしまう。

### 面接で聞かれそうなポイント

- 「なぜApp Factoryパターンを使ったのか？」→ テスト時に異なる設定（SQLiteインメモリDB、CSRF無効化など）でアプリを作れるようにするため。
- 「CSRFProtectはなぜ必要？」→ 外部サイトからの不正なPOSTリクエストを防ぐため。フォームにトークンを埋め込み、サーバーで照合する。

---

## 2. app/config.py（設定ファイル）

```
役割: 環境変数からアプリの設定を読み込むクラス
```

### コード解説

```python
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
```
- `SECRET_KEY`: Flaskのセッション暗号化に使う秘密鍵。Cookieに保存されるセッションデータを署名するために必要。
- `os.getenv("SECRET_KEY", "dev-secret-key")`: 環境変数`SECRET_KEY`があればそれを使い、なければ`"dev-secret-key"`をデフォルトにする。
- **本番では必ず強力なランダム文字列に変更する**必要がある。

```python
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://gizmo@localhost/nexttrack_db"
    )
```
- DB接続先のURL。`postgresql://ユーザー名@ホスト/DB名`の形式。
- Docker環境では`docker-compose.yml`で`DATABASE_URL`を上書きする。

```python
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```
- Flask-SQLAlchemyの変更追跡機能を無効化。メモリ節約のため。（このプロジェクトではFlask-SQLAlchemyの機能は直接は使っていないが、設定として残してある）

```python
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "True").lower() == "true"
```
- CSRF保護のON/OFF。テスト時は環境変数で`False`にして、テストコードからフォーム送信しやすくする。
- `.lower() == "true"`: 環境変数は文字列で来るので、`"True"` / `"False"`をboolに変換している。

### 面接で聞かれそうなポイント

- 「SECRET_KEYが漏れるとどうなる？」→ セッションの偽造が可能になる。攻撃者が他人のセッションを作り、なりすましログインができてしまう。
- 「なぜ環境変数で設定を管理する？」→ コードに秘密情報をハードコードしないため。`.env`ファイルや環境変数で管理し、Gitにはコミットしない。

---

## 3. app/extensions.py（DB接続・セッション定義）

```
役割: SQLAlchemyのエンジン・セッション・Baseクラスを定義する
```

### コード解説

```python
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
```

- `create_engine`: DBとの接続を管理するエンジンを作る関数
- `make_url`: DB接続URLをパースしてオブジェクトにする
- `sessionmaker`: DBセッション（トランザクション管理の単位）を作るファクトリ
- `declarative_base`: ORMのモデルクラスの基底クラスを作る関数
- `StaticPool`: コネクションプーリングの一種。SQLiteインメモリ用。

```python
url = make_url(Config.SQLALCHEMY_DATABASE_URI)
engine_kwargs = {"future": True}
```
- `future=True`: SQLAlchemy 2.0スタイルの新しいAPIを使うことを宣言。

```python
if url.get_backend_name() == "sqlite":
    engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
```
- **SQLite特有の設定**。テスト時（`DATABASE_URL=sqlite://`）だけ適用される。
- `check_same_thread=False`: SQLiteはデフォルトでは作成したスレッドからしかアクセスできない。Flaskは別スレッドでリクエストを処理する場合があるので、この制限を解除。
- `StaticPool`: インメモリSQLiteではDB接続が切れるとデータが消えるので、接続を使い回す（プールする）。

```python
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, **engine_kwargs)
```
エンジンの生成。これがDBとの「接続の窓口」になる。

```python
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    expire_on_commit=False,
)
```
- `SessionLocal`: DBセッションのファクトリ。`SessionLocal()`を呼ぶたびに新しいセッションが得られる。
- `autocommit=False`: 明示的に`commit()`しないと保存されない（安全側の設定）
- `autoflush=False`: クエリ前に自動的にflushしない。意図しないDB書き込みを防ぐ。
- `expire_on_commit=False`: **commit後もオブジェクトの属性にアクセスできる**ようにする。これがないと、commit後に`user.email`などにアクセスするとエラーになる（セッションが切れているため）。

```python
Base = declarative_base()
```
- `Base`: すべてのORMモデル（User, Track）の親クラス。このクラスを継承したクラスが自動的にテーブルとして認識される。

### 面接で聞かれそうなポイント

- 「ORMとは何か？」→ Object-Relational Mapping。Pythonのクラス/オブジェクトとDBのテーブル/行を対応づけて、SQLを直接書かずにDBを操作できる仕組み。
- 「expire_on_commitをFalseにしたのはなぜ？」→ DBセッションをclose()した後でもモデルの属性にアクセスしたいから。テンプレートにデータを渡すとき、セッションはすでに閉じていることが多い。
- 「SessionLocalを毎回呼ぶのはなぜ？」→ リクエストごとに独立したDBセッションを使い、トランザクション分離を確保するため。

---

## 4. app/models/user.py（Userモデル）

```
役割: usersテーブルに対応するORMモデル
```

### コード解説

```python
class User(Base):
    __tablename__ = "users"
```
- `Base`を継承 → SQLAlchemyが「これはDBテーブルに対応するクラスだ」と認識する。
- `__tablename__ = "users"`: 対応するテーブル名を指定。

```python
    id = Column(Integer, primary_key=True)
```
- **主キー（Primary Key）**。自動でインクリメント（1, 2, 3...と自動採番）される。

```python
    email = Column(String(255), unique=True, nullable=False, index=True)
```
- `unique=True`: 同じメールアドレスは登録できない（一意制約）
- `nullable=False`: NULLは許可しない（必須）
- `index=True`: **インデックスを貼る**。ログイン時にemailで検索するので、検索速度を上げるため。

```python
    password_hash = Column(String(255), nullable=False)
```
- パスワードは**ハッシュ化して保存**する。生のパスワードは絶対にDBに入れない。
- `werkzeug.security.generate_password_hash()`でハッシュ化、`check_password_hash()`で照合。

```python
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```
- `DateTime(timezone=True)`: タイムゾーン情報付きの日時型。PostgreSQLでは`TIMESTAMPTZ`に対応。
- `default=lambda: ...`: レコード作成時に自動的にUTCの現在時刻を入れる。

```python
    tracks = relationship(
        "Track",
        back_populates="user",
        cascade="all, delete-orphan"
    )
```
- **リレーション（関連）の定義**。UserとTrackは1対多の関係。
- `back_populates="user"`: Track側の`user`属性と双方向で繋がる。
- `cascade="all, delete-orphan"`: **ユーザーを削除したら、そのユーザーのトラックも全部削除される**。孤立レコード（orphan）を防ぐ。

### 面接で聞かれそうなポイント

- 「パスワードをハッシュ化するのはなぜ？」→ DBが漏洩しても生パスワードが分からないようにするため。ハッシュは一方向変換なので元に戻せない。
- 「cascade delete-orphanとは？」→ 親（User）が消えたら子（Track）も連動削除する設定。DBの整合性を保つ。
- 「indexをemailに貼る理由は？」→ ログイン時に`WHERE email = ?`で検索するため。インデックスがないとテーブル全行をスキャンして遅い。

---

## 5. app/models/track.py（Trackモデル）

```
役割: tracksテーブルに対応するORMモデル
```

### コード解説

```python
class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
```
- `ForeignKey("users.id")`: usersテーブルのid列への**外部キー制約**。このtrack がどのuserに属するかを表す。
- `ondelete="CASCADE"`: DB側でもカスケード削除を設定（SQLAlchemy側のcascadeとDB側のondeleteの両方で設定するのがベストプラクティス）。
- `index=True`: user_idで頻繁にフィルタリングするので検索を高速化。

```python
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    bpm = Column(Integer, nullable=False)
    key = Column(String(3), nullable=False)
    energy = Column(Integer, nullable=False)
```
- `bpm`: テンポ。曲の速さを表す数値（例: 128）
- `key`: Camelot形式のキー（例: "8A", "11B"）。最大3文字（"12B"）なので`String(3)`。
- `energy`: 曲の盛り上がり度。1〜10のスケール。

```python
    user = relationship("User", back_populates="tracks")
```
- User側の`tracks`リレーションとの双方向設定。`track.user`でそのtrackのユーザー情報にアクセスできる。

```python
    __table_args__ = (
        CheckConstraint("bpm BETWEEN 40 AND 250", name="check_bpm_range"),
        CheckConstraint("energy BETWEEN 1 AND 10", name="check_energy_range"),
    )
```
- **CHECK制約**: DB側でデータの範囲を強制する。アプリ側のバリデーションをすり抜けてもDBが最後の砦になる。
- BPMは40〜250（実際の楽曲がカバーする範囲）
- Energyは1〜10（DJソフトの一般的なスケール）

### 面接で聞かれそうなポイント

- 「外部キー制約はなぜ必要？」→ 存在しないユーザーに紐づくトラックが作られるのを防ぐ。データの整合性を担保する。
- 「CHECK制約とアプリ側バリデーションの両方があるのはなぜ？」→ **多層防御**。アプリ側はUX（ユーザーに分かりやすいエラーメッセージ）、DB側はデータの最終防御。
- 「Camelot形式とは？」→ DJミックスで使うキーの表記法。1〜12の数字とA/Bの組み合わせで表す。Camelot Wheelという円形の図で隣接するキーが調和する。

---

## 6. app/routes/auth.py（認証ルート）

```
役割: ユーザー登録・ログイン・ログアウトのHTTPエンドポイント
```

### コード解説

```python
auth_bp = Blueprint("auth", __name__)
```
- **Blueprint**の定義。`"auth"`は名前で、`url_for("auth.login")`のように使う。

#### ユーザー登録（/register）

```python
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
```
- GETでフォーム表示、POSTで登録処理。1つのエンドポイントで両方を処理するFlaskの典型的なパターン。

```python
    email = request.form["email"].strip().lower()
```
- `.strip()`: 前後の空白を除去
- `.lower()`: 小文字に正規化。メールアドレスの大文字小文字の違いで重複登録されるのを防ぐ。

```python
    if len(password) < 8:
        flash("パスワードは8文字以上にしてください。", "error")
        return render_template("auth/register.html")
```
- パスワードの最低文字数チェック。
- `flash()`: 1回限りのメッセージをセッションに保存し、次のテンプレート描画時に表示する。第2引数はカテゴリ（`"error"` or `"success"`）。

```python
    hashed_password = generate_password_hash(password)
    user = User(email=email, password_hash=hashed_password)
```
- `generate_password_hash()`: Werkzeugライブラリの関数。パスワードを**ソルト付きハッシュ**に変換する。
- **ソルト**: ランダムな文字列をパスワードに追加してからハッシュ化する。同じパスワードでも毎回違うハッシュ値になるので、レインボーテーブル攻撃を防げる。

```python
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        flash("このメールアドレスはすでに登録済みです。", "error")
```
- `IntegrityError`: `unique=True`に違反したときに発生する例外。つまり、同じメールアドレスが既に存在する場合。
- `db.rollback()`: トランザクションを巻き戻す。エラーが起きたDB操作を取り消す。
- `finally: db.close()`: どちらの場合もDBセッションを閉じる。**リソースリーク防止**。

#### ログイン（/login）

```python
    user = db.query(User).filter(User.email == email).first()
```
- emailでユーザーを検索。`.first()`は最初の1件を返す（なければ`None`）。

```python
    if user and check_password_hash(user.password_hash, password):
        session["user_id"] = user.id
        return redirect(url_for("tracks.index"))
```
- `check_password_hash()`: 保存されたハッシュと入力パスワードを照合する。
- `session["user_id"]`: FlaskのセッションにユーザーIDを保存。以降のリクエストでログイン状態を判定できる。
- セッションはCookieに暗号化されて保存される（`SECRET_KEY`で署名）。

#### ログアウト（/logout）

```python
    session.clear()
    return redirect(url_for("auth.login"))
```
- セッションの全データを消去 → ログイン状態が解除される。

### 面接で聞かれそうなポイント

- 「パスワードの照合はどうやっている？」→ 入力パスワードをハッシュ化して、DBに保存されたハッシュと比較する。元のパスワードは復元しない。
- 「セッション管理の仕組みは？」→ ログイン成功時にユーザーIDをセッション（サーバー署名付きCookie）に保存。以降のリクエストでそのCookieを読んで認証状態を確認する。
- 「IntegrityErrorを使っているのはなぜ？」→ 事前にSELECTで存在確認するより、INSERTしてエラーをキャッチする方が**レースコンディション**に強い（2人が同時に登録しようとしても安全）。

---

## 7. app/routes/tracks.py（トラックCRUD + 推薦ルート）

```
役割: トラックの一覧表示・登録・編集・削除・推薦機能のHTTPエンドポイント
```

### 主要な関数とヘルパー

#### `_validate_track_form(form)` — バリデーション関数

```python
def _validate_track_form(form):
    title = form.get("title", "").strip()
    ...
    try:
        bpm = int(form.get("bpm", ""))
    except ValueError:
        return None, "BPM は数値で入力してください。"
    ...
    try:
        parse_camelot(key)
    except ValueError:
        return None, "Key は Camelot 形式で入力してください"
```
- フォームの入力値を検証して、問題があればエラーメッセージを返す。
- 正常なら`(辞書データ, None)`、エラーなら`(None, エラーメッセージ)`を返す。
- **Camelotキーの検証**は`score.py`の`parse_camelot()`を再利用している。

#### `_build_transition_tip()` — DJミックスのヒント生成

```python
def _build_transition_tip(base_energy, cand_energy, bpm_diff):
    if bpm_diff <= 2:
        bpm_tip = "テンポ差が小さいのでロングミックス向き"
    ...
```
- BPM差とEnergy差から、DJ向けのアドバイスを日本語で生成する。
- 例: 「テンポ差が小さいのでロングミックス向き / 展開を上げたい場面向き」

#### `_find_user_track(db, track_id, user_id)` — 所有権チェック付き検索

```python
def _find_user_track(db, track_id, user_id):
    return db.query(Track).filter(
        Track.id == track_id,
        Track.user_id == user_id,
    ).first()
```
- `track_id`だけでなく`user_id`もフィルタ条件に入れることで、**他のユーザーのトラックにはアクセスできない**ようにしている。
- もし`track_id`だけで検索すると、URLを手打ちして他人のトラックを見たり編集できてしまう（**IDOR脆弱性**: Insecure Direct Object Reference）。

#### 一覧表示（GET /）

```python
@tracks_bp.route("/")
@login_required
def index():
    tracks = db.query(Track).filter(Track.user_id == g.current_user.id).order_by(Track.id.desc()).all()
```
- `@login_required`: ログインしていないユーザーはログインページにリダイレクトされる。
- `g.current_user`: `@login_required`デコレータで設定されたログイン中のユーザーオブジェクト。
- `order_by(Track.id.desc())`: 新しいものが上に来るように降順ソート。

#### トラック登録（POST /tracks）

```python
@tracks_bp.route("/tracks", methods=["POST"])
@login_required
def create_track():
    payload, error = _validate_track_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("tracks.new_track"))
    track = Track(**payload, user_id=g.current_user.id)
```
- `**payload`: 辞書をキーワード引数に展開。`Track(title="...", artist="...", ...)`と同じ。
- `user_id=g.current_user.id`: 現在ログインしているユーザーのIDを自動的にセット。

#### 推薦機能（GET /tracks/<id>/recommend）

```python
@tracks_bp.route("/tracks/<int:track_id>/recommend")
@login_required
def recommend(track_id):
```
- **アプリの中心機能**。選択した曲（base_track）に対して、他の自分の曲すべてとのスコアを計算し、上位10曲を推薦する。

```python
    candidates = db.query(Track).filter(
        Track.id != track_id,          # 自分自身は除外
        Track.user_id == g.current_user.id,  # 自分のトラックだけ
    ).all()
```

```python
    for cand in candidates:
        result = calc_total_score(base_payload, {"bpm": cand.bpm, ...})
        recommendations.append({...})

    recommendations.sort(key=lambda row: row["total_score"], reverse=True)
```
- 全候補のスコアを計算し、`total_score`の降順でソート。
- `recommendations[:10]`: 上位10件だけテンプレートに渡す。

### 面接で聞かれそうなポイント

- 「_find_user_trackで二重フィルタする理由は？」→ IDOR脆弱性の防止。URLのtrack_idを改ざんして他人のデータにアクセスするのを防ぐ。
- 「推薦ロジックはなぜルートではなくサービス層に置いた？」→ 責務の分離。ルートはHTTPリクエスト/レスポンスの処理に集中し、ビジネスロジックはサービス層で単体テスト可能にする。
- 「CRUDとは？」→ Create（作成）、Read（読み取り）、Update（更新）、Delete（削除）の4つの基本操作。

---

## 8. app/services/score.py（推薦スコアリングロジック）

```
役割: DJミックスの相性スコアを計算する「ドメインロジック」（このアプリの心臓部）
```

### 設計思想

**BPMを最重視（weight: 0.70）** している。これはDJミックスにおいてテンポのズレが最も致命的だから。キーは相性が多少合わなくても聴感上の違和感が少ないので、weight: 0.10と軽めに設定。

```
総合スコア = BPMスコア × 0.70 + Energyスコア × 0.20 + Keyスコア × 0.10
```

### 各関数の解説

#### `calc_bpm_score(base_bpm, cand_bpm)` — BPMスコア計算

```python
diff = abs(base_bpm - cand_bpm)
if diff <= 2: score = 100
elif diff == 3: score = 90
...
```
- 2曲のBPMの差分を取り、ルックアップテーブル形式でスコアを返す。
- `abs()`: 絶対値。どちらが速いかは関係なく、差の大きさだけで判定。
- BPM差2以内は「ほぼ一致」で100点、10以上は0点。

#### `calc_energy_score(base_energy, cand_energy)` — Energyスコア計算

- BPMスコアと同様に差分ベースで計算。
- 入力値のバリデーション（1〜10の範囲チェック）も含んでいる。

#### `parse_camelot(key)` — Camelotキーのパース

```python
def parse_camelot(key: str):
    key = key.strip().upper()
    number_part = key[:-1]   # "8A" → "8"
    letter_part = key[-1]    # "8A" → "A"
    number = int(number_part)
```
- Camelotキー文字列（例: "8A"）を数値部分（8）と文字部分（A）に分解する。
- 不正な入力にはValueErrorを送出。

#### `is_adjacent(n1, n2)` — Camelot番号の隣接判定

```python
def is_adjacent(n1, n2):
    return (n1 - n2) % 12 in (1, 11)
```
- **Camelot Wheelは12段階の循環構造**（12の次は1に戻る）。
- `(n1 - n2) % 12`が1か11なら隣接。例: 12と1は`(12-1)%12 = 11`なので隣接。

#### `calc_key_score(base_key, cand_key)` — Keyスコア計算

```python
if n1 == n2 and l1 == l2: return 100   # 完全一致
if l1 == l2 and is_adjacent(n1, n2): return 95  # 隣接・同Letter
if n1 == n2 and l1 != l2: return 90   # 同Number・相対調（AとBの切替）
if l1 != l2 and is_adjacent(n1, n2): return 80  # 隣接・異Letter
return 30  # それ以外
```
- Camelot Wheelの理論に基づいたスコアリング。

**Camelot Wheelの考え方（面接で説明できるように）:**
- 同じ番号でAとBの違い = **相対調**（メジャーとマイナーの関係）。調和的。
- 隣接する番号で同じ文字 = **半音階的に近い調**。自然に聴こえる転調。
- 隣接する番号で違う文字 = やや遠いけどまだ許容範囲。

#### `bpm_reason()`, `energy_reason()`, `key_reason()` — 理由文生成

- 各スコアの値から**日本語の評価文**を生成する。
- UIに「なぜこの曲を推薦したのか」の理由を表示するための関数。

#### `calc_total_score(base, cand, weights)` — 総合スコア計算

```python
def calc_total_score(base: dict, cand: dict, weights: dict = DEFAULT_WEIGHTS):
    ...
    if round(bpm_w + energy_w + key_w, 5) != 1.0:
        raise ValueError("Weights must sum to 1.0")

    total = bpm_score * bpm_w + energy_score * energy_w + key_score * key_w
```
- 3つのスコアを**加重平均**して総合スコアを算出。
- weightの合計が1.0であることをバリデーション（`round(..., 5)`は浮動小数点の誤差対策）。
- weightsは引数で渡せるので、将来的に重みを変更可能にする拡張性がある。

### 面接で聞かれそうなポイント

- 「なぜBPMの重みが0.70と高い？」→ DJミックスではテンポが合わないと曲が重ならないため最も重要。キーは多少ずれても聴感上の違和感が少ない。
- 「加重平均とは？」→ 各スコアに重み（weight）を掛けて合算する。全体の中でBPMを70%、Energyを20%、Keyを10%として評価する。
- 「Camelot Wheelの循環をどう処理している？」→ `(n1 - n2) % 12`の剰余演算（mod）で循環を表現。12と1の差は`11 % 12 = 11`で隣接と判定。

---

## 9. app/utils/auth.py（認証デコレータ）

```
役割: ログイン必須のエンドポイントを保護するデコレータ
```

### コード解説

```python
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("auth.login"))

        db = SessionLocal()
        try:
            user = db.get(User, user_id)
        finally:
            db.close()

        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))

        g.current_user = user
        return func(*args, **kwargs)
    return wrapper
```

- **デコレータ**: 関数を「包む」関数。`@login_required`と書くだけで、その下の関数にログインチェック機能を追加できる。
- `@wraps(func)`: 元の関数名やドキュメント文字列を保持する。これがないとFlaskのルーティングが壊れる（すべての関数名が`wrapper`になってしまう）。
- `session.get("user_id")`: セッションからユーザーIDを取得。ログインしていなければ`None`。
- `db.get(User, user_id)`: 主キーでユーザーを取得。SQLAlchemy 2.0の新しい書き方。
- `g.current_user = user`: **Flaskのgオブジェクト**にユーザーを格納。`g`はリクエストスコープのグローバル変数で、そのリクエストの処理中だけ有効。以降、`g.current_user`でどこからでもログインユーザーにアクセスできる。

### 面接で聞かれそうなポイント

- 「Pythonのデコレータとは？」→ 関数を引数に取り、機能を追加した新しい関数を返す高階関数。`@`構文はシンタックスシュガー。
- 「gオブジェクトとは？」→ Flaskのリクエストコンテキストに紐づいた一時的なストレージ。リクエストが終わると自動的に破棄される。
- 「なぜDBからユーザーを再取得する？」→ セッションにはIDだけ保存しているので、最新のユーザー情報をDBから取得する必要がある。また、ユーザーが削除されている場合にもセッションをクリアできる。

---

## 10. migrations/001_initial.py（マイグレーションファイル）

```
役割: 初回のテーブル作成マイグレーション
```

```python
def upgrade(engine):
    Base.metadata.create_all(bind=engine)
```

- `Base.metadata.create_all()`: 定義されたすべてのモデル（User, Track）に対応するテーブルを作成する。
- 「マイグレーション」とは、DBのスキーマ（テーブル構造）を段階的に変更管理する仕組み。バージョン管理のDB版。
- このプロジェクトでは簡易的な自前マイグレーションだが、本格的にはAlembicというツールを使う。

---

## 11. scripts/migrate.py（マイグレーション実行スクリプト）

```
役割: Docker起動時にテーブルを自動作成するスクリプト
```

```python
def run():
    print("[migrate] テーブルの確認・作成を開始します...")
    Base.metadata.create_all(bind=engine)
```

- `docker-compose.yml`の`command`から呼ばれる: `sh -c "python scripts/migrate.py && gunicorn ..."`
- テーブルが既に存在すれば何もしない（`create_all`は冪等: 何回実行しても同じ結果になる）。

---

## 12. scripts/init_db.py（DB接続確認スクリプト）

```
役割: DBに接続できるかだけを確認するスクリプト
```

```python
def main():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection is ready.")
```

- `SELECT 1`: 最もシンプルなクエリ。DBが応答するかの疎通確認。
- `with engine.connect() as connection`: コンテキストマネージャ。ブロックを抜けると自動的に接続を閉じる。

---

## 13. tests/conftest.py（テストの共通設定）

```
役割: pytestのフィクスチャ（テスト用の共通セットアップ）を定義
```

### コード解説

```python
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["WTF_CSRF_ENABLED"] = "False"
```
- テスト用の環境変数を設定。**SQLiteインメモリDB**を使うことで、PostgreSQLなしでテストを実行できる。
- CSRFを無効化することで、テストコードからフォームPOSTしやすくする。

```python
@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
```
- `autouse=True`: 全テストで自動的に実行される。
- テストの前にテーブルを作り直し、テスト後に削除する。**各テストが独立した状態で実行される**ことを保証。
- `yield`: yieldの前がセットアップ、後がティアダウン。

```python
@pytest.fixture()
def user_with_tracks():
    db = SessionLocal()
    user = User(email="dj@example.com", password_hash=generate_password_hash("password123"))
    other_user = User(email="other@example.com", ...)
    db.add_all([user, other_user])
    db.commit()
    # Track追加...
```
- テスト用のデータを作るフィクスチャ。2人のユーザーと3つのトラックを作成。
- `other_user`のトラック（"Hidden Track"）はデータ分離のテストに使う。

```python
@pytest.fixture()
def logged_in_client(client, user_with_tracks):
    client.post("/login", data={"email": "dj@example.com", "password": "password123"})
    return client, user_with_tracks
```
- ログイン済み状態のテストクライアントを返すフィクスチャ。

### 面接で聞かれそうなポイント

- 「pytestのフィクスチャとは？」→ テストの前準備（セットアップ）と後片付け（ティアダウン）を再利用可能にする仕組み。
- 「なぜSQLiteインメモリを使う？」→ テストの高速化。PostgreSQLを起動する必要がなく、メモリ上で瞬時にDB操作が完了する。
- 「autouse=Trueの意味は？」→ フィクスチャを引数に書かなくても全テストで自動的に適用される。

---

## 14. tests/test_app.py（アプリ全体テスト）

```
役割: アプリの基本動作とデータ分離をテスト
```

- `test_create_app_loads_secret_key`: SECRET_KEYが正しく読み込まれるかの確認。
- `test_tracks_are_scoped_to_logged_in_user`: ログインユーザーのトラックだけが表示され、他ユーザーのトラック（"Hidden Track"）は表示されないことを検証。
- `test_cannot_open_other_users_track`: 他ユーザーのトラックIDにアクセスすると404が返ることを検証（**IDOR対策の確認**）。

---

## 15. tests/test_auth.py（認証テスト）

```
役割: ユーザー登録・ログイン・ログアウトの動作テスト
```

主なテスト:
- `test_register_success`: 正常登録でログインページにリダイレクトされ、DBにユーザーが作成されること
- `test_register_duplicate_email`: 同一メールで2回登録するとエラーになること
- `test_register_short_password`: 8文字未満のパスワードが拒否されること
- `test_login_success`: 正しい認証情報でトラック一覧にリダイレクトされること
- `test_login_wrong_password`: 間違ったパスワードでエラーメッセージが出ること
- `test_logout_redirects_to_login`: ログアウト後にログインページにリダイレクトされること

---

## 16. tests/test_tracks.py（トラックCRUD + 推薦テスト）

```
役割: トラックの登録・編集・削除・推薦機能のテスト
```

主なテスト:
- **認証ガード**: 未ログインでアクセスするとリダイレクトされる
- **バリデーション**: BPM範囲外、Energy範囲外、不正なKey形式、Title空欄のテスト
- **CRUD**: 正常な登録・編集・削除のテスト
- **所有権**: 他ユーザーのトラックを編集/削除しようとすると404が返る
- **推薦**: 2曲以上ある場合にスコアが表示される / 1曲しかない場合のエラーメッセージ

---

## 17. tests/test_score.py（スコアリングロジック単体テスト）

```
役割: score.pyの各関数を独立してテスト
```

主なテスト:
- **BPMスコア**: 差分0→100点、差分3→90点、差分10以上→0点、対称性の確認
- **Keyスコア**: 完全一致→100点、隣接→95点、相対調→90点、循環（12A→1A）の確認
- **Energyスコア**: 差分0→100点、範囲外入力でValueError
- **総合スコア**: 完全一致→100点、BPM重視の設計確認（BPM一致なら他が悪くても高スコア）
- **理由文**: 各差分レベルに対して正しい日本語が返ること
- **Camelotパース**: 正常入力のパース、不正入力（ZZ, 0A, 13A, 8C）でValueError

### 面接で聞かれそうなポイント

- 「なぜスコアリングロジックの単体テストを分けた？」→ HTTPリクエストを通さずにビジネスロジックだけをテストできる。テストが速く、問題の特定も容易。
- 「テストの命名規則は？」→ `test_<何をテストするか>_<期待する結果>`の形式。例: `test_bpm_exact`は「BPMが完全一致のとき」のテスト。

---

## 18. templates/base.html（ベーステンプレート）

```
役割: 全ページ共通のHTML構造（レイアウトテンプレート）
```

- **Jinja2のテンプレート継承**を使用。他のテンプレートは`{% extends "base.html" %}`で継承し、`{% block content %}`の部分だけを上書きする。
- ナビゲーション: ログイン状態（`session.get("user_id")`）に応じて表示を切り替え。
- `get_flashed_messages(with_categories=true)`: `flash()`で設定したメッセージを表示。`error`なら赤背景、`success`なら緑背景。
- **CSRFトークン**は各フォームに`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`として埋め込む。

---

## 19. templates/auth/（認証系テンプレート）

### login.html
- メールアドレスとパスワードの入力フォーム。
- `type="email"`: ブラウザのメールアドレスバリデーション。
- `required`: HTML5の必須入力チェック。

### register.html
- `minlength="8"`: パスワードの最低文字数をHTML側でも制限（サーバー側のバリデーションとの二重チェック）。

---

## 20. templates/tracks/（トラック系テンプレート）

### index.html（一覧ページ）
- `{% for track in tracks %}`: Jinja2のforループでトラック一覧を描画。
- トラックがない場合は`{% if not tracks %}`で案内メッセージを表示。

### new.html（登録フォーム）
- BPM: `type="number" min="40" max="250"` でブラウザ側でも範囲制限。
- Key: `pattern="^(1[0-2]|[1-9])[AaBb]$"` 正規表現でCamelot形式を制限。
- Energy: `type="number" min="1" max="10"` で範囲制限。

### detail.html（詳細ページ）
- トラック情報の表示 + Edit, Recommend Next Track, Deleteのリンク/ボタン。
- Deleteは`<form method="POST">`で実装（GETでの削除はCSRF攻撃に弱いため）。

### edit.html（編集フォーム）
- new.htmlとほぼ同じだが、`value="{{track.title}}"`で既存値をプリセット。

### recommend.html（推薦結果ページ）
- Base Track（基準曲）の情報を表示。
- 推薦曲ごとに総合スコア、BPM/Energy/Keyの個別スコアと理由文、transition_tip（DJヒント）を表形式で表示。

---

## 21. templates/errors/（エラーページ）

### 404.html
- 「ページが見つかりません」メッセージとトラック一覧へのリンク。

### 500.html
- 「サーバーエラー」メッセージとトラック一覧へのリンク。

---

## 22. Dockerfile

```dockerfile
FROM python:3.11        # Pythonの公式Dockerイメージをベースにする
WORKDIR /app            # コンテナ内の作業ディレクトリを/appに設定
COPY requirements.txt . # 依存関係ファイルだけ先にコピー（キャッシュ効率化）
RUN pip install -r requirements.txt  # 依存関係をインストール
COPY . .                # アプリのソースコードをコピー
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:create_app()"]  # 起動コマンド
```

- `requirements.txt`を先にコピーしてpip installするのは**Dockerのレイヤーキャッシュ**を活用するため。ソースコードを変更してもrequirements.txtが変わらなければ、pip installのレイヤーはキャッシュから再利用される。
- `gunicorn`: 本番用のWSGIサーバー。Flaskの開発サーバーは本番には使わない（パフォーマンスとセキュリティの問題がある）。
- `0.0.0.0`: すべてのネットワークインターフェースでリッスン。Docker内からアクセス可能にするため。

---

## 23. docker-compose.yml

```yaml
services:
  db:      # PostgreSQLコンテナ
  web:     # Flaskアプリコンテナ
  nginx:   # リバースプロキシコンテナ
```

### 3つのコンテナの関係

```
ブラウザ → Nginx(:80) → Gunicorn/Flask(:8000) → PostgreSQL(:5432)
```

- **db**: PostgreSQL 15。`volumes: postgres_data`でデータを永続化。
- **web**: Flaskアプリ。`depends_on: db`でDBが起動した後に起動する。`expose: "8000"`はDocker内部ネットワークにのみポートを公開（外部からは直接アクセスできない）。
- **nginx**: リバースプロキシ。外部の80番ポートへのアクセスをwebの8000番に中継する。
- `command: sh -c "python scripts/migrate.py && gunicorn ..."`: まずマイグレーションを実行し、成功したらgunicornを起動する。

### 面接で聞かれそうなポイント

- 「なぜNginxを使う？」→ 静的ファイルの配信、ロードバランシング、SSL終端、リバースプロキシなど。Gunicorn単体より安全で高速。
- 「depends_onで起動順を制御しているが、DBが完全に起動するまで待つわけではない？」→ その通り。`depends_on`はコンテナの起動順だけで、DBが接続可能になるまでは待たない。本番ではwait-for-itスクリプトなどで対応する。

---

## 24. nginx/nginx.conf

```nginx
server {
    listen 80;
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- `proxy_pass http://web:8000`: Docker Composeのサービス名`web`で名前解決される。
- `proxy_set_header Host $host`: 元のHostヘッダーをバックエンドに転送。
- `proxy_set_header X-Real-IP $remote_addr`: クライアントの実IPをバックエンドに伝える（Nginxを経由するとIPがNginxのものになるため）。

---

## 25. requirements.txt（依存パッケージ一覧）

| パッケージ | バージョン | 役割 |
|-----------|-----------|------|
| Flask | 3.1.2 | Webフレームワーク本体 |
| Flask-SQLAlchemy | 3.1.1 | FlaskとSQLAlchemyの統合（設定の簡略化） |
| Flask-WTF | 1.2.2 | CSRF保護 |
| SQLAlchemy | 2.0.45 | ORM（DBとPythonオブジェクトの橋渡し） |
| psycopg2-binary | 2.9.11 | PostgreSQLのPythonドライバ |
| python-dotenv | 1.2.1 | .envファイルから環境変数を読み込む |
| gunicorn | 21.2.0 | 本番用WSGIサーバー |
| pytest | 9.0.2 | テストフレームワーク |
| WTForms | 3.2.2 | フォームバリデーション（Flask-WTFの依存） |

---

## 26. pytest.ini（pytest設定ファイル）

```ini
[pytest]
pythonpath = .
norecursedirs = copy_paste_ready
```

- `pythonpath = .`: プロジェクトルートをPythonのモジュール検索パスに追加。`from app import ...`が動くようにする。
- `norecursedirs`: テスト対象外のディレクトリを指定。

---

## 27. .env.example（環境変数テンプレート）

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/nexttrack_db
WTF_CSRF_ENABLED=True
```

- `.env`ファイルのテンプレート。`cp .env.example .env`して編集する。
- `.env`自体は`.gitignore`に入っているのでGitにはコミットされない（秘密情報の漏洩防止）。

---

## 28. .gitignore / .dockerignore

### .gitignore
- `__pycache__/`: Pythonのコンパイル済みファイル
- `*.sqlite3`, `*.db`: ローカルのDBファイル
- `.venv/`: 仮想環境
- `.env`: 秘密情報を含む環境変数ファイル
- `.pytest_cache/`: テストのキャッシュ

### .dockerignore
- Dockerビルド時にコンテキストから除外するファイル。ビルドの高速化とイメージサイズの削減。

---

## 面接で使える重要用語まとめ

| 用語 | 意味 |
|------|------|
| **App Factory** | `create_app()`関数でFlaskアプリを生成するパターン。テスト時に異なる設定で別インスタンスを作れる |
| **Blueprint** | Flaskのルートを機能ごとにモジュール分けする仕組み |
| **ORM** | Object-Relational Mapping。PythonオブジェクトとDBテーブルを対応づける |
| **マイグレーション** | DBスキーマの変更をバージョン管理する仕組み |
| **CSRF** | Cross-Site Request Forgery。外部サイトからの不正なPOSTリクエスト。トークンで防ぐ |
| **IDOR** | Insecure Direct Object Reference。URLのIDを改ざんして他人のデータにアクセスする脆弱性 |
| **ハッシュ化** | パスワードを一方向変換して保存する。元に戻せないので漏洩しても安全 |
| **ソルト** | ハッシュ化前にランダム文字列を追加。レインボーテーブル攻撃を防ぐ |
| **加重平均** | 各要素に重みを付けて平均する。`Σ(値×重み)` |
| **Camelot Wheel** | DJ用のキー表記法。12段階×2（A/B）の循環構造 |
| **Service層** | ビジネスロジックをルート（コントローラー）から分離した層 |
| **フィクスチャ** | テストの前準備を再利用可能にするpytestの機能 |
| **リバースプロキシ** | クライアントからのリクエストをバックエンドサーバーに中継するサーバー（Nginx） |
| **WSGIサーバー** | PythonのWebアプリケーションを動かすサーバー（Gunicorn）。FlaskはWSGI準拠 |
| **Docker Compose** | 複数のDockerコンテナをまとめて管理・起動する仕組み |
| **冪等（べきとう）** | 何回実行しても同じ結果になる性質。`create_all()`は既存テーブルを壊さない |
