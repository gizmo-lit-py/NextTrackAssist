from flask import Flask, render_template, request, redirect, url_for, abort
from contextlib import contextmanager
from db import SessionLocal
import models
import score


app = Flask(__name__)


# ==============================
# DBセッション管理（実務想定）
# ==============================

@contextmanager
def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ==============================
# ホーム（曲一覧）
# ==============================

@app.route("/")
def home():
    with get_db() as session:
        tracks = session.query(models.Track).all()
        return render_template("tracks/index.html", tracks=tracks)


# ==============================
# 曲追加フォーム表示
# ==============================

@app.route("/tracks/new")
def new_track():
    return render_template("tracks/new.html")


# ==============================
# 曲追加処理
# ==============================

@app.route("/tracks", methods=["POST"])
def create_track():
    with get_db() as session:
        try:
            new_track = models.Track(
                title=request.form["title"],
                artist=request.form["artist"],
                bpm=int(request.form["bpm"]),
                key=request.form["key"],
                energy=int(request.form["energy"])
            )

            session.add(new_track)
            session.commit()

        except Exception as e:
            session.rollback()
            print(f"Create track error: {e}")
            abort(400)

    return redirect(url_for("home"))


# ==============================
# レコメンド機能
# ==============================

@app.route("/tracks/<int:track_id>/recommend")
def recommend(track_id):

    with get_db() as session:

        base_track = session.query(models.Track).filter_by(id=track_id).first()

        if not base_track:
            abort(404)

        tracks = session.query(models.Track).all()

        base = {
            "bpm": base_track.bpm,
            "key": base_track.key,
            "energy": base_track.energy
        }

        results = []

        for track in tracks:
            if track.id == track_id:
                continue

            cand = {
                "bpm": track.bpm,
                "key": track.key,
                "energy": track.energy
            }

            try:
                score_result = score.calc_total_score(base, cand)
            except Exception as e:
                print(f"Score calculation error: {e}")
                continue

            results.append({
                "track": track,
                "score": score_result
            })

        results.sort(key=lambda x: x["score"]["total_score"], reverse=True)
        top5 = results[:5]

        return render_template(
            "tracks/recommend.html",
            base_track=base_track,
            recommendations=top5
        )


if __name__ == "__main__":
    app.run(debug=True)