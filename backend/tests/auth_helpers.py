FAKE_PASSWORD = "test-only-password"


def create_user(db, User, username="admin", display_name="Administrator"):
    user = User(username=username, display_name=display_name, is_active=True)
    user.set_password(FAKE_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username="admin", password=FAKE_PASSWORD):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    body = response.get_json()
    return response, body.get("data") if body else None


def csrf_post(client, path, csrf_token, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["X-CSRF-Token"] = csrf_token
    return client.post(path, headers=headers, **kwargs)
