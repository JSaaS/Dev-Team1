# tests/test_api_documentation.py

import pytest
from src.api_documentation import ApiDocumentation

@pytest.fixture
def api_doc():
    return ApiDocumentation()


def test_add_endpoint(api_doc):
    api_doc.add_endpoint(
        path="/test",
        method="GET",
        parameters={"param1": "description1"},
        response={"key": "value"}
    )
    assert len(api_doc.endpoints) == 1
    assert api_doc.endpoints[0]["path"] == "/test"
    assert api_doc.endpoints[0]["method"] == "GET"
    assert api_doc.endpoints[0]["parameters"] == {"param1": "description1"}
    assert api_doc.endpoints[0]["response"] == {"key": "value"}


def test_get_documentation(api_doc):
    api_doc.add_endpoint(
        path="/test",
        method="GET",
        parameters={"param1": "description1"},
        response={"key": "value"}
    )
    documentation = api_doc.get_documentation()
    assert len(documentation) == 1
    assert documentation[0]["path"] == "/test"
    assert documentation[0]["method"] == "GET"
    assert documentation[0]["parameters"] == {"param1": "description1"}
    assert documentation[0]["response"] == {"key": "value"}


def test_str_representation(api_doc):
    api_doc.add_endpoint(
        path="/test",
        method="GET",
        parameters={"param1": "description1"},
        response={"key": "value"}
    )
    str_representation = str(api_doc)
    expected_str = "Path: /test, Method: GET, Parameters: {'param1': 'description1'}, Response: {'key': 'value'}"
    assert str_representation == expected_str


def test_add_multiple_endpoints(api_doc):
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
    assert len(api_doc.endpoints) == 2
    assert api_doc.endpoints[1]["path"] == "/test2"
    assert api_doc.endpoints[1]["method"] == "POST"
    assert api_doc.endpoints[1]["parameters"] == {"param2": "description2"}
    assert api_doc.endpoints[1]["response"] == {"key2": "value2"}
