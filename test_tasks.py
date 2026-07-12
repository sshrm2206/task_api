import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from app import create_app
from config import TestingConfig
from models import db


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username="alice", email="alice@example.com", password="secret123"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def login(client, username="alice", password="secret123"):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def auth_header(client):
    login(client)
    resp = login(client)
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    def test_register_success(self, client):
        resp = register(client)
        assert resp.status_code == 201
        assert resp.get_json()["user"]["username"] == "alice"

    def test_register_duplicate_username(self, client):
        register(client)
        resp = register(client, email="other@example.com")
        assert resp.status_code == 409

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={"username": "bob"})
        assert resp.status_code == 400

    def test_login_success(self, client):
        register(client)
        resp = login(client)
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_wrong_password(self, client):
        register(client)
        resp = login(client, password="wrongpass")
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = login(client, username="ghost")
        assert resp.status_code == 401


class TestTasks:
    def _headers(self, client):
        register(client)
        resp = login(client)
        token = resp.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_task_requires_auth(self, client):
        resp = client.post("/api/tasks", json={"title": "No auth"})
        assert resp.status_code == 401

    def test_create_task_success(self, client):
        headers = self._headers(client)
        resp = client.post("/api/tasks", json={"title": "Write tests"}, headers=headers)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["title"] == "Write tests"
        assert body["status"] == "pending"

    def test_create_task_missing_title(self, client):
        headers = self._headers(client)
        resp = client.post("/api/tasks", json={"description": "no title"}, headers=headers)
        assert resp.status_code == 400

    def test_create_task_invalid_status(self, client):
        headers = self._headers(client)
        resp = client.post(
            "/api/tasks", json={"title": "Bad status", "status": "nope"}, headers=headers
        )
        assert resp.status_code == 400

    def test_list_tasks(self, client):
        headers = self._headers(client)
        client.post("/api/tasks", json={"title": "Task 1"}, headers=headers)
        client.post("/api/tasks", json={"title": "Task 2"}, headers=headers)
        resp = client.get("/api/tasks", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 2

    def test_filter_tasks_by_status(self, client):
        headers = self._headers(client)
        client.post(
            "/api/tasks",
            json={"title": "Done task", "status": "completed"},
            headers=headers,
        )
        client.post("/api/tasks", json={"title": "Pending task"}, headers=headers)
        resp = client.get("/api/tasks?status=completed", headers=headers)
        data = resp.get_json()
        assert data["total"] == 1
        assert data["tasks"][0]["title"] == "Done task"

    def test_get_single_task(self, client):
        headers = self._headers(client)
        create_resp = client.post("/api/tasks", json={"title": "Solo task"}, headers=headers)
        task_id = create_resp.get_json()["id"]
        resp = client.get(f"/api/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Solo task"

    def test_get_task_not_found(self, client):
        headers = self._headers(client)
        resp = client.get("/api/tasks/999", headers=headers)
        assert resp.status_code == 404

    def test_update_task(self, client):
        headers = self._headers(client)
        create_resp = client.post("/api/tasks", json={"title": "Old title"}, headers=headers)
        task_id = create_resp.get_json()["id"]
        resp = client.put(
            f"/api/tasks/{task_id}",
            json={"title": "New title", "status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["title"] == "New title"
        assert body["status"] == "in_progress"

    def test_delete_task(self, client):
        headers = self._headers(client)
        create_resp = client.post("/api/tasks", json={"title": "To delete"}, headers=headers)
        task_id = create_resp.get_json()["id"]
        resp = client.delete(f"/api/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        resp2 = client.get(f"/api/tasks/{task_id}", headers=headers)
        assert resp2.status_code == 404

    def test_user_cannot_see_others_tasks(self, client):
        headers_alice = self._headers(client)
        client.post("/api/tasks", json={"title": "Alice task"}, headers=headers_alice)

        register(client, username="bob", email="bob@example.com")
        resp = login(client, username="bob")
        headers_bob = {"Authorization": f"Bearer {resp.get_json()['access_token']}"}

        resp = client.get("/api/tasks", headers=headers_bob)
        assert resp.get_json()["total"] == 0
