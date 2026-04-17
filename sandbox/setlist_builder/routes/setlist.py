"""
セットリストビルダー用ルート
============================
既存の tracks_bp とは独立したブループリント。
sandbox 内で試す用。本番に組み込む場合は app/routes/ にコピーする。
"""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.extensions import SessionLocal
from app.models.track import Track
from app.utils.auth import login_required

# sandbox の services を使う
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.setlist_builder import (
    build_setlist,
    DIRECTION_UP,
    DIRECTION_KEEP,
    DIRECTION_DOWN,
)


setlist_bp = Blueprint(
    "setlist",
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
)


@setlist_bp.route("/setlist", methods=["GET"])
@login_required
def setlist_form():
    """セットリスト生成フォームを表示"""
    return render_template("setlist/form.html")


@setlist_bp.route("/setlist/build", methods=["POST"])
@login_required
def setlist_build():
    """セットリストを生成して結果を表示"""

    # --- フォームの入力を受け取る ---
    try:
        start_bpm = int(request.form.get("start_bpm", "128"))
    except ValueError:
        flash("開始BPMは数値で入力してください。")
        return redirect(url_for("setlist.setlist_form"))

    if not (40 <= start_bpm <= 250):
        flash("開始BPMは40〜250の範囲で入力してください。")
        return redirect(url_for("setlist.setlist_form"))

    direction = request.form.get("direction", DIRECTION_KEEP)
    if direction not in (DIRECTION_UP, DIRECTION_KEEP, DIRECTION_DOWN):
        direction = DIRECTION_KEEP

    try:
        set_length = int(request.form.get("set_length", "60"))
    except ValueError:
        flash("セット時間は数値で入力してください。")
        return redirect(url_for("setlist.setlist_form"))

    if not (10 <= set_length <= 300):
        flash("セット時間は10〜300分の範囲で入力してください。")
        return redirect(url_for("setlist.setlist_form"))

    # --- ユーザーのトラックをDBから取得 ---
    with SessionLocal() as session:
        rows = session.query(Track).filter_by(user_id=g.current_user.id).all()
        tracks = [
            {
                "id": t.id,
                "title": t.title,
                "artist": t.artist,
                "bpm": t.bpm,
                "key": t.key,
                "energy": t.energy,
            }
            for t in rows
        ]

    if len(tracks) < 2:
        flash("セットリストを作るには最低2曲必要です。先にトラックを登録してください。")
        return redirect(url_for("setlist.setlist_form"))

    # --- セットリスト生成 ---
    result = build_setlist(
        tracks=tracks,
        start_bpm=start_bpm,
        direction=direction,
        set_length_minutes=set_length,
    )

    direction_labels = {
        DIRECTION_UP: "BPMを上げていく",
        DIRECTION_KEEP: "BPMをキープ",
        DIRECTION_DOWN: "BPMを下げていく",
    }

    return render_template(
        "setlist/result.html",
        result=result,
        start_bpm=start_bpm,
        direction=direction,
        direction_label=direction_labels.get(direction, direction),
        set_length=set_length,
    )
