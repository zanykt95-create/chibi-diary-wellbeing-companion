"""
tests/test_mcp_server.py

Unit tests for the Chibi MCP Server tools.

Tests mock the ImagenClient so no real Vertex AI calls are made.
All tests should pass without internet access or credentials.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestGenerateChibiImage:
    """Tests for the generate_chibi_image MCP tool function."""

    def test_success_returns_correct_schema(self):
        """Tool returns expected keys on success."""
        mock_path = "./output/chibi_images/chibi_20240101_120000_abc12345.png"

        with patch("mcp_server.chibi_mcp_server._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_path
            mock_get_client.return_value = mock_client

            from mcp_server.chibi_mcp_server import generate_chibi_image
            result = generate_chibi_image("A cute chibi character beaming with joy")

        assert result["status"] == "success"
        assert result["image_path"] == mock_path
        assert result["model"] == "imagen-3.0-generate-001"
        assert result["error"] == ""
        assert "prompt_used" in result

    def test_error_handling_on_imagen_failure(self):
        """Tool returns error dict when Imagen raises an exception."""
        with patch("mcp_server.chibi_mcp_server._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.side_effect = RuntimeError("Quota exceeded")
            mock_get_client.return_value = mock_client

            from mcp_server.chibi_mcp_server import generate_chibi_image
            result = generate_chibi_image("A sad chibi character in the rain")

        assert result["status"] == "error"
        assert "Quota exceeded" in result["error"]
        assert result["image_path"] == ""

    def test_prompt_is_preserved_in_response(self):
        """The exact prompt sent to the tool is echoed back in prompt_used."""
        test_prompt = "A cute chibi character with wide eyes, kawaii aesthetic"

        with patch("mcp_server.chibi_mcp_server._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = "./output/chibi_images/test.png"
            mock_get_client.return_value = mock_client

            from mcp_server.chibi_mcp_server import generate_chibi_image
            result = generate_chibi_image(test_prompt)

        assert result["prompt_used"] == test_prompt


class TestImagenClient:
    """Tests for ImagenClient initialization."""

    def test_output_dir_created_on_init(self, tmp_path):
        """ImagenClient creates the output directory if it doesn't exist."""
        output_dir = tmp_path / "chibi_test_output"
        assert not output_dir.exists()

        from mcp_server.imagen_client import ImagenClient
        client = ImagenClient(
            project="test-project",
            location="us-central1",
            output_dir=str(output_dir),
        )

        assert output_dir.exists()
