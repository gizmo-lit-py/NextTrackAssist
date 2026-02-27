from flask import Flask, render_template, request, url_for, redirect, abort, jsonify
from datetime import datetime
import db
import score

app = Flask(__name__)

# アプリ起動時にDB初期化
db.init_db()


#  DBから1件取るだけの関数
def fetch_track(track_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
    track = cursor.fetchone()
    conn.close()
    return track


@app.route("/")
def home():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks ORDER BY id DESC")
    tracks = cursor.fetchall()
    conn.close()
    return render_template("index.html", tracks=tracks)


@app.route("/tracks/new")
def new_track():
    return render_template("tracks/new.html")


@app.route("/tracks", methods=["POST"])
def create_track():
    title = request.form["title"]
    artist = request.form["artist"]
    bpm = request.form["bpm"]
    key = request.form["key"]
    energy = request.form["energy"]
    genre = request.form["genre"]
    created_at = datetime.now().isoformat()

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tracks (title, artist, bpm, key, energy, genre, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, artist, bpm, key, energy, genre, created_at),
    )

    conn.commit()
    conn.close()
    return redirect(url_for("home"))


@app.route("/tracks/<int:track_id>")
def show_track(track_id):
    track = fetch_track(track_id)
    if track is None:
        abort(404)
    return render_template("tracks/detail.html", track=track)


@app.route("/tracks/<int:track_id>/delete", methods=["POST"])
def delete_track(track_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))



@app.route("/tracks/<int:track_id>/edit")
def edit_track(track_id):
    track = fetch_track(track_id)
    if track is None:
        abort(404)
    return render_template("tracks/edit.html", track=track)

@app.route("/tracks/<int:track_id>/update", methods=["POST"])
def update_track(track_id):
    
    track = fetch_track(track_id)
    if track is None:
        abort(404)

    title = request.form["title"]
    artist = request.form["artist"]
    bpm = request.form["bpm"]
    key = request.form["key"]
    energy = request.form["energy"]
    genre = request.form.get("genre", "")


    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE tracks
        SET title = ?, artist = ?, bpm = ?, key = ?, energy = ?, genre = ?
        WHERE id = ?
        """,
        (title, artist, bpm, key, energy, genre, track_id),
    )
    conn.commit()
    conn.close()


    return redirect(url_for("show_track", track_id=track_id))

@app.route("/debug-score")
def debug_score():
    
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT * FROM tracks
                   ORDER BY id ASC
                   """)

    tracks = cursor.fetchall()
    conn.close()

    if len(tracks) < 2:
        return "曲が足りない"
    
    base_track = tracks[0]

    base = {
        "bpm": base_track["bpm"],
        "key": base_track["key"],
        "energy": base_track["energy"]
    }

    result = []

    for track in tracks[1:]:

        cand = {
            "bpm": track["bpm"],
            "key": track["key"],
            "energy": track["energy"]
        }

        score_result = score.calculate_match_score(base, cand)
        result.append({
            "title": track["title"],
            "total_score": score_result["total_score"]
        })
    
    result.sort(key=lambda x: x["total_score"], reverse=True)

    return jsonify(result)    

@app.route("/tracks/<int:track_id>/recommend")
def recommend(track_id):

    base_track = fetch_track(track_id)

    if base_track is None:
        abort(404)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT * FROM tracks
                   ORDER BY id ASC
                   """)
    
    tracks = cursor.fetchall()
    conn.close()

    base = {
        "bpm": base_track["bpm"],
        "key": base_track["key"],
        "energy": base_track["energy"]
    }

    result = []

    for track in tracks:
        if track["id"] == track_id:
            continue
    
        cand = {
            "bpm": track["bpm"],
            "key": track["key"],
            "energy": track["energy"]
        }

        score_result = score.calculate_match_score(base, cand)
        result.append({
            "title": track["title"],
            "total_score": score_result["total_score"],

            "bpm_score": score_result["bpm_score"],
            "bpm_reason": score_result["bpm_reason"],

            "key_score": score_result["key_score"],
            "key_label": score_result["key_label"], 
            
            "energy_score": score_result["energy_score"] ,
            "energy_reason": score_result["energy_reason"]})
    
    result.sort(key=lambda x: x["total_score"], reverse=True)
    top5 = result[:5]

    return render_template("tracks/recommend.html", base_track=base_track, recommendations=top5)
    


    

    

    




if __name__ == "__main__":
    app.run(debug=True, port=5001)