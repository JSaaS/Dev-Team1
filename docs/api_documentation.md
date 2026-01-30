# API Documentation

## Overview
This document provides an overview of the API endpoints available in the application. Each endpoint is described with its purpose, request method, required parameters, and response structure.

## Table of Contents
1. [Authentication](#authentication)
2. [Tasks](#tasks)
   - [Create Task](#create-task)
   - [List Tasks](#list-tasks)
   - [Update Task](#update-task)
   - [Delete Task](#delete-task)

## Authentication
All endpoints require authentication via an API key. Include the API key in the request headers as follows:

```
Authorization: Bearer YOUR_API_KEY
```

## Tasks

### Create Task
- **Endpoint:** `/api/tasks`
- **Method:** `POST`
- **Description:** Create a new task.
- **Request Body:**
  ```json
  {
    "title": "string",
    "description": "string",
    "due_date": "YYYY-MM-DD"
  }
  ```
- **Response:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "description": "string",
    "due_date": "YYYY-MM-DD",
    "status": "string"
  }
  ```

### List Tasks
- **Endpoint:** `/api/tasks`
- **Method:** `GET`
- **Description:** Retrieve a list of all tasks.
- **Response:**
  ```json
  [
    {
      "id": "integer",
      "title": "string",
      "description": "string",
      "due_date": "YYYY-MM-DD",
      "status": "string"
    },
    ...
  ]
  ```

### Update Task
- **Endpoint:** `/api/tasks/{id}`
- **Method:** `PUT`
- **Description:** Update the details of an existing task.
- **Request Body:**
  ```json
  {
    "title": "string",
    "description": "string",
    "due_date": "YYYY-MM-DD",
    "status": "string"
  }
  ```
- **Response:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "description": "string",
    "due_date": "YYYY-MM-DD",
    "status": "string"
  }
  ```

### Delete Task
- **Endpoint:** `/api/tasks/{id}`
- **Method:** `DELETE`
- **Description:** Delete a task by its ID.
- **Response:**
  ```json
  {
    "message": "Task deleted successfully."
  }
  ```
