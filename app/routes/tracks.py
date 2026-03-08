from flask import Blueprint, render_template, request, redirect, abort, url_for, flash
from app.extensions import SessionLocal
from app.models.track import Track
from app.services.score import calc_total_score, parse_camelot
from app.utils.auth import login_required

tracks_bp = Blueprint("tracks", __name__)


def _validate_track_form(form):
    title = form.get("title", "").strip()
    artist = form.get("artist", "").strip()
    key = form.get("key", "").strip().upper()

    if not title:
        return None, "Title は必須です。"
    if not artist:
        return None, "Artist は必須です。"

    try:
        bpm = int(form.get("bpm", ""))
    except ValueError:
        return None, "BPM は数値で入力してください。"

    try:
        energy = int(form.get("energy", ""))
    except ValueError:
        return None, "Energy は数値で入力してください。"

    if not 40 <= bpm <= 250:
        return None, "BPM は 40 から 250 の範囲で入力してください。"
    if not 1 <= energy <= 10:
        return None, "Energy は 1 から 10 の範囲で入力してください。"

    try:
        parse_camelot(key)
    except ValueError:
        return None, "Key は Camelot 形式で入力してください（例: 8A, 9B）。"

    return {
        "title": title,
        "artist": artist,
        "bpm": bpm,
        "key": key,
        "energy": energy,
    }, None


def _build_transition_tip(base_energy, cand_energy, bpm_diff):
    if bpm_diff <= 2:
        bpm_tip = "テンポ差が小さいのでロングミックス向き"
    elif bpm_diff <= 5:
        bpm_tip = "軽いピッチ調整で自然につなげやすい"
    else:
        bpm_tip = "テンポ差が大きいのでブレイクやカットイン向き"

    if cand_energy > base_energy:
        energy_tip = "展開を上げたい場面向き"
    elif cand_energy < base_energy:
        energy_tip = "グルーブを落ち着かせたい場面向き"
    else:
        energy_tip = "同じ熱量を維持しやすい"

    return f"{bpm_tip} / {energy_tip}"


@tracks_bp.route("/")
@login_required
def index():

    db = SessionLocal()

    tracks = db.query(Track).order_by(Track.id.desc()).all()

    db.close()

    return render_template("tracks/index.html", tracks=tracks)


@tracks_bp.route("/tracks/new")
@login_required
def new_track():

    return render_template("tracks/new.html")


@tracks_bp.route("/tracks", methods=["POST"])
@login_required
def create_track():

    payload, error = _validate_track_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("tracks.new_track"))

    db = SessionLocal()

    track = Track(**payload)

    db.add(track)
    db.commit()

    db.close()

    flash("トラックを登録しました。", "success")
    return redirect("/")


@tracks_bp.route("/tracks/<int:track_id>")
@login_required
def detail(track_id):

    db = SessionLocal()

    track = db.query(Track).filter(Track.id == track_id).first()

    db.close()

    if not track:
        abort(404)

    return render_template("tracks/detail.html", track=track)


@tracks_bp.route("/tracks/<int:track_id>/edit")
@login_required
def edit(track_id):

    db = SessionLocal()

    track = db.query(Track).filter(Track.id == track_id).first()

    db.close()

    if not track:
        abort(404)

    return render_template("tracks/edit.html", track=track)


@tracks_bp.route("/tracks/<int:track_id>/update", methods=["POST"])
@login_required
def update(track_id):

    payload, error = _validate_track_form(request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("tracks.edit", track_id=track_id))

    db = SessionLocal()

    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        db.close()
        abort(404)

    track.title = payload["title"]
    track.artist = payload["artist"]
    track.bpm = payload["bpm"]
    track.key = payload["key"]
    track.energy = payload["energy"]

    db.commit()
    db.close()

    flash("トラックを更新しました。", "success")
    return redirect(f"/tracks/{track_id}")


@tracks_bp.route("/tracks/<int:track_id>/delete", methods=["POST"])
@login_required
def delete(track_id):

    db = SessionLocal()

    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        db.close()
        abort(404)

    db.delete(track)
    db.commit()

    db.close()

    flash("トラックを削除しました。", "success")
    return redirect("/")


@tracks_bp.route("/tracks/<int:track_id>/recommend")
@login_required
def recommend(track_id):
    db = SessionLocal()
    base_track = db.query(Track).filter(Track.id == track_id).first()

    if not base_track:
        db.close()
        abort(404)

    candidates = db.query(Track).filter(Track.id != track_id).all()
    db.close()

    if not candidates:
        flash("他のトラックがないため、おすすめを計算できません。", "error")
        return redirect(url_for("tracks.detail", track_id=track_id))

    base_payload = {
        "bpm": base_track.bpm,
        "energy": base_track.energy,
        "key": base_track.key,
    }

    recommendations = []
    for cand in candidates:
        result = calc_total_score(
            base_payload,
            {"bpm": cand.bpm, "energy": cand.energy, "key": cand.key},
        )
        recommendations.append(
            {
                "id": cand.id,
                "title": cand.title,
                "artist": cand.artist,
                "bpm": cand.bpm,
                "key": cand.key,
                "energy": cand.energy,
                "total_score": result["total_score"],
                "bpm_diff": result["bpm_diff"],
                "transition_tip": _build_transition_tip(
                    base_track.energy, cand.energy, result["bpm_diff"]
                ),
            }
        )

    recommendations.sort(key=lambda row: row["total_score"], reverse=True)

    return render_template(
        "tracks/recommend.html",
        base_track=base_track,
        recommendations=recommendations[:10],
    )
