# API Documentation

## Overview
This document provides a comprehensive overview of the API endpoints available in the system. Each endpoint is described with its path, HTTP method, parameters, and expected response.

## Endpoints

### Adding an Endpoint
To add an endpoint to the documentation, use the `add_endpoint` method.

#### Method
`add_endpoint(path: str, method: str, parameters: Dict[str, str], response: Dict[str, str]) -> None`

#### Parameters
- `path` (str): The path of the API endpoint.
- `method` (str): The HTTP method used (GET, POST, etc.).
- `parameters` (Dict[str, str]): A dictionary of parameters with their descriptions.
- `response` (Dict[str, str]): A dictionary describing the response format.

#### Example
```python
api_doc = ApiDocumentation()
api_doc.add_endpoint(
    path="/test",
    method="GET",
    parameters={"param1": "description1"},
    response={"key": "value"}
)
```

### Retrieving Documentation
To retrieve the documentation for all API endpoints, use the `get_documentation` method.

#### Method
`get_documentation() -> List[Dict[str, Dict[str, str]]]`

#### Returns
A list of dictionaries containing endpoint information.

#### Example
```python
documentation = api_doc.get_documentation()
```

### String Representation
The `__str__` method provides a formatted string representation of all API endpoints.

#### Example
```python
print(str(api_doc))
```

## Usage Examples

### Basic Usage
```python
api_doc = ApiDocumentation()
api_doc.add_endpoint(
    path="/example",
    method="POST",
    parameters={"param1": "description1"},
    response={"key": "value"}
)
print(api_doc.get_documentation())
```

### Multiple Endpoints
```python
api_doc.add_endpoint(
    path="/test1",
    method="GET",
    parameters={"param1": "description1"},
    response={"key1": "value1"}
)
api_doc.add_endpoint(
    path="/test2",
    method="POST",
    parameters={"param2": "description2"},
    response={"key2": "value2"}
)
print(api_doc)
```
