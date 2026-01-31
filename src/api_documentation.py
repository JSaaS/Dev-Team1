# src/api_documentation.py

from typing import List, Dict

class ApiDocumentation:
    """
    A class to handle the documentation of API endpoints.
    """

    def __init__(self):
        self.endpoints = []

    def add_endpoint(self, path: str, method: str, parameters: Dict[str, str], response: Dict[str, str]) -> None:
        """
        Add an API endpoint to the documentation.

        :param path: The path of the API endpoint
        :param method: The HTTP method used (GET, POST, etc.)
        :param parameters: A dictionary of parameters with their descriptions
        :param response: A dictionary describing the response format
        """
        endpoint = {
            "path": path,
            "method": method,
            "parameters": parameters,
            "response": response
        }
        self.endpoints.append(endpoint)

    def get_documentation(self) -> List[Dict[str, Dict[str, str]]]:
        """
        Retrieve the documentation for all API endpoints.

        :return: A list of dictionaries containing endpoint information
        """
        return self.endpoints

    def __str__(self) -> str:
        """
        Provide a string representation of the API documentation.

        :return: A formatted string of all API endpoints
        """
        doc_lines = [f"Path: {ep['path']}, Method: {ep['method']}, Parameters: {ep['parameters']}, Response: {ep['response']}" for ep in self.endpoints]
        return "\n".join(doc_lines)
