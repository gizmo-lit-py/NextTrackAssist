# NextTrackAssist：起動からDB作成までの流れ

Railwayは除外。「コンテナが起動してからDBのテーブルが出来上がるまで」を順番に追う。

---

## 全体の順番

```
Dockerfile の CMD
  │
  ├─① python scripts/migrate.py   ← テーブルを作る
  │
  └─② gunicorn "app:create_app()"  ← Webサーバーを起動する
```

CMD の `&&` でつながっているので、**マイグレーションが成功したらgunicornが起動する。失敗したら止まる。**

---

## ① migrate.py が何をするか（順番に）

```
migrate.py が実行される
  │
  ├─ Step 1: app.extensions をインポートする
  │          → このとき extensions.py の中身が全部実行される
  │
  ├─ Step 2: Track と User モデルをインポートする
  │          → このとき「Baseにテーブル定義が登録される」
  │
  ├─ Step 3: Base.metadata.create_all(bind=engine)
  │          → テーブルをDBに作る
  │
  └─ Step 4: 追加マイグレーション（002, 003）を順番に実行する
```

---

## Step 1 の中身：extensions.py で何が起きるか

```python
# extensions.py が import されたとき、この順番で実行される

url = make_url(Config.SQLALCHEMY_DATABASE_URI)
# ↑ まず config.py を読みに行く
#   DATABASE_URL 環境変数があればそれを使う
#   なければ "postgresql://gizmo@localhost/nexttrack_db" がデフォルト
#   → Railway では DATABASE_URL が設定されているのでそちらが使われる

# SQLite か PostgreSQL かを判定する
if url.get_backend_name() == "sqlite":
    engine = create_engine(..., StaticPool)   # テスト用
else:
    engine = create_engine(..., pool_pre_ping=True)  # 本番用
# ↑ 環境変数1本でDB接続先が自動で切り替わる仕組み

SessionLocal = sessionmaker(bind=engine, ...)
# ↑ DB操作に使うセッションの「設計図」を作る（まだ接続はしない）

Base = declarative_base()
# ↑ モデルクラスの「親」を作る。この Base に後でテーブル定義が登録される
```

**ポイント：`engine` も `Base` も `SessionLocal` も、この時点ではまだDBに接続していない。設計図を作っているだけ。**

---

## Step 2 の中身：モデルをインポートすると何が起きるか

```python
from app.models.track import Track  # noqa: F401
from app.models.user import User    # noqa: F401
```

モデルファイルの中身はこんな形になっている：

```python
# track.py
class Track(Base):          # ← Base を継承している
    __tablename__ = "tracks"
    id = Column(Integer, primary_key=True)
    bpm = Column(Float, nullable=False)
    key = Column(String(3), nullable=False)
    energy = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), ...)
    __table_args__ = (
        CheckConstraint("bpm BETWEEN 40 AND 250", ...),
        CheckConstraint("energy BETWEEN 1 AND 10", ...),
        CheckConstraint("key IN ('1A','1B',...,'12B')", ...),
    )
```

`class Track(Base)` と書いた瞬間に、**Pythonが自動的に「Baseにtracksテーブルの設計図を登録する」**。
migrate.py の `# noqa: F401` コメントは「このimportは使ってないように見えるけど、Base登録のために必要だよ」という意味。

---

## Step 3 の中身：create_all が何をするか

```python
Base.metadata.create_all(bind=engine)
```

`Base.metadata` の中には、Step 2 で登録された **users テーブルと tracks テーブルの設計図** が入っている。

`create_all` はこれを使って：
1. DBに接続する（engine 経由）
2. 「このテーブル、もう存在する？」とDBに確認する
3. **存在しなければ CREATE TABLE を実行する**
4. **存在すればスキップする（冪等）**

つまり何回実行しても安全。

---

## Step 4 の中身：追加マイグレーション（002・003）

`create_all` は「テーブルがあれば何もしない」ので、あとから列を追加したり制約を変えたりするときに使えない。そこで別途マイグレーションファイルを用意している。

```python
ADDITIONAL_MIGRATION_MODULES = [
    "migrations.002_bpm_float",      # bpm を Integer → Float に変更
    "migrations.003_key_constraint", # key に Camelot 24値の CHECK 制約を追加
]
```

各ファイルに `upgrade(engine)` 関数が定義されていて、「すでに適用済みなら何もしない」冪等な処理になっている。

---

## ② gunicorn + create_app() が何をするか

マイグレーションが終わったあと、gunicorn が起動する。

```
gunicorn -b 0.0.0.0:${PORT:-8000} "app:create_app()"
```

`create_app()` の中でやっていること：

```python
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)   # SECRET_KEY, DATABASE_URL を読み込む
    csrf.init_app(app)               # CSRF保護を有効化

    # Blueprintを登録する（ルーティングを有効化）
    app.register_blueprint(auth_bp)   # /register, /login, /logout
    app.register_blueprint(tracks_bp) # /tracks, /recommend, /generate-set
    app.register_blueprint(api_bp)    # /api/tracks, /api/recommend, /api/generate-set

    return app
```

**ポイント：create_app() はテーブルを作らない。テーブルはもう migrate.py が作ってある。create_app() はルーティングを有効にしてリクエストを受け付ける準備をするだけ。**

---

## 全体をひとことで

```
Dockerfile CMD
  ↓
migrate.py
  ├─ extensions.py → DATABASE_URL を読んで engine と Base を作る
  ├─ モデルimport → Base にテーブル設計図が登録される
  ├─ create_all → 存在しないテーブルを CREATE TABLE
  └─ upgrade() → 列追加・制約変更などの追加マイグレーション
  ↓
gunicorn → create_app()
  ├─ Flask アプリを生成
  ├─ Config 読み込み
  ├─ CSRF 有効化
  └─ Blueprint 登録（ルーティング有効化）
  ↓
HTTPリクエストを受け付け開始
```

---

## よく混乱するポイントまとめ

| 疑問 | 答え |
|------|------|
| Base って何？ | モデルクラスの「親」。`class Track(Base)` と書くことで、Baseにテーブル設計図が登録される |
| engine って何？ | DBへの接続設定をまとめたオブジェクト。実際の接続は必要になったときに初めて張る |
| create_all はいつDBに触る？ | 呼び出された瞬間（migrate.py の `run()` の中） |
| create_app() はDBを作る？ | 作らない。Blueprintを登録してWebサーバーの準備をするだけ |
| `noqa: F401` って何？ | 「使ってないimportに見えるけど、Baseへの登録のために必要だから警告を消して」という意味 |
| SQLite と PostgreSQL の切替は？ | `DATABASE_URL` 環境変数1本で自動切替。テスト時は `sqlite://`、本番は Railway の PostgreSQL URL |
