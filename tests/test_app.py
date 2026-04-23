import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture
def client():
    """Fixture to provide a TestClient and reset activities state after each test."""
    original_activities = copy.deepcopy(activities)
    yield TestClient(app, follow_redirects=False)
    activities.clear()
    activities.update(original_activities)


def test_root_redirect(client):
    """Test that the root endpoint redirects to the static index.html."""
    response = client.get("/")
    assert response.status_code == 307  # Temporary redirect
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test successful retrieval of all activities."""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "Basketball Team" in data
    assert "Soccer Club" in data
    # Verify structure of one activity
    basketball = data["Basketball Team"]
    assert "description" in basketball
    assert "schedule" in basketball
    assert "max_participants" in basketball
    assert "participants" in basketball
    assert isinstance(basketball["participants"], list)


def test_signup_success(client):
    """Test successful signup for an activity."""
    response = client.post("/activities/Basketball Team/signup", params={"email": "newstudent@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Signed up newstudent@example.com for Basketball Team" == data["message"]
    # Verify the participant was added
    assert "newstudent@example.com" in activities["Basketball Team"]["participants"]


def test_signup_activity_not_found(client):
    """Test signup for a non-existent activity."""
    response = client.post("/activities/Nonexistent Activity/signup", params={"email": "student@example.com"})
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Activity not found"


def test_signup_already_signed_up(client):
    """Test signup when the student is already signed up."""
    # First signup
    client.post("/activities/Soccer Club/signup", params={"email": "existing@example.com"})
    # Attempt second signup
    response = client.post("/activities/Soccer Club/signup", params={"email": "existing@example.com"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Student already signed up"


def test_signup_edge_case_empty_email(client):
    """Edge case: Signup with an empty email string."""
    response = client.post("/activities/Art Club/signup", params={"email": ""})
    assert response.status_code == 200  # No validation in the app, so it succeeds
    assert "" in activities["Art Club"]["participants"]


def test_signup_edge_case_duplicate_in_initial_data(client):
    """Edge case: Signup for an activity that already has participants, ensuring no conflict."""
    # Chess Club starts with participants
    initial_count = len(activities["Chess Club"]["participants"])
    response = client.post("/activities/Chess Club/signup", params={"email": "newchess@example.com"})
    assert response.status_code == 200
    assert len(activities["Chess Club"]["participants"]) == initial_count + 1
    assert "newchess@example.com" in activities["Chess Club"]["participants"]


def test_unregister_success(client):
    """Test successful unregistration from an activity."""
    # First, sign up
    client.post("/activities/Drama Club/signup", params={"email": "removeme@example.com"})
    assert "removeme@example.com" in activities["Drama Club"]["participants"]
    # Now unregister
    response = client.delete("/activities/Drama Club/participants/removeme@example.com")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Unregistered removeme@example.com from Drama Club" == data["message"]
    # Verify removed
    assert "removeme@example.com" not in activities["Drama Club"]["participants"]


def test_unregister_activity_not_found(client):
    """Test unregistration from a non-existent activity."""
    response = client.delete("/activities/Nonexistent Activity/participants/student@example.com")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Activity not found"


def test_unregister_participant_not_found(client):
    """Test unregistration when the participant is not signed up."""
    response = client.delete("/activities/Math Club/participants/notsignedup@example.com")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Participant not found"


def test_unregister_edge_case_remove_from_initial_data(client):
    """Edge case: Unregister a participant who was in the initial data."""
    # Programming Class has initial participants
    assert "emma@mergington.edu" in activities["Programming Class"]["participants"]
    response = client.delete("/activities/Programming Class/participants/emma@mergington.edu")
    assert response.status_code == 200
    assert "emma@mergington.edu" not in activities["Programming Class"]["participants"]


def test_unregister_edge_case_empty_email(client):
    """Edge case: Unregister with an empty email string (route doesn't match empty path param)."""
    # First sign up with empty email
    client.post("/activities/Debate Club/signup", params={"email": ""})
    assert "" in activities["Debate Club"]["participants"]
    # Now unregister - empty email in path doesn't match route
    response = client.delete("/activities/Debate Club/participants/")
    assert response.status_code == 404  # Route doesn't match empty {email}
    # Note: Empty email remains, as delete failed
    assert "" in activities["Debate Club"]["participants"]