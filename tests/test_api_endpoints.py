# Full test file content...
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test for Create Task Endpoint

def test_create_task_success(client):
    response = client.post('/api/tasks', json={"title": "Test Task", "description": "Test Description"})
    assert response.status_code == 201
    assert response.json['title'] == "Test Task"


def test_create_task_missing_title(client):
    response = client.post('/api/tasks', json={"description": "Test Description"})
    assert response.status_code == 400

# Test for List Tasks Endpoint

def test_list_tasks_success(client):
    response = client.get('/api/tasks')
    assert response.status_code == 200
    assert isinstance(response.json, list)

# Test for Update Task Endpoint

def test_update_task_success(client):
    # First, create a task
    create_response = client.post('/api/tasks', json={"title": "Task to Update", "description": "Description"})
    task_id = create_response.json['id']

    # Now, update the task
    update_response = client.put(f'/api/tasks/{task_id}', json={"title": "Updated Task", "description": "Updated Description", "status": "completed"})
    assert update_response.status_code == 200
    assert update_response.json['title'] == "Updated Task"


def test_update_task_not_found(client):
    response = client.put('/api/tasks/999', json={"title": "Non-existent Task", "description": "Description", "status": "completed"})
    assert response.status_code == 404

# Test for Delete Task Endpoint

def test_delete_task_success(client):
    # First, create a task
    create_response = client.post('/api/tasks', json={"title": "Task to Delete", "description": "Description"})
    task_id = create_response.json['id']

    # Now, delete the task
    delete_response = client.delete(f'/api/tasks/{task_id}')
    assert delete_response.status_code == 204


def test_delete_task_not_found(client):
    response = client.delete('/api/tasks/999')
    assert response.status_code == 404
