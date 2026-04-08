"""
Tobi AI — core chatbot response logic.

This module is responsible for producing Tobi's replies.  It has three modes
that form a layered fallback chain:

  Mode 1 — AI with context  (get_ai_response_with_context)   ← PRIMARY
      Calls the local Llama-3 model via llama-server with:
        • A system prompt (personality + full menu)
        • The last 10 messages from the DB (conversation memory)
        • The user's current message
      Used by main.py when llama_server_url is configured.

  Mode 2 — AI without context  (get_ai_response)             ← LEGACY
      Same HTTP call but without conversation history.
      Used by get_tobi_response_async when USE_LOCAL_AI=true.
      Kept for backwards compatibility; prefer Mode 1 for new work.

  Mode 3 — Template fallback  (get_tobi_response)            ← FALLBACK
      Pure Python keyword matching + hardcoded response strings.
      Used when:
        • llama_server_url is not configured (template-only mode)
        • The AI call times out (>60 s)
        • The AI returns an empty response
        • Any other unexpected error from the AI server
      Guarantees Tobi always has something useful to say.

Flow in production (AI enabled):
  POST /chat → get_ai_response_with_context → llama-server
                                            ↘ (on error) get_tobi_response

Flow in template mode (USE_LOCAL_AI=false or llama_server_url unset):
  POST /chat → get_tobi_response_async → get_tobi_response
"""

import random
import logging
import httpx
from typing import Any

from .menu_data import MENU_DATA
from .config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template response bank
# ---------------------------------------------------------------------------
# Pre-written replies Tobi uses when the AI model is unavailable.
# Multiple options per category give variety so the same phrasing doesn't
# repeat on every request.
# ---------------------------------------------------------------------------
TOBI_RESPONSES = {
    "greeting": [
        "Hey dude! Welcome to The Common House! What can I get ya today?",
        "Yo! Stoked you're here bro! Ready to order some killer food?",
        "Hey there! Tobi here, ready to hook you up with some tasty grub!",
    ],
    "menu": [
        "Our menu is totally rad! We got everything from Truffle Fries to Lobster Mac. What sounds good to you?",
        "Bro, we've got the sickest menu! Check out our starters, mains, desserts, and drinks!",
    ],
    "order": [
        "Awesome choice dude! I'll get that order in for ya!",
        "Sweet! That's gonna be delicious, bro!",
    ],
    "default": [
        "Right on! Anything else I can help you with?",
        "Cool cool! What else can I do for ya?",
        "For sure! Let me know if you need anything else!",
    ],
}


# ---------------------------------------------------------------------------
# Menu search helper
# ---------------------------------------------------------------------------

def find_menu_item(query: str) -> list[tuple[str, dict[str, Any]]]:
    """
    Search the menu for items that match the user's query.

    The search has two passes:
      1. Direct string match — checks if the query (or individual keywords) appear
         in the item name or description.
      2. Semantic mapping — maps casual food terms to formal item names so a user
         asking "do you have pasta?" will match "Short Rib Pappardelle" even though
         the word "pasta" doesn't appear in that item's name.

    Args:
        query: The full user message, e.g. "do you have any fish dishes?"

    Returns:
        A list of (category, item_dict) tuples for every matching item.
        Empty list if nothing matched.
    """
    query_lower = query.lower()
    matches = []

    # Map common/casual food words → terms that appear in the menu data.
    # Add entries here when users frequently ask for something but the exact
    # word doesn't appear in the item name or description.
    food_mappings = {
        "burger":   ["burger", "burgers"],
        "pasta":    ["pappardelle", "spaghetti", "mac"],
        "fish":     ["salmon", "cod"],
        "chicken":  ["chicken"],
        "steak":    ["steak", "sirloin"],
        "fries":    ["fries", "frite"],
        "salad":    ["cobb"],
        "cocktail": ["martini", "negroni", "margarita", "fashioned", "sour"],
        "dessert":  ["torte", "cake", "pudding"],
    }

    # Strip punctuation/plurals from each word so "burgers?" → "burger"
    query_words = query_lower.split()
    food_keywords = [w.rstrip("s?!.,") for w in query_words if len(w) > 3]

    for category in ["starters", "mains", "desserts", "drinks"]:
        for item in MENU_DATA[category]:
            item_name_lower = item["name"].lower()
            item_desc_lower = item["description"].lower()

            # Pass 1: direct substring match on name or description
            if query_lower in item_name_lower or item_name_lower in query_lower:
                matches.append((category, item))
                continue
            elif query_lower in item_desc_lower:
                matches.append((category, item))
                continue

            # Pass 2: keyword + mapping match
            for keyword in food_keywords:
                if keyword in food_mappings:
                    # Use the mapping to expand the keyword to related terms
                    if any(term in item_name_lower or term in item_desc_lower
                           for term in food_mappings[keyword]):
                        matches.append((category, item))
                        break
                elif keyword in item_name_lower or keyword in item_desc_lower:
                    # Direct keyword hit (no mapping needed)
                    matches.append((category, item))
                    break

    logger.debug(f"find_menu_item: '{query}' → {len(matches)} match(es)")
    return matches


# ---------------------------------------------------------------------------
# Mode 3 — Template fallback responses
# ---------------------------------------------------------------------------

def get_tobi_response(prompt: str) -> str:
    """
    Generate a response using keyword matching and hardcoded templates.

    This is the guaranteed-available fallback when the AI model is unreachable
    or disabled.  The matching priority is:

      1. Greeting detection (short messages only, ≤3 words)
      2. Specific menu item search (most specific → most useful)
      3. General menu question ("what do you have?")
      4. Recommendation request ("what do you recommend?")
      5. Price question ("how much is…?")
      6. Default catch-all

    Args:
        prompt: The user's raw message.

    Returns:
        A Tobi-style response string.
    """
    prompt_lower = prompt.lower()

    # Only treat very short messages as pure greetings to avoid false positives
    # on messages like "hey, what burgers do you have?"
    greeting_words = ["hi", "hello", "hey", "sup", "yo"]
    words = prompt_lower.split()
    if len(words) <= 3 and any(word in greeting_words for word in words):
        return random.choice(TOBI_RESPONSES["greeting"])

    # Try to find specific menu items first — more helpful than a generic reply
    menu_matches = find_menu_item(prompt)

    if menu_matches:
        if len(menu_matches) == 1:
            # Single match: give a rich description with price
            category, item = menu_matches[0]
            surfer_adjectives = ["rad", "killer", "awesome", "sick", "gnarly", "stellar", "epic"]
            adj = random.choice(surfer_adjectives)
            price_str = f"${item['price']:.2f}"
            return (
                f"Oh dude, the {item['name']} is {adj}! It's {item['description']} - "
                f"totally worth the {price_str}. Want me to add it to your order?"
            )
        else:
            # Multiple matches: list up to 3 options and let the user choose
            item_names = [item[1]["name"] for item in menu_matches[:3]]
            if len(item_names) == 2:
                return (
                    f"Nice! We've got {item_names[0]} and {item_names[1]}. "
                    f"Both are super tasty bro! Which one sounds good?"
                )
            else:
                items_str = ", ".join(item_names[:-1]) + f", and {item_names[-1]}"
                return f"Dude, we've got {items_str}! All of them are awesome. What are you feeling?"

    # General menu inquiry
    if any(word in prompt_lower for word in ["menu", "what do you have", "what do you serve"]):
        return random.choice(TOBI_RESPONSES["menu"])

    # Recommendation / best dish questions
    if any(word in prompt_lower for word in ["recommend", "suggest", "best", "popular"]):
        popular_items = [
            "The Short Rib Pappardelle is insane bro - super popular!",
            "Can't go wrong with our House Smash Burger - it's a crowd favorite!",
            "The Truffle Fries are a total hit, dude!",
            "Everyone loves the Lobster Mac & Cheese - it's next level!",
        ]
        return random.choice(popular_items)

    # Price-related questions
    if any(word in prompt_lower for word in ["price", "cost", "how much", "expensive"]):
        return (
            "Our prices are super fair dude! Starters are around $11-16, "
            "mains are $16-32, and drinks are $11-14. Want to see the full menu?"
        )

    # Nothing matched — use a generic, friendly default
    return random.choice(TOBI_RESPONSES["default"])


# ---------------------------------------------------------------------------
# Mode 2 — Legacy AI call (no conversation history)
# ---------------------------------------------------------------------------

async def get_ai_response(prompt: str) -> str:
    """
    Send a single-turn request to the Llama-3 model via llama-server.

    This is the older, simpler variant that does NOT include conversation history.
    It constructs the menu context inline rather than using prompts.py.

    Kept for use by get_tobi_response_async (the USE_LOCAL_AI=true code path).
    For new work, prefer get_ai_response_with_context which supports memory.

    Args:
        prompt: The user's current message.

    Returns:
        AI-generated text, or a template fallback on any error.
    """
    if not settings.llama_server_url:
        logger.warning("llama_server_url not configured, falling back to templates")
        return get_tobi_response(prompt)

    # Build a self-contained system prompt with the full menu embedded
    menu_context = f"""You are Tobi, a super chill surfer dude who works at {settings.restaurant_name}.
You're laid-back, friendly, and use casual surfer language (dude, bro, rad, sick, gnarly, etc).

Our Menu:

STARTERS:
"""
    for item in MENU_DATA["starters"]:
        menu_context += f"- {item['name']}: {item['description']} (${item['price']:.2f})\n"

    menu_context += "\nMAINS:\n"
    for item in MENU_DATA["mains"]:
        menu_context += f"- {item['name']}: {item['description']} (${item['price']:.2f})\n"

    menu_context += "\nDESSERTS:\n"
    for item in MENU_DATA["desserts"]:
        menu_context += f"- {item['name']}: {item['description']} (${item['price']:.2f})\n"

    menu_context += "\nDRINKS:\n"
    for item in MENU_DATA["drinks"]:
        menu_context += f"- {item['name']}: {item['description']} (${item['price']:.2f})\n"

    menu_context += "\n\nRespond to the customer in 1-2 short sentences. Keep it casual and fun!"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.llama_server_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "system", "content": menu_context},
                        {"role": "user",   "content": prompt},
                    ],
                    "max_tokens": 100,
                    "temperature": 0.7,
                    # Stop tokens prevent the model from continuing beyond the reply
                    "stop": ["\n\n", "Customer:", "User:"],
                },
            )
            response.raise_for_status()
            result = response.json()
            ai_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not ai_text:
                logger.warning("AI returned empty response, using template fallback")
                return get_tobi_response(prompt)

            logger.info(f"AI response: {ai_text}")
            return ai_text

    except httpx.TimeoutException as e:
        logger.error(f"Timeout calling llama-server (60s exceeded): {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)
    except httpx.ConnectError as e:
        logger.error(f"Connection error to llama-server: {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)
    except Exception as e:
        logger.error(f"Unexpected error calling llama-server: {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)


# ---------------------------------------------------------------------------
# Mode 1 — Primary AI call with conversation history (context-aware)
# ---------------------------------------------------------------------------

async def get_ai_response_with_context(prompt: str, session_id: str, db) -> str:
    """
    Send a multi-turn request to the Llama-3 model, including conversation history.

    This is the main function called by the /chat endpoint.  It:
      1. Queries the DB for the last 10 messages in this session.
      2. Builds an OpenAI-style messages array:
           [system prompt + menu]  +  [last 10 DB messages]  +  [current user message]
      3. POSTs the array to llama-server at /v1/chat/completions.
      4. Falls back to template responses on any error.

    The 10-message window is a balance between context quality and prompt size.
    Llama-3-8B has a 4096-token context window; the system prompt already uses
    ~600 tokens, leaving ~3400 for history.  10 short messages typically fit
    well within that budget.

    Args:
        prompt:     The user's current message (already stored in DB by caller).
        session_id: UUID identifying the current conversation.
        db:         SQLAlchemy session injected by FastAPI's Depends(get_db).

    Returns:
        AI-generated text, or a template fallback on any error.
    """
    from app.prompts import get_system_prompt
    from app.models import DBMessage

    if not settings.llama_server_url:
        logger.warning("llama_server_url not configured, falling back to templates")
        return get_tobi_response(prompt)

    # Fetch the last 10 messages (desc so we get the most recent), then reverse
    # back to chronological order for the messages array.
    # Note: the current user message is NOT yet in the DB at this point because
    # main.py stores it, then calls this function, so history contains prior turns only.
    history = (
        db.query(DBMessage)
        .filter(DBMessage.session_id == session_id)
        .order_by(DBMessage.timestamp.desc())
        .limit(10)
        .all()
    )

    # Start with the system prompt (personality + rules + full menu)
    messages = [
        {"role": "system", "content": get_system_prompt(include_menu=True)}
    ]

    # Append historical messages in chronological order (oldest first)
    for msg in reversed(history):
        messages.append({"role": msg.role, "content": msg.content})

    # Append the current user turn last
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.llama_server_url}/v1/chat/completions",
                json={
                    "messages": messages,
                    "max_tokens": 150,      # Slightly higher than Mode 2 for richer replies
                    "temperature": 0.6,     # Lower than Mode 2 for more consistent personality
                    "stop": ["\n\n", "Customer:", "User:"],
                },
            )
            response.raise_for_status()
            result = response.json()
            ai_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not ai_text:
                logger.warning("AI returned empty response, using template fallback")
                return get_tobi_response(prompt)

            logger.info(f"AI response with context ({len(history)} msgs history): {ai_text}")
            return ai_text

    except httpx.TimeoutException as e:
        logger.error(f"Timeout calling llama-server (60s exceeded): {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)
    except httpx.ConnectError as e:
        logger.error(f"Connection error to llama-server: {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)
    except Exception as e:
        logger.error(f"Unexpected error calling llama-server: {e}", exc_info=True)
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)


# ---------------------------------------------------------------------------
# Public async entry point (used when USE_LOCAL_AI=true without DB context)
# ---------------------------------------------------------------------------

async def get_tobi_response_async(prompt: str) -> str:
    """
    High-level entry point: routes to AI or templates based on configuration.

    This function is called in contexts where we don't have a DB session
    (e.g. simple scripts or tests).  For the main chat endpoint, main.py calls
    get_ai_response_with_context directly to pass the DB session.

    Args:
        prompt: The user's message.

    Returns:
        Tobi's response string.
    """
    if settings.use_local_ai and settings.llama_server_url:
        # Route to AI (Mode 2 — no conversation history)
        return await get_ai_response(prompt)
    else:
        # Route to templates (Mode 3 — always available)
        return get_tobi_response(prompt)
