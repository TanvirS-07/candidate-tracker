"""Core pipeline behaviour. Each test pins something a refactor could plausibly break."""


def test_create_defaults_to_applied_and_validates_email(client, make_candidate):
    c = make_candidate()
    assert c["stage"] == "Applied" and c["notes"] == [] and c["summary"] is None
    bad = client.post("/api/candidates", json={"name": "X", "email": "not-an-email", "role": "Eng"})
    assert bad.status_code == 422


def test_filter_by_stage_and_role_combined(client, make_candidate):
    a = make_candidate(email="a@example.com", role="Engineer")
    make_candidate(email="b@example.com", role="Analyst")
    client.patch(f"/api/candidates/{a['id']}/stage", json={"stage": "Interview"})

    assert len(client.get("/api/candidates").json()) == 2
    assert [c["id"] for c in client.get("/api/candidates?stage=Interview").json()] == [a["id"]]
    assert client.get("/api/candidates?role=Analyst&stage=Interview").json() == []
    assert client.get("/api/candidates?stage=Bogus").status_code == 422


def test_sort_by_stage_uses_pipeline_order_not_alphabetical(client, make_candidate):
    # Alphabetically Offer < Rejected < Screening; pipeline order is Screening < Offer < Rejected.
    ids = {}
    for stage in ["Rejected", "Offer", "Screening"]:
        c = make_candidate(email=f"{stage.lower()}@example.com")
        client.patch(f"/api/candidates/{c['id']}/stage", json={"stage": stage})
        ids[stage] = c["id"]
    order = [c["stage"] for c in client.get("/api/candidates?sort=stage").json()]
    assert order == ["Screening", "Offer", "Rejected"]


def test_sort_by_date_is_newest_first(client, make_candidate):
    first = make_candidate(email="1@example.com")
    second = make_candidate(email="2@example.com")
    assert [c["id"] for c in client.get("/api/candidates?sort=date").json()] == [second["id"], first["id"]]


def test_notes_are_timestamped_newest_first_and_append_only(client, make_candidate):
    c = make_candidate()
    client.post(f"/api/candidates/{c['id']}/notes", json={"text": "first"})
    r = client.post(f"/api/candidates/{c['id']}/notes", json={"text": "  second  "})
    notes = r.json()["notes"]
    assert [n["text"] for n in notes] == ["second", "first"]
    assert all(n["created_at"] for n in notes)
    # No route exists to edit or delete a note.
    note_id = notes[0]["id"]
    assert client.delete(f"/api/candidates/{c['id']}/notes/{note_id}").status_code == 404
    assert client.put(f"/api/candidates/{c['id']}/notes/{note_id}", json={"text": "x"}).status_code == 404
    assert client.post(f"/api/candidates/{c['id']}/notes", json={"text": "   "}).status_code == 422


def test_archive_hides_from_list_but_keeps_data(client, make_candidate):
    c = make_candidate()
    client.patch(f"/api/candidates/{c['id']}/archive", json={"archived": True})
    assert client.get("/api/candidates").json() == []
    assert len(client.get("/api/candidates?include_archived=true").json()) == 1
    assert client.get(f"/api/candidates/{c['id']}").status_code == 200


def test_delete_removes_candidate_and_notes(client, make_candidate):
    c = make_candidate()
    client.post(f"/api/candidates/{c['id']}/notes", json={"text": "hello"})
    assert client.delete(f"/api/candidates/{c['id']}").status_code == 204
    assert client.get(f"/api/candidates/{c['id']}").status_code == 404
    assert client.delete(f"/api/candidates/{c['id']}").status_code == 404
