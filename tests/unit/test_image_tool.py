# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for image generation tool and Cloud Storage integration."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agent import competitor_analyst, generate_smartphone_image, product_advocate
from app.image_service import BUCKET_NAME, IMAGE_LOCATION, IMAGE_MODEL, PROJECT_ID, generate_and_store_image


def test_image_service_constants():
    """Verify required model, region, project, and bucket configurations."""
    assert IMAGE_MODEL == "gemini-3.1-flash-lite-image"
    assert IMAGE_LOCATION == "global"
    assert PROJECT_ID == "qwiklabs-gcp-04-7d222e5d4be1"
    assert BUCKET_NAME == "bwg3-qwiklabs-gcp-04-7d222e5d4be1"


def test_agent_tools_registration():
    """Verify generate_smartphone_image and generate_comparison_image tools are registered with agents."""
    advocate_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in product_advocate.tools]
    assert "generate_smartphone_image" in advocate_tool_names

    analyst_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in competitor_analyst.tools]
    assert "generate_smartphone_image" in analyst_tool_names
    assert "generate_comparison_image" in analyst_tool_names

    # Check PreloadMemoryTool is present in competitor_analyst
    assert any("preload_memory" in str(getattr(t, "name", getattr(t, "__name__", str(t)))).lower() for t in competitor_analyst.tools)



@pytest.mark.asyncio
async def test_generate_and_store_image_workflow():
    """Verify image generation, tool_context artifact save, and GCS upload without local files."""
    dummy_bytes = b"\xff\xd8\xff\xe0dummy_jpeg_data"
    mock_part = MagicMock()
    mock_part.inline_data = MagicMock(data=dummy_bytes, mime_type="image/jpeg")

    mock_response = MagicMock()
    mock_response.parts = [mock_part]

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = mock_response

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket

    mock_tool_context = AsyncMock()

    with (
        patch("app.image_service.get_genai_client", return_value=mock_genai_client),
        patch("app.image_service.get_storage_client", return_value=mock_storage_client),
    ):
        result = await generate_and_store_image(
            model_name="Google Pixel 11 Pro",
            color="Obsidian",
            tool_context=mock_tool_context,
        )

    # 1. Check GenAI call uses gemini-3.1-flash-lite-image
    assert mock_genai_client.models.generate_content.called
    gen_call_kwargs = mock_genai_client.models.generate_content.call_args[1]
    assert gen_call_kwargs["model"] == "gemini-3.1-flash-lite-image"

    # 2. Check artifact saved with tool_context
    assert mock_tool_context.save_artifact.called
    artifact_kwargs = mock_tool_context.save_artifact.call_args[1]
    assert "google_pixel_11_pro" in artifact_kwargs["filename"]
    assert artifact_kwargs["artifact"].inline_data.data == dummy_bytes

    # 3. Check GCS upload called with direct bytes
    mock_storage_client.bucket.assert_called_with("bwg3-qwiklabs-gcp-04-7d222e5d4be1")
    assert mock_blob.upload_from_string.called
    upload_args = mock_blob.upload_from_string.call_args
    assert upload_args[0][0] == dummy_bytes
    assert upload_args[1]["content_type"] == "image/jpeg"

    # 4. Check returned public URL
    assert result["status"] == "success"
    assert result["url"].startswith("https://storage.googleapis.com/bwg3-qwiklabs-gcp-04-7d222e5d4be1/smartphones/")
    assert result["image_url"] == result["url"]


@pytest.mark.asyncio
async def test_generate_and_store_comparison_image_workflow():
    """Verify side-by-side comparison image generation, GCS upload, and Memory Bank push."""
    from app.image_service import generate_and_store_comparison_image

    dummy_bytes = b"\xff\xd8\xff\xe0comparison_dummy_jpeg"
    mock_part = MagicMock()
    mock_part.inline_data = MagicMock(data=dummy_bytes, mime_type="image/jpeg")

    mock_response = MagicMock()
    mock_response.parts = [mock_part]

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = mock_response

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket

    mock_tool_context = AsyncMock()

    with (
        patch("app.image_service.get_genai_client", return_value=mock_genai_client),
        patch("app.image_service.get_storage_client", return_value=mock_storage_client),
    ):
        result = await generate_and_store_comparison_image(
            primary_phone="Google Pixel 11 Pro",
            competitor_phones=["Samsung Galaxy S25 Ultra", "Apple iPhone 16 Pro"],
            tool_context=mock_tool_context,
        )

    # 1. Check GenAI prompt includes side-by-side comparison and Google theme
    assert mock_genai_client.models.generate_content.called
    gen_call_kwargs = mock_genai_client.models.generate_content.call_args[1]
    prompt_used = gen_call_kwargs["contents"][0]
    assert "Google-themed" in prompt_used or "Google themed" in prompt_used or "Google" in prompt_used
    assert "Pixel 11 Pro" in prompt_used
    assert "Galaxy S25 Ultra" in prompt_used

    # 2. Check artifact saved with tool_context
    assert mock_tool_context.save_artifact.called
    artifact_kwargs = mock_tool_context.save_artifact.call_args[1]
    assert "compare_" in artifact_kwargs["filename"]

    # 3. Check GCS upload called with direct bytes
    mock_storage_client.bucket.assert_called_with("bwg3-qwiklabs-gcp-04-7d222e5d4be1")
    assert mock_blob.upload_from_string.called
    upload_args = mock_blob.upload_from_string.call_args
    assert upload_args[0][0] == dummy_bytes

    # 4. Check Memory Bank push
    assert mock_tool_context.add_memory.called
    add_memory_kwargs = mock_tool_context.add_memory.call_args[1]
    memories = add_memory_kwargs["memories"]
    assert len(memories) >= 1
    assert "comparison" in memories[0].content.parts[0].text.lower()
    assert result["url"] in memories[0].content.parts[0].text

    # 5. Check add_session_to_memory was called
    assert mock_tool_context.add_session_to_memory.called

    # 6. Check returned structure
    assert result["status"] == "success"
    assert result["url"].startswith("https://storage.googleapis.com/bwg3-qwiklabs-gcp-04-7d222e5d4be1/smartphones/comparisons/")
    assert result["memory_bank_status"] == "pushed_to_memory_bank"

