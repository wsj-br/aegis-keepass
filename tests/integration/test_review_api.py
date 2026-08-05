"""Integration tests for review match/search APIs."""

from __future__ import annotations

from tests.fixtures.builders import GITHUB_AEGIS_UUID, ORPHAN_AEGIS_UUID


def _find_entry(entries_json, aegis_uuid: str):
    return next(e for e in entries_json["entries"] if e["aegis_uuid"] == aegis_uuid)


def test_aegis_entries_filter(authed_client):
    all_resp = authed_client.get("/api/aegis-entries?status=all")
    assert all_resp.status_code == 200
    assert all_resp.get_json()["stats"]["total"] == 3

    unmatched = authed_client.get("/api/aegis-entries?status=unmatched")
    assert unmatched.status_code == 200
    body = unmatched.get_json()
    assert body["stats"]["unmatched"] >= 1
    assert all(not e["matched"] for e in body["entries"])

    q = authed_client.get("/api/aegis-entries?q=GitHub")
    assert q.status_code == 200
    assert any(e["issuer"] == "GitHub" for e in q.get_json()["entries"])


def test_keepass_search(authed_client):
    resp = authed_client.get("/api/keepass/search?q=GitHub")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] >= 1
    assert any(r["title"] == "GitHub" for r in body["results"])


def test_put_and_delete_match(authed_client):
    # Find KeePass UUID for Unrelated Bank via search
    search = authed_client.get("/api/keepass/search?q=Unrelated")
    kp_uuid = search.get_json()["results"][0]["uuid"]

    put = authed_client.put(
        "/api/match",
        json={
            "aegis_uuid": ORPHAN_AEGIS_UUID,
            "keepass_uuid": kp_uuid,
        },
    )
    assert put.status_code == 200
    entry = put.get_json()["entry"]
    assert entry["matched"] is True
    assert entry["keepass_uuid"] == kp_uuid
    assert entry["source"] == "manual" or entry["modified"] is True

    delete = authed_client.delete(
        "/api/match",
        json={"aegis_uuid": ORPHAN_AEGIS_UUID},
    )
    assert delete.status_code == 200
    cleared = delete.get_json()["entry"]
    assert cleared["matched"] is False


def test_match_conflict_then_confirm(authed_client):
    entries = authed_client.get("/api/aegis-entries").get_json()
    github = _find_entry(entries, GITHUB_AEGIS_UUID)
    assert github["matched"] is True
    github_kp = github["keepass_uuid"]

    # Try to link orphan to the same KeePass entry without confirm
    conflict = authed_client.put(
        "/api/match",
        json={
            "aegis_uuid": ORPHAN_AEGIS_UUID,
            "keepass_uuid": github_kp,
        },
    )
    assert conflict.status_code == 409
    assert conflict.get_json()["error"] == "conflict"

    confirmed = authed_client.put(
        "/api/match",
        json={
            "aegis_uuid": ORPHAN_AEGIS_UUID,
            "keepass_uuid": github_kp,
            "confirm": True,
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["entry"]["keepass_uuid"] == github_kp


def test_suggest_match(authed_client):
    # Clear orphan first (unmatched), suggest for GitHub-like orphan won't work;
    # clear GitHub match and re-suggest.
    authed_client.delete("/api/match", json={"aegis_uuid": GITHUB_AEGIS_UUID})
    resp = authed_client.post(
        "/api/keepass/suggest",
        json={"aegis_uuid": GITHUB_AEGIS_UUID},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["suggestion"] is not None or body.get("entry", {}).get("matched")
