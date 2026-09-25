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

"""Video generation and Cloud Storage upload service for PhonePilot using Google Omni."""

import asyncio
import base64
import datetime
import logging
import re
from typing import Any

from google import genai
from google.cloud import storage
from google.genai import types

logger = logging.getLogger("phone_pilot.video_service")

# Hardcoded project ID and public Cloud Storage bucket name
PROJECT_ID: str = "qwiklabs-gcp-04-7d222e5d4be1"
BUCKET_NAME: str = "bwg3-qwiklabs-gcp-04-7d222e5d4be1"
VIDEO_MODEL: str = "gemini-omni-flash-preview"
VIDEO_LOCATION: str = "global"

_genai_client: genai.Client | None = None
_storage_client: storage.Client | None = None


def get_genai_client() -> genai.Client:
    """Returns a singleton GenAI client configured for Vertex AI in global location."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=VIDEO_LOCATION,
        )
    return _genai_client


def get_storage_client() -> storage.Client:
    """Returns a singleton Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


async def generate_and_store_video(
    model_name: str,
    prompt_focus: str = "",
    tool_context: Any = None,
) -> dict[str, Any]:
    """Generates a short showcase video using gemini-omni-flash-preview in the global region,

    saves it to tool_context as an artifact, and uploads the bytes directly to the public GCS bucket.

    Args:
        model_name: Name of the smartphone (e.g. 'Google Pixel 11 Pro').
        prompt_focus: Optional feature or aspect to highlight (e.g. 'camera zoom', 'sleek design').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL and metadata.
    """
    client = get_genai_client()

    focus_clause = f" highlighting {prompt_focus}" if prompt_focus else ""
    prompt = (
        f"Cinematic commercial 360-degree product showcase of the {model_name} smartphone{focus_clause}. "
        "Sleek rotating hero shot, dramatic studio lighting highlighting premium glass and metal finishes, "
        "pristine camera lens details, 4k ultra-high definition product video, smooth camera motion."
    )

    logger.info("Generating video with %s (region: %s): %s", VIDEO_MODEL, VIDEO_LOCATION, prompt)

    try:
        interaction = await asyncio.to_thread(
            client.interactions.create,
            model=VIDEO_MODEL,
            input=prompt,
        )
    except Exception as e:
        logger.error("Failed calling interactions.create with %s: %s", VIDEO_MODEL, e)
        return {
            "error": f"Failed to generate video for '{model_name}' using {VIDEO_MODEL}: {str(e)}"
        }

    # If the interaction is still in progress, poll until completed
    if interaction.status != "completed":
        for _ in range(30):
            await asyncio.sleep(4)
            interaction = await asyncio.to_thread(client.interactions.get, interaction.id)
            if interaction.status in ("completed", "failed", "cancelled"):
                break

    if interaction.status != "completed":
        return {
            "error": f"Video generation for '{model_name}' did not complete successfully. Status: {interaction.status}"
        }

    if not hasattr(interaction, "output_video") or not interaction.output_video or not interaction.output_video.data:
        return {
            "error": f"Failed to generate video for '{model_name}'. No video data returned by {VIDEO_MODEL}."
        }

    raw_data = interaction.output_video.data
    if isinstance(raw_data, str):
        try:
            video_bytes = base64.b64decode(raw_data)
        except Exception as e:
            logger.error("Failed to base64 decode video data: %s", e)
            return {"error": f"Failed to decode video data: {str(e)}"}
    else:
        video_bytes = raw_data

    mime_type = getattr(interaction.output_video, "mime_type", "video/mp4") or "video/mp4"

    # Generate unique filename
    safe_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model_name.lower()).strip("_")
    if prompt_focus:
        safe_focus = re.sub(r"[^a-zA-Z0-9]+", "_", prompt_focus.lower()).strip("_")[:20]
        safe_slug = f"{safe_slug}_{safe_focus}"

    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    filename = f"{safe_slug}_showcase_{timestamp}.mp4"

    # (1) Save artifact with tool_context so it appears in Playground Artifacts panel
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(
                filename=filename,
                artifact=artifact_part,
            )
            logger.info("Saved video artifact %s to tool_context", filename)
        except Exception as e:
            logger.warning("Could not save video artifact to tool_context: %s", e)

    # (2) Upload video bytes to the public Cloud Storage bucket without writing to local file
    try:
        storage_cli = get_storage_client()
        bucket = storage_cli.bucket(BUCKET_NAME)
        blob_name = f"videos/{filename}"
        blob = bucket.blob(blob_name)
        await asyncio.to_thread(blob.upload_from_string, video_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        logger.info("Uploaded video to public URL: %s", public_url)
    except Exception as e:
        logger.error("Failed uploading video bytes to GCS bucket %s: %s", BUCKET_NAME, e)
        return {
            "error": f"Failed uploading video to Cloud Storage bucket '{BUCKET_NAME}': {str(e)}"
        }

    return {
        "status": "success",
        "model_name": model_name,
        "prompt_focus": prompt_focus,
        "filename": filename,
        "video_url": public_url,
        "url": public_url,
    }
