from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def valid_payload(**overrides):
    payload = {
        "board_width": 5,
        "board_height": 4,
        "piece_width": 2,
        "piece_height": 1,
        "allow_rotation": True,
        "defects": [{"x": 4, "y": 0}],
    }
    payload.update(overrides)
    return payload


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_valid_optimization_response():
    response = client.post("/api/cut", json=valid_payload())
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["product_count"] == 9
    assert data["stats"]["waste_area"] == 2
    assert data["products"][0]["rotated"] in (False, True)


def test_out_of_range_board_returns_422():
    response = client.post("/api/cut", json=valid_payload(board_width=11))
    assert response.status_code == 422


def test_out_of_board_defect_returns_422():
    response = client.post(
        "/api/cut",
        json=valid_payload(defects=[{"x": 5, "y": 0}]),
    )
    assert response.status_code == 422


def test_duplicate_defect_returns_422():
    response = client.post(
        "/api/cut",
        json=valid_payload(
            defects=[{"x": 0, "y": 0}, {"x": 0, "y": 0}]
        ),
    )
    assert response.status_code == 422
    assert "repeat" in response.text


def test_extra_field_returns_422():
    response = client.post(
        "/api/cut",
        json=valid_payload(kerf=0.1),
    )
    assert response.status_code == 422


def test_extra_nested_defect_field_returns_422():
    payload = valid_payload(defects=[{"x": 0, "y": 0, "blocked": True}])
    response = client.post("/api/cut", json=payload)
    assert response.status_code == 422


def test_numeric_float_rejected_by_strict_schema():
    response = client.post(
        "/api/cut",
        json=valid_payload(board_width=5.5),
    )
    assert response.status_code == 422


def test_boolean_is_not_accepted_as_integer():
    response = client.post(
        "/api/cut",
        json=valid_payload(board_width=True),
    )
    assert response.status_code == 422


def test_non_rotated_piece_must_fit():
    response = client.post(
        "/api/cut",
        json=valid_payload(
            board_width=3,
            board_height=3,
            piece_width=4,
            piece_height=1,
            allow_rotation=True,
            defects=[],
        ),
    )
    assert response.status_code == 422


def test_rotated_only_piece_is_allowed_when_rotation_enabled():
    response = client.post(
        "/api/cut",
        json=valid_payload(
            board_width=2,
            board_height=3,
            piece_width=3,
            piece_height=1,
            allow_rotation=True,
            defects=[],
        ),
    )
    assert response.status_code == 200
    assert response.json()["stats"]["product_count"] == 2


def test_rotated_only_piece_rejected_without_rotation():
    response = client.post(
        "/api/cut",
        json=valid_payload(
            board_width=2,
            board_height=3,
            piece_width=3,
            piece_height=1,
            allow_rotation=False,
            defects=[],
        ),
    )
    assert response.status_code == 422
