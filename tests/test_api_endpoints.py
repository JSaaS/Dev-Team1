# Full test file content...
import pytest
from app import create_app
from flask import json

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test for creating a task

def test_create_task_success(client):
    response = client.post('/api/tasks',
                           data=json.dumps({
                               'title': 'Test Task',
                               'description': 'Test Description',
                               'due_date': '2023-12-31'
                           }),
                           content_type='application/json')
    assert response.status_code == 201
    assert 'id' in response.json

# Test for listing tasks

def test_list_tasks_success(client):
    response = client.get('/api/tasks')
    assert response.status_code == 200
    assert isinstance(response.json, list)

# Test for updating a task

def test_update_task_success(client):
    # First, create a task to update
    create_response = client.post('/api/tasks',
                                  data=json.dumps({
                                      'title': 'Test Task',
                                      'description': 'Test Description',
                                      'due_date': '2023-12-31'
                                  }),
                                  content_type='application/json')
    task_id = create_response.json['id']

    # Now, update the task
    update_response = client.put(f'/api/tasks/{task_id}',
                                 data=json.dumps({
                                     'title': 'Updated Task',
                                     'description': 'Updated Description',
                                     'due_date': '2023-12-31',
                                     'status': 'completed'
                                 }),
                                 content_type='application/json')
    assert update_response.status_code == 200
    assert update_response.json['title'] == 'Updated Task'

# Test for deleting a task

def test_delete_task_success(client):
    # First, create a task to delete
    create_response = client.post('/api/tasks',
                                  data=json.dumps({
                                      'title': 'Task to Delete',
                                      'description': 'Description',
                                      'due_date': '2023-12-31'
                                  }),
                                  content_type='application/json')
    task_id = create_response.json['id']

    # Now, delete the task
    delete_response = client.delete(f'/api/tasks/{task_id}')
    assert delete_response.status_code == 200
    assert delete_response.json['message'] == 'Task deleted successfully.'

# Edge case: Test creating a task with missing fields

def test_create_task_missing_fields(client):
    response = client.post('/api/tasks',
                           data=json.dumps({
                               'title': 'Incomplete Task'
                           }),
                           content_type='application/json')
    assert response.status_code == 400

# Edge case: Test updating a non-existent task

def test_update_non_existent_task(client):
    response = client.put('/api/tasks/9999',
                          data=json.dumps({
                              'title': 'Non-existent Task',
                              'description': 'Description',
                              'due_date': '2023-12-31',
                              'status': 'completed'
                          }),
                          content_type='application/json')
    assert response.status_code == 404
