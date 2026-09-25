# ruff: noqa
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

import datetime
import logging
from zoneinfo import ZoneInfo

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.device_api import fetch_recent_devices
from app.firestore_db import (
    get_phone_specs_from_db,
    list_phones_from_db,
    save_phone_to_db,
    save_trade_in_inquiry_to_db,
)
from app.image_service import (
    generate_and_store_comparison_image,
    generate_and_store_image,
)

logger = logging.getLogger("phone_pilot.agent")

MODEL = "gemini-3.6-flash"


async def generate_smartphone_image(
    model_name: str,
    color: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generates a product image for a smartphone using gemini-3.1-flash-lite-image in the global region.

    Saves the image into session artifacts (visible in the Playground Artifacts panel)
    and uploads the image bytes directly to a public Cloud Storage bucket, returning
    the public HTTPS URL.

    Args:
        model_name: The full name of the smartphone (e.g. 'Google Pixel 11 Pro', 'Samsung Galaxy S25 Ultra').
        color: Optional color finish to render (e.g. 'Obsidian', 'Porcelain', 'Hazel', 'Titanium Gray').
        tool_context: ADK ToolContext automatically injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL (image_url) and image metadata.
    """
    return await generate_and_store_image(
        model_name=model_name,
        color=color,
        tool_context=tool_context,
    )


async def generate_comparison_image(
    primary_phone: str,
    competitor_phones: list[str] | str,
    tool_context: ToolContext = None,
) -> dict:
    """Generates a rich, Google-themed side-by-side product comparison image comparing smartphones.

    Uses gemini-3.1-flash-lite-image in the global region, saves the image as an artifact,
    uploads it to public Cloud Storage, and pushes the image details into the Memory Bank.

    Args:
        primary_phone: The user's primary/preferred smartphone (e.g. 'Google Pixel 11 Pro').
        competitor_phones: Competitor device(s) to compare side-by-side
            (e.g. ['Samsung Galaxy S25 Ultra', 'Apple iPhone 16 Pro'] or 'Samsung Galaxy S25 Ultra, Apple iPhone 16 Pro').
        tool_context: ADK ToolContext automatically injected by the framework.

    Returns:
        A dictionary containing the public HTTPS URL (image_url) and comparison metadata.
    """
    return await generate_and_store_comparison_image(
        primary_phone=primary_phone,
        competitor_phones=competitor_phones,
        tool_context=tool_context,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after agent turns to send session events to Vertex AI Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        logger.debug("Memory bank add_session_to_memory notification: %s", e)
    return None



def list_smartphones(brand: str = "") -> list[dict]:
    """Lists smartphones currently available in the Firestore database catalog.

    Args:
        brand: Optional brand name to filter by (e.g., 'Google', 'Apple', 'Samsung').
               If empty or omitted, returns all smartphones.

    Returns:
        A list of dictionaries with phone summaries (model_name, brand, price, features).
    """
    return list_phones_from_db(brand=brand)


def get_smartphone_details(model_name: str) -> dict:
    """Retrieves full specifications and features for a smartphone model from Firestore.

    Use this tool whenever a user asks about the features, specs, camera, battery,
    display, processor, or pricing of a specific phone (e.g., 'Google Pixel 11 Pro',
    'Pixel 10 Pro', 'iPhone 16 Pro', 'Galaxy S25 Ultra').

    Args:
        model_name: The name or model identifier of the smartphone to look up.

    Returns:
        A dictionary containing detailed specifications (price, display, processor,
        camera_system, battery, colors, storage_options, features, trade_in_value_base),
        or an error message if not found.
    """
    data = get_phone_specs_from_db(model_name)
    if not data:
        return {"error": f"Smartphone '{model_name}' was not found in the catalog."}
    return data


def add_or_update_smartphone(
    model_name: str,
    brand: str,
    price: float,
    display: str,
    processor: str,
    camera_system: str,
    battery: str,
    features: list[str],
) -> str:
    """Adds a new smartphone or updates an existing phone specification in the Firestore catalog.

    Args:
        model_name: The full name of the smartphone (e.g. 'Google Pixel 11 Pro').
        brand: The manufacturer brand (e.g. 'Google', 'Samsung', 'Apple').
        price: The retail price in USD.
        display: Display specifications (size, resolution, refresh rate, brightness).
        processor: Chipset / CPU details.
        camera_system: Main, ultrawide, telephoto, and front camera specifications.
        battery: Battery capacity and charging speed specs.
        features: Key selling points and software/hardware feature highlights.

    Returns:
        A confirmation message with the saved document ID.
    """
    doc_id = save_phone_to_db(
        {
            "model_name": model_name,
            "brand": brand,
            "price": price,
            "display": display,
            "processor": processor,
            "camera_system": camera_system,
            "battery": battery,
            "features": features,
            "in_stock": True,
        }
    )
    return f"Successfully saved smartphone '{model_name}' to Firestore with ID: {doc_id}."


def save_trade_in_inquiry(
    user_name: str,
    current_phone: str,
    condition: str,
    target_phone: str,
    estimated_value: float,
) -> str:
    """Records a customer's trade-in estimate inquiry into the Firestore database.

    Args:
        user_name: Name or handle of the user.
        current_phone: The device they currently own (e.g., 'Pixel 8 Pro').
        condition: Device condition (e.g. 'Flawless', 'Good', 'Cracked screen').
        target_phone: The phone they want to upgrade to (e.g., 'Google Pixel 11 Pro').
        estimated_value: Calculated estimated trade-in value in USD.

    Returns:
        A confirmation string with the recorded inquiry ID.
    """
    inquiry_id = save_trade_in_inquiry_to_db(
        {
            "user_name": user_name,
            "current_phone": current_phone,
            "condition": condition,
            "target_phone": target_phone,
            "estimated_value": estimated_value,
        }
    )
    return f"Trade-in inquiry recorded in Firestore with ID: {inquiry_id}."


# Agent 1: Product Advocate
# Enthusiastically presents all specs, positive highlights, and trade-in valuations
# for the phone the user is interested in.
product_advocate = Agent(
    name="product_advocate",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Enthusiastically presents all product features, specifications, product images, and trade-in valuation positively.",
    instruction=(
        "You are the Product Advocate agent for PhonePilot.\n"
        "Your mission: When the user inquires about or expresses interest in a smartphone or wearable (e.g., Google Pixel 11 Pro, Apple Watch, Galaxy phones, or the latest mobile releases):\n"
        "1. If the user asks about latest/newest mobile devices, recent releases, or wearables, call `fetch_recent_devices` to fetch live real-time release details from the public Phone Specs API.\n"
        "2. If inquiring about a specific catalog device, query Firestore via get_smartphone_details to retrieve specifications and pricing.\n"
        "3. Generate a photorealistic product visual for the smartphone using generate_smartphone_image (optionally specifying a color like Obsidian, Porcelain, or Hazel).\n"
        "4. Prominently embed the returned public image URL in your response using markdown syntax: ![Smartphone](<image_url>).\n"
        "5. Present ALL features, specs, camera capabilities, display quality, processor performance, battery life, and trade-in options in an enthusiastic, completely positive, structured point-by-point breakdown.\n"
        "6. Emphasize every strength and justify why the user's selected device is a great, compelling choice."
    ),
    tools=[
        get_smartphone_details,
        list_smartphones,
        fetch_recent_devices,
        generate_smartphone_image,
        save_trade_in_inquiry,
        add_or_update_smartphone,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    output_key="advocate_review",
)

# Agent 2: Competitor Analyst
# Analyzes competitor and alternative devices from the Firestore catalog and public specs API,
# critically comparing specs, suggesting which device could be a better buy,
# and generating a rich Google-themed side-by-side comparison image pushed to Memory Bank.
competitor_analyst = Agent(
    name="competitor_analyst",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Analyzes competitor and related products from Firestore and live specs API, provides smart buyer suggestions, and generates rich Google-themed side-by-side visual comparisons pushed to Memory Bank.",
    instruction=(
        "You are the Competitor Analyst & Smart Buyer Advisor for PhonePilot.\n"
        "Your mission: Following the Product Advocate's positive review, provide a sharp, objective critical analysis "
        "by comparing the user's preferred smartphone against alternative flagships and wearables in the market.\n"
        "1. Identify the smartphone or device preferred by the user.\n"
        "2. Query the Firestore catalog using list_smartphones and get_smartphone_details, and call `fetch_recent_devices` to discover the newest released competitor flagships and wearables across brands (e.g. Apple, Samsung, Google, Xiaomi).\n"
        "3. Provide a clear comparison table contrasting prices, processors, display specs, cameras, battery, and trade-in allowances.\n"
        "4. Provide a concrete analysis of which alternative device could be a BETTER BUY instead of the user's preferred model, "
        "highlighting specific reasons (e.g., raw performance/S-Pen on Galaxy S25/S26 Ultra, videography/ecosystem on iPhone 16/18 Pro, "
        "or budget savings with long support on Pixel 10 Pro).\n"
        "5. Conclude with your helpful, honest buyer recommendation and suggestion.\n"
        "6. MANDATORY LAST STEP - GENERATE COMPARISON IMAGE:\n"
        "   At the very end of your response (under your comparison table and final buyer suggestion), "
        "   you MUST ALWAYS call the `generate_comparison_image` tool to generate a rich, Google-themed graphic comparing the user's preferred phone "
        "   and the competing flagship(s) side-by-side (this image is also automatically saved as an artifact, uploaded to Cloud Storage, and pushed to the Memory Bank).\n"
        "   Never skip calling `generate_comparison_image`. Prominently embed this comparison image at the very end of your response using markdown syntax on its own line:\n"
        "   ![Product Comparison](<image_url>).\n"
        "If the user only sent a general greeting without specifying a product, briefly introduce yourself as the Competitor Analyst ready to evaluate alternatives once a model is chosen."
    ),
    tools=[
        list_smartphones,
        get_smartphone_details,
        fetch_recent_devices,
        generate_comparison_image,
        generate_smartphone_image,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
)

# Sequential Pipeline: Product Advocate runs first, Competitor Analyst runs second.
root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[product_advocate, competitor_analyst],
    description="PhonePilot sequential pipeline: Product Advocate showcases the chosen device positively, then Competitor Analyst evaluates rivals, suggests smarter buys, and generates a side-by-side comparison image pushed to Memory Bank.",
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
