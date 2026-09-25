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

"""Unit tests for video generation tool and Cloud Storage integration."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agent import competitor_analyst, generate_smartphone_video, product_advocate
from app.video_service import (
    BUCKET_NAME,
    PROJECT_ID,
    VIDEO_LOCATION,
    VIDEO_MODEL,
    generate_and_store_video,
)


def test_video_service_constants():
    """Verify required model, region, project, and bucket configurations."""
    assert VIDEO_MODEL == "gemini-omni-flash-preview"
    assert VIDEO_LOCATION == "global"
    assert PROJECT_ID == "qwiklabs-gcp-04-7d222e5d4be1"
    assert BUCKET_NAME == "bwg3-qwiklabs-gcp-04-7d222e5d4be1"


def test_agent_video_tools_registration():
    """Verify generate_smartphone_video tool is registered with agents."""
    advocate_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in product_advocate.tools]
    assert "generate_smartphone_video" in advocate_tool_names

    analyst_tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in competitor_analyst.tools]
    assert "generate_smartphone_video" in analyst_tool_names


@pytest.mark.asyncio
async def test_generate_and_store_video_workflow():
    """Verify video generation, tool_context artifact save, and GCS upload without local files."""
    dummy_video_bytes = b"\x00\x00\x00 ftypisomdummy_mp4_bytes"
    encoded_video_data = base64.b64encode(dummy_video_bytes).decode("ascii")

    mock_interaction = MagicMock()
    mock_interaction.id = "test-interaction-123"
    mock_interaction.status = "completed"
    mock_interaction.output_video = MagicMock(
        data=encoded_video_data,
        mime_type="video/mp4",
    )

    mock_genai_client = MagicMock()
    mock_genai_client.interactions.create.return_value = mock_interaction

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket

    mock_tool_context = MagicMock()
    mock_tool_context.save_artifact = AsyncMock()

    with patch("app.video_service.get_genai_client", return_value=mock_genai_client), \
         patch("app.video_service.get_storage_client", return_value=mock_storage_client):
        result = await generate_and_store_video(
            model_name="Google Pixel 11 Pro",
            prompt_focus="titanium frame",
            tool_context=mock_tool_context,
        )

    # 1. Verify GenAI client called with correct model
    mock_genai_client.interactions.create.assert_called_once()
    call_kwargs = mock_genai_client.interactions.create.call_args.kwargs
    assert call_kwargs["model"] == "gemini-omni-flash-preview"
    assert "Google Pixel 11 Pro" in call_kwargs["input"]

    # 2. Verify artifact saved via tool_context
    mock_tool_context.save_artifact.assert_awaited_once()
    artifact_call = mock_tool_context.save_artifact.call_args.kwargs
    assert "google_pixel_11_pro" in artifact_call["filename"]
    assert artifact_call["filename"].endswith(".mp4")
    assert artifact_call["artifact"].inline_data.data == dummy_video_bytes
    assert artifact_call["artifact"].inline_data.mime_type == "video/mp4"

    # 3. Verify Cloud Storage upload
    mock_storage_client.bucket.assert_called_with("bwg3-qwiklabs-gcp-04-7d222e5d4be1")
    mock_blob.upload_from_string.assert_called_once_with(dummy_video_bytes, content_type="video/mp4")

    # 4. Verify return structure
    assert result["status"] == "success"
    assert result["model_name"] == "Google Pixel 11 Pro"
    assert result["video_url"].startswith(f"https://storage.googleapis.com/{BUCKET_NAME}/videos/")
    assert result["video_url"].endswith(".mp4")
