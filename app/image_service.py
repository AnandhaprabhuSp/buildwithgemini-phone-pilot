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

"""Image generation and Cloud Storage upload service for PhonePilot."""

import datetime
import logging
import re
from typing import Any

from google import genai
from google.cloud import storage
from google.genai import types

logger = logging.getLogger("phone_pilot.image_service")

# Hardcoded project ID and public Cloud Storage bucket name
PROJECT_ID: str = "qwiklabs-gcp-04-7d222e5d4be1"
BUCKET_NAME: str = "bwg3-qwiklabs-gcp-04-7d222e5d4be1"
IMAGE_MODEL: str = "gemini-3.1-flash-lite-image"
IMAGE_LOCATION: str = "global"

_genai_client: genai.Client | None = None
_storage_client: storage.Client | None = None


def get_genai_client() -> genai.Client:
    """Returns a singleton GenAI client configured for Vertex AI in global location."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=IMAGE_LOCATION,
        )
    return _genai_client


def get_storage_client() -> storage.Client:
    """Returns a singleton Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


async def generate_and_store_image(
    model_name: str,
    color: str = "",
    tool_context: Any = None,
) -> dict[str, Any]:
    """Generates a product image using gemini-3.1-flash-lite-image in global region,

    saves it to tool_context as an artifact, and uploads the bytes to public GCS bucket.

    Args:
        model_name: Name of the smartphone (e.g. 'Google Pixel 11 Pro').
        color: Optional color finish (e.g. 'Obsidian', 'Porcelain', 'Hazel').
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL and metadata.
    """
    client = get_genai_client()

    color_clause = f" in {color} color finish" if color else ""
    prompt = (
        f"Professional studio product photography of {model_name}{color_clause}. "
        "Sleek premium flagship smartphone, pristine glass and metal design, centered, "
        "dramatic studio lighting, sharp focus, 4k resolution, clean minimal background."
    )

    logger.info("Generating image with %s (region: %s): %s", IMAGE_MODEL, IMAGE_LOCATION, prompt)

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes: bytes | None = None
    mime_type: str = "image/jpeg"

    if response.parts:
        for part in response.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {
            "error": f"Failed to generate image for '{model_name}'. No image data returned by {IMAGE_MODEL}."
        }

    # Generate unique filename
    safe_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model_name.lower()).strip("_")
    if color:
        safe_color = re.sub(r"[^a-zA-Z0-9]+", "_", color.lower()).strip("_")
        safe_slug = f"{safe_slug}_{safe_color}"

    extension = "jpg" if "jpeg" in mime_type.lower() else "png"
    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    filename = f"{safe_slug}_{timestamp}.{extension}"

    # (1) Save artifact with tool_context so it appears in Playground Artifacts panel
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(
                filename=filename,
                artifact=artifact_part,
            )
            logger.info("Saved artifact %s to tool_context", filename)
        except Exception as e:
            logger.warning("Could not save artifact to tool_context: %s", e)

    # (2) Upload image bytes to the public Cloud Storage bucket without writing to local file
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(BUCKET_NAME)
    blob_name = f"smartphones/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    logger.info("Uploaded image to public URL: %s", public_url)

    return {
        "status": "success",
        "model_name": model_name,
        "color": color,
        "filename": filename,
        "image_url": public_url,
        "url": public_url,
    }


async def generate_and_store_comparison_image(
    primary_phone: str,
    competitor_phones: list[str] | str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Generates a rich, Google-themed side-by-side product comparison image using

    gemini-3.1-flash-lite-image in the global region, saves it to session artifacts,
    uploads it to the public GCS bucket, and pushes the image memory to Memory Bank.

    Args:
        primary_phone: The user's primary/preferred smartphone (e.g. 'Google Pixel 11 Pro').
        competitor_phones: One or more competitor smartphones to compare side-by-side.
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL, phones compared, and status.
    """
    client = get_genai_client()

    if isinstance(competitor_phones, str):
        competitors = [p.strip() for p in competitor_phones.split(",") if p.strip()]
    else:
        competitors = list(competitor_phones)

    all_phones = [primary_phone] + competitors
    phones_str = " vs ".join(all_phones)

    prompt = (
        f"A rich, premium, Google-themed graphic comparing smartphones side-by-side: {phones_str}. "
        "Clean Google Material Design aesthetic with subtle Google colored accent lighting (blue, red, yellow, green), "
        "showing the devices standing side-by-side on sleek presentation pedestals, "
        "crisp studio lighting, photorealistic high-resolution product comparison render, modern tech showcase."
    )

    logger.info("Generating side-by-side comparison image: %s", prompt)

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes: bytes | None = None
    mime_type: str = "image/jpeg"

    if response.parts:
        for part in response.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {
            "error": f"Failed to generate comparison image for '{phones_str}'. No image data returned by {IMAGE_MODEL}."
        }

    slug_parts = [re.sub(r"[^a-zA-Z0-9]+", "_", p.lower()).strip("_") for p in all_phones]
    combined_slug = "_vs_".join(slug_parts)[:60]
    extension = "jpg" if "jpeg" in mime_type.lower() else "png"
    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    filename = f"compare_{combined_slug}_{timestamp}.{extension}"

    # (1) Save artifact with tool_context so it appears in Playground Artifacts panel
    if tool_context is not None and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(
                filename=filename,
                artifact=artifact_part,
            )
            logger.info("Saved comparison artifact %s to tool_context", filename)
        except Exception as e:
            logger.warning("Could not save comparison artifact to tool_context: %s", e)

    # (2) Upload image bytes to public Cloud Storage bucket without writing to local file
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(BUCKET_NAME)
    blob_name = f"smartphones/comparisons/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    logger.info("Uploaded comparison image to public URL: %s", public_url)

    # (3) Push comparison image fact to Memory Bank
    if tool_context is not None:
        try:
            if hasattr(tool_context, "add_memory"):
                from google.adk.memory.memory_entry import MemoryEntry

                memory_fact = (
                    f"Product comparison image generated for {phones_str}. "
                    f"Google-themed side-by-side visual comparison graphic. "
                    f"Public Image URL: {public_url}"
                )
                entry = MemoryEntry(
                    content=types.Content(
                        parts=[types.Part.from_text(text=memory_fact)]
                    ),
                    custom_metadata={
                        "type": "product_comparison_image",
                        "phones": phones_str,
                        "url": public_url,
                        "timestamp": str(datetime.datetime.now(datetime.timezone.utc)),
                    },
                )
                await tool_context.add_memory(memories=[entry])
                logger.info("Pushed comparison image to Memory Bank: %s", phones_str)
        except Exception as e:
            logger.warning("Could not add comparison image to Memory Bank: %s", e)

        try:
            if hasattr(tool_context, "add_session_to_memory"):
                await tool_context.add_session_to_memory()
                logger.info("Triggered add_session_to_memory for comparison turn")
        except Exception as e:
            logger.warning("Could not trigger add_session_to_memory: %s", e)

    return {
        "status": "success",
        "primary_phone": primary_phone,
        "competitor_phones": competitors,
        "phones_compared": phones_str,
        "filename": filename,
        "image_url": public_url,
        "url": public_url,
        "memory_bank_status": "pushed_to_memory_bank",
    }

