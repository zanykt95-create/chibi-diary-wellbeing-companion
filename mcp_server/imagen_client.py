"""
mcp_server/imagen_client.py

Vertex AI Imagen 3 client for chibi-style image generation.
Wraps the vertexai SDK into a clean, testable interface.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

_MODEL_NAME = "imagen-3.0-generate-001"
_DEFAULT_OUTPUT_DIR = "./output/chibi_images"


class ImagenClient:
    """Wraps Vertex AI Imagen 3 via google-genai SDK for chibi illustration generation."""

    def __init__(
        self,
        project: str,
        location: str,
        output_dir: str = _DEFAULT_OUTPUT_DIR,
    ) -> None:
        self.project = project
        self.location = location
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
            )
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate a chibi image from the prompt. Returns the saved file path.

        Args:
            prompt: Descriptive chibi-style image prompt.

        Returns:
            Relative file path to the saved PNG image.

        Raises:
            RuntimeError: If image generation fails.
        """
        client = self._get_client()

        response = client.models.generate_images(
            model=_MODEL_NAME,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="BLOCK_ONLY_HIGH",
                person_generation="ALLOW_ALL",
            ),
        )

        # Check for filtered/empty response
        if not response.generated_images:
            raise RuntimeError(
                f"Imagen 3 returned no images. "
                f"HTTP response: {getattr(response, 'sdk_http_response', 'N/A')}"
            )

        generated = response.generated_images[0]

        # Image may be None if it was filtered by RAI
        if generated.image is None:
            reason = generated.rai_filtered_reason or "unknown RAI filter"
            raise RuntimeError(f"Image filtered by safety system: {reason}")

        image_bytes = generated.image.image_bytes
        if not image_bytes:
            raise RuntimeError("Imagen 3 returned empty image bytes.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"chibi_{timestamp}_{unique_id}.png"
        output_path = self.output_dir / filename

        output_path.write_bytes(image_bytes)
        return str(output_path)
