from flask import Blueprint, render_template, request, redirect, abort
from app.extensions import SessionLocal
from app.models.track import Track
from app.services.score import calc_total_score
from app.utils.auth import login_required

tracks_bp = Blueprint("tracks", __name__)


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

    db = SessionLocal()

    track = Track(
        title=request.form["title"],
        artist=request.form["artist"],
        bpm=int(request.form["bpm"]),
        key=request.form["key"],
        energy=int(request.form["energy"])
    )

    db.add(track)
    db.commit()

    db.close()

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

    db = SessionLocal()

    track = db.query(Track).filter(Track.id == track_id).first()

    if not track:
        db.close()
        abort(404)

    track.title = request.form["title"]
    track.artist = request.form["artist"]
    track.bpm = int(request.form["bpm"])
    track.key = request.form["key"]
    track.energy = int(request.form["energy"])

    db.commit()
    db.close()

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

    return redirect("/")