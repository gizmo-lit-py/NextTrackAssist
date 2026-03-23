from app.extensions import SessionLocal
from app.models.track import Track


def login(client, email="dj@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_create_app_loads_secret_key(app):
    assert app.config["SECRET_KEY"] == "test-secret-key"


def test_tracks_are_scoped_to_logged_in_user(client, user_with_tracks):
    response = login(client)
    assert response.status_code == 302

    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Track A" in body
    assert "Track B" in body
    assert "Hidden Track" not in body


def test_cannot_open_other_users_track(client, user_with_tracks):
    login(client)

    db = SessionLocal()
    hidden_track = db.query(Track).filter(Track.title == "Hidden Track").first()
    db.close()

    response = client.get(f"/tracks/{hidden_track.id}")
    assert response.status_code == 404