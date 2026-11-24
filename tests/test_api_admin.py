import uuid

from starlette.testclient import TestClient


# 1. Admin creates a user key -> 201 with raw key; use it immediately -> works
def test_admin_create_api_key_and_use_immediately(admin_client: TestClient) -> None:
    res = admin_client.post(
        "/admin/api-keys",
        json={"name": "new-test-user", "role": "user"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "api_key" in data
    raw_key = data["api_key"]

    # Use the newly created key immediately on /investigations with explicit header
    inv_res = admin_client.get("/investigations", headers={"X-API-Key": raw_key})
    assert inv_res.status_code == 200


# 2. Admin list -> returns summary, no key_hash or raw key in response
def test_admin_list_keys_never_exposes_hashes(admin_client: TestClient) -> None:
    # Create two keys
    admin_client.post("/admin/api-keys", json={"name": "key-1", "role": "user"})
    admin_client.post("/admin/api-keys", json={"name": "key-2", "role": "admin"})

    res = admin_client.get("/admin/api-keys")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2
    for item in items:
        assert "id" in item
        assert "name" in item
        assert "role" in item
        assert "is_active" in item
        assert "created_at" in item
        assert "key_hash" not in item
        assert "raw_key" not in item
        assert "api_key" not in item


# 3. Admin revokes key -> subsequent requests with that key -> 401
def test_admin_revoke_key(admin_client: TestClient) -> None:
    create_res = admin_client.post(
        "/admin/api-keys",
        json={"name": "to-revoke", "role": "user"},
    )
    assert create_res.status_code == 201
    key_id = create_res.json()["id"]
    raw_key = create_res.json()["api_key"]

    # Confirm key works
    user_res = admin_client.get("/investigations", headers={"X-API-Key": raw_key})
    assert user_res.status_code == 200

    # Revoke key (admin_client still has its admin credentials in default headers)
    del_res = admin_client.delete(f"/admin/api-keys/{key_id}")
    assert del_res.status_code == 204

    # Subsequent request with revoked key must fail with 401 api_key_disabled
    subsequent = admin_client.get("/investigations", headers={"X-API-Key": raw_key})
    assert subsequent.status_code == 401
    assert subsequent.json() == {"error": "api_key_disabled"}


# 4. Non-admin tries create/list/revoke -> 403
def test_non_admin_forbidden_on_all_admin_routes(user_client: TestClient) -> None:
    fake_id = uuid.uuid4()

    post_res = user_client.post("/admin/api-keys", json={"name": "bad", "role": "user"})
    assert post_res.status_code == 403
    assert post_res.json() == {"error": "admin_required"}

    get_res = user_client.get("/admin/api-keys")
    assert get_res.status_code == 403
    assert get_res.json() == {"error": "admin_required"}

    del_res = user_client.delete(f"/admin/api-keys/{fake_id}")
    assert del_res.status_code == 403
    assert del_res.json() == {"error": "admin_required"}
