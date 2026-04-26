import logging
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.extensions import SessionLocal
from app.models.track import Track
from app.services.rekordbox import parse_rekordbox_csv
from app.services.score import calc_total_score, parse_camelot
from app.services.set_generator import generate_dj_set
from app.utils.auth import login_required

logger =logging.getLogger(__name__)

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
        # BPM は小数も許容（例: 80.5）。整数値を入れても float として扱う。
        bpm = float(form.get("bpm", ""))
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
    # bpm_diff は float でも来る前提
    diff = float(bpm_diff)
    if diff <= 2.0:
        bpm_tip = "テンポ差が小さいのでロングミックス向き"
    elif diff <= 5.0:
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


def _find_user_track(db, track_id, user_id):
    return db.query(Track).filter(
        Track.id == track_id,
        Track.user_id == user_id,
    ).first()


@tracks_bp.route("/")
@login_required
def index():
    db = SessionLocal()

    try:
        tracks = (
            db.query(Track)
            .filter(Track.user_id == g.current_user.id)
            .order_by(Track.id.desc())
            .all()
        )
    finally:
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

    try:
        track = Track(**payload, user_id=g.current_user.id)
        db.add(track)
        db.commit()
        logger.info("トラック作成: id=%s, user=%s", track.id, g.current_user.id)
    except Exception:
        db.rollback()
        logger.exception("トラック作成に失敗(user=%s)",g.current_user.id)
        raise
    finally:
        db.close()

    flash("トラックを登録しました。", "success")
    return redirect(url_for("tracks.index"))


@tracks_bp.route("/tracks/<int:track_id>")
@login_required
def detail(track_id):
    db = SessionLocal()

    try:
        track = _find_user_track(db, track_id, g.current_user.id)
    finally:
        db.close()

    if not track:
        abort(404)

    return render_template("tracks/detail.html", track=track)


@tracks_bp.route("/tracks/<int:track_id>/edit")
@login_required
def edit(track_id):
    db = SessionLocal()

    try:
        track = _find_user_track(db, track_id, g.current_user.id)
    finally:
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

    try:
        track = _find_user_track(db, track_id, g.current_user.id)
        if not track:
            abort(404)

        track.title = payload["title"]
        track.artist = payload["artist"]
        track.bpm = payload["bpm"]
        track.key = payload["key"]
        track.energy = payload["energy"]
        db.commit()
        logger.info("トラック更新: id=%s, user=%s", track_id, g.current_user.id)
    except Exception:
        db.rollback()
        logger.exception("トラック更新に失敗 (id=%s, user=%s)", track_id, g.current_user.id)
        raise
    finally:
        db.close()

    flash("トラックを更新しました。", "success")
    return redirect(url_for("tracks.detail", track_id=track_id))


@tracks_bp.route("/tracks/<int:track_id>/delete", methods=["POST"])
@login_required
def delete(track_id):
    db = SessionLocal()

    try:
        track = _find_user_track(db, track_id, g.current_user.id)
        if not track:
            abort(404)

        db.delete(track)
        db.commit()
        logger.info("トラック削除: id=%s, user=%s", track_id, g.current_user.id)
    except Exception:
        db.rollback()
        logger.exception("トラック削除に失敗 (id=%s, user=%s)", track_id, g.current_user.id)
        raise
    finally:
        db.close()

    flash("トラックを削除しました", "success")
    return redirect(url_for("tracks.index"))


@tracks_bp.route("/tracks/import")
@login_required
def import_form():
    """rekordbox CSV インポートフォームを表示する（GET）。"""
    return render_template("tracks/import.html")


@tracks_bp.route("/tracks/import", methods=["POST"])
@login_required
def import_tracks():
    """
    アップロードされた rekordbox CSV ファイルを処理して、
    トラックを一括登録する（POST）。

    処理の流れ:
        1. ファイルの存在・拡張子をチェック
        2. parse_rekordbox_csv() でパース
        3. DBに一括保存（bulk_save_objects）
        4. 結果（成功N件/スキップM件）を flash して一覧へリダイレクト
    """
    # ---- ファイルの存在チェック ----
    if "csv_file" not in request.files:
        flash("ファイルが選択されていません。", "error")
        return redirect(url_for("tracks.import_form"))

    file = request.files["csv_file"]

    if file.filename == "":
        flash("ファイルが選択されていません。", "error")
        return redirect(url_for("tracks.import_form"))

    # ---- 拡張子チェック（セキュリティ）----
    # .txt も許可するのは、rekordbox が .txt で書き出す場合があるため
    allowed_extensions = {".csv", ".txt"}
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
        flash("CSV または TXT ファイルのみアップロードできます。", "error")
        return redirect(url_for("tracks.import_form"))

    # ---- Energy のデフォルト値をフォームから取得 ----
    try:
        default_energy = int(request.form.get("default_energy", "5"))
        if not (1 <= default_energy <= 10):
            default_energy = 5
    except ValueError:
        default_energy = 5

    # ---- ファイルをバイト列として読み込む ----
    file_bytes = file.read()

    # ---- rekordbox CSV をパース ----
    result = parse_rekordbox_csv(file_bytes, default_energy=default_energy)

    if not result["tracks"] and result["skipped"] == 0 and result["skip_reasons"]:
        # ヘッダが見つからないなど、ファイル自体が読めなかった場合
        flash(f"インポートに失敗しました: {result['skip_reasons'][0]}", "error")
        return redirect(url_for("tracks.import_form"))

    # ---- DBに一括保存 ----
    db = SessionLocal()
    try:
        track_objects = [
            Track(**payload, user_id=g.current_user.id)
            for payload in result["tracks"]
        ]
        db.bulk_save_objects(track_objects)
        db.commit()
        logger.info(
            "CSVインポート完了: %s件登録, %s件スキップ (user=%s)",
            result["imported"], result["skipped"], g.current_user.id,
        )
    except Exception:
        db.rollback()
        logger.exception("CSVインポートに失敗 (user=%s)", g.current_user.id)
        raise
    finally:
        db.close()

    # ---- 結果を flash メッセージで表示 ----
    imported = result["imported"]
    skipped  = result["skipped"]

    if imported > 0:
        flash(f"{imported} 件のトラックをインポートしました。", "success")
    if skipped > 0:
        reasons_text = " / ".join(result["skip_reasons"][:5])
        flash(f"{skipped} 件をスキップしました（{reasons_text}）", "error")
    if imported == 0 and skipped == 0:
        flash("インポートできるトラックが見つかりませんでした。", "error")

    return redirect(url_for("tracks.index"))


@tracks_bp.route("/tracks/<int:track_id>/recommend")
@login_required
def recommend(track_id):
    db = SessionLocal()

    try:
        base_track = _find_user_track(db, track_id, g.current_user.id)
        if not base_track:
            abort(404)

        candidates = db.query(Track).filter(
            Track.id != track_id,
            Track.user_id == g.current_user.id,
        ).all()
    finally:
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
        # BPM差が大きすぎる候補（result is None）は推薦から除外する
        if result is None:
            continue
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
                "bpm_score": result["bpm_score"],
                "energy_score": result["energy_score"],
                "key_score": result["key_score"],
                "bpm_reason": result["bpm_reason"],
                "energy_reason": result["energy_reason"],
                "key_reason": result["key_reason"],
                "transition_tip": _build_transition_tip(
                    base_track.energy,
                    cand.energy,
                    result["bpm_diff"],
                ),
            }
        )

    recommendations.sort(key=lambda row: row["total_score"], reverse=True)

    return render_template(
        "tracks/recommend.html",
        base_track=base_track,
        recommendations=recommendations[:10],
    )


@tracks_bp.route("/tracks/generate-set")
@login_required
def generate_set_form():
    """DJセット生成フォームを表示する（GET）。"""
    return render_template("tracks/generate_set.html")


@tracks_bp.route("/tracks/generate-set", methods=["POST"])
@login_required
def generate_set():
    """
    DJセットを生成して結果を表示する（POST）。

    フォームから start_bpm, target_bpm, num_tracks を受け取り、
    set_generator で最適セットを計算して set_result.html に渡す。
    """

    try:
        # BPM は小数も可（例: 124.5）
        start_bpm = float(request.form.get("start_bpm", ""))
        target_bpm = float(request.form.get("target_bpm", ""))
        num_tracks = int(request.form.get("num_tracks", ""))
    except ValueError:
        flash("BPMとトラック数は数値で入力してください。", "error")
        return redirect(url_for("tracks.generate_set_form"))

    if not (40 <= start_bpm <= 250) or not (40 <= target_bpm <= 250):
        flash("BPM は 40〜250 の範囲で入力してください。", "error")
        return redirect(url_for("tracks.generate_set_form"))

    if not (2 <= num_tracks <= 30):
        flash("トラック数は 2〜30 の範囲で入力してください。", "error")
        return redirect(url_for("tracks.generate_set_form"))

    db = SessionLocal()
    try:
        result = generate_dj_set(
            db=db,
            user_id=g.current_user.id,
            start_bpm=start_bpm,
            target_bpm=target_bpm,
            num_tracks=num_tracks,
        )
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("tracks.generate_set_form"))
    finally:
        db.close()

    return render_template(
        "tracks/set_result.html",
        result=result,
        start_bpm=start_bpm,
        target_bpm=target_bpm,
    )