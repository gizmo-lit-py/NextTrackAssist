# ==========================================
# NextTrackAssist - REST API
# ==========================================
#
# JSON を返す API エンドポイント。
# フロントエンドや外部サービスから利用する。
# ==========================================

import logging

from flask import Blueprint, g, jsonify, request

from app.extensions import SessionLocal
from app.models.track import Track
from app.services.rekordbox import parse_rekordbox_csv
from app.services.score import calc_total_score
from app.services.set_generator import generate_dj_set
from app.utils.auth import login_required

logger=logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ==============================
# GET /api/tracks
# ==============================

@api_bp.get("/tracks")
@login_required
def list_tracks_api():
    """ログインユーザーの全トラックを JSON で返す。"""
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

    payload = [
        {
            "id": t.id,
            "title": t.title,
            "artist": t.artist,
            "bpm": t.bpm,
            "key": t.key,
            "energy": t.energy,
        }
        for t in tracks
    ]

    return jsonify(payload), 200


# ==============================
# POST /api/import
# ==============================

@api_bp.post("/import")
@login_required
def import_tracks_api():
    """
    rekordbox CSV をアップロードしてトラックを一括登録する。

    Request:
        Content-Type: multipart/form-data
        csv_file: CSVファイル
        default_energy (optional): 1-10, デフォルト5

    Response:
        {"imported": 5, "skipped": 2, "skip_reasons": [...]}
    """
    if "csv_file" not in request.files:
        return jsonify({"error": "csv_file is required"}), 400

    file = request.files["csv_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    allowed = {".csv", ".txt"}
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        return jsonify({"error": "Only .csv and .txt files are allowed"}), 400

    try:
        default_energy = int(request.form.get("default_energy", "5"))
        if not (1 <= default_energy <= 10):
            default_energy = 5
    except ValueError:
        default_energy = 5

    file_bytes = file.read()
    result = parse_rekordbox_csv(file_bytes, default_energy=default_energy)

    if not result["tracks"] and result["skipped"] == 0:
        return jsonify({"error": "Failed to parse CSV", "details": result["skip_reasons"]}), 400

    db = SessionLocal()
    try:
        track_objects = [
            Track(**payload, user_id=g.current_user.id)
            for payload in result["tracks"]
        ]
        db.bulk_save_objects(track_objects)
        db.commit()
        logger.info(
            "API CSVインポート完了: %s件登録, %s件スキップ (user=%s)",
            result["imported"], result["skipped"], g.current_user.id,
        ) 
    except Exception:
        db.rollback()
        logger.exception("API CSVインポートに失敗 (user=%s)", g.current_user.id)
        raise
    finally:
        db.close()

    return jsonify({
        "imported": result["imported"],
        "skipped": result["skipped"],
        "skip_reasons": result["skip_reasons"][:10],
    }), 201


# ==============================
# GET /api/recommend/<track_id>
# ==============================

@api_bp.get("/recommend/<int:track_id>")
@login_required
def recommend_api(track_id):
    """
    指定トラックに対する推薦結果を JSON で返す。

    Response:
        {
            "base_track": {...},
            "recommendations": [{...}, ...]
        }
    """
    db = SessionLocal()

    try:
        base_track = db.query(Track).filter(
            Track.id == track_id,
            Track.user_id == g.current_user.id,
        ).first()

        if not base_track:
            return jsonify({"error": "Track not found"}), 404

        candidates = db.query(Track).filter(
            Track.id != track_id,
            Track.user_id == g.current_user.id,
        ).all()
    finally:
        db.close()

    if not candidates:
        return jsonify({"error": "No other tracks to recommend from"}), 400

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
        recommendations.append({
            "id": cand.id,
            "title": cand.title,
            "artist": cand.artist,
            "bpm": cand.bpm,
            "key": cand.key,
            "energy": cand.energy,
            "total_score": result["total_score"],
            "bpm_score": result["bpm_score"],
            "energy_score": result["energy_score"],
            "key_score": result["key_score"],
            "bpm_reason": result["bpm_reason"],
            "energy_reason": result["energy_reason"],
            "key_reason": result["key_reason"],
        })

    recommendations.sort(key=lambda r: r["total_score"], reverse=True)

    return jsonify({
        "base_track": {
            "id": base_track.id,
            "title": base_track.title,
            "artist": base_track.artist,
            "bpm": base_track.bpm,
            "key": base_track.key,
            "energy": base_track.energy,
        },
        "recommendations": recommendations[:10],
    }), 200


# ==============================
# POST /api/generate-set
# ==============================

@api_bp.post("/generate-set")
@login_required
def generate_set_api():
    """
    DJセットを自動生成する。

    Request (JSON):
        {
            "start_bpm": 126,
            "target_bpm": 134,
            "num_tracks": 10
        }

    Response:
        {
            "tracks": [...],
            "bpm_curve": [126, 128, ...],
            "energy_curve": [6, 7, ...],
            "avg_score": 87.3,
            "total_tracks": 10
        }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        # BPM は小数も可（例: 124.5）。num_tracks のみ整数。
        start_bpm = float(data.get("start_bpm", 0))
        target_bpm = float(data.get("target_bpm", 0))
        num_tracks = int(data.get("num_tracks", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "start_bpm/target_bpm must be numbers, num_tracks must be integer"}), 400

    if not (40 <= start_bpm <= 250):
        return jsonify({"error": "start_bpm must be between 40 and 250"}), 400
    if not (40 <= target_bpm <= 250):
        return jsonify({"error": "target_bpm must be between 40 and 250"}), 400
    if not (2 <= num_tracks <= 30):
        return jsonify({"error": "num_tracks must be between 2 and 30"}), 400

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
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

    return jsonify(result), 200
