"""
Tobi AI - Menu-aware chatbot with surfer personality.
"""

import random
import logging
import httpx
from typing import Any

from .menu_data import MENU_DATA
from .config import settings

logger = logging.getLogger(__name__)


# Tobi's response templates
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


def find_menu_item(query: str) -> list[tuple[str, dict[str, Any]]]:
    """
    Search for menu items matching the query.

    Args:
        query: User's search query

    Returns:
        List of tuples containing (category, item_dict)
    """
    query_lower = query.lower()
    matches = []

    # Food term mappings (handle common variations and plurals)
    food_mappings = {
        "burger": ["burger", "burgers"],
        "pasta": ["pappardelle", "spaghetti", "mac"],
        "fish": ["salmon", "cod"],
        "chicken": ["chicken"],
        "steak": ["steak", "sirloin"],
        "fries": ["fries", "frite"],
        "salad": ["cobb"],
        "cocktail": ["martini", "negroni", "margarita", "fashioned", "sour"],
        "dessert": ["torte", "cake", "pudding"],
    }

    # Extract food-related keywords from query
    query_words = query_lower.split()
    food_keywords = [w.rstrip("s?!.,") for w in query_words if len(w) > 3]

    # Search through all menu categories
    for category in ["starters", "mains", "desserts", "drinks"]:
        for item in MENU_DATA[category]:
            item_name_lower = item["name"].lower()
            item_desc_lower = item["description"].lower()

            # Direct match in name or description
            if query_lower in item_name_lower or item_name_lower in query_lower:
                matches.append((category, item))
                continue
            elif query_lower in item_desc_lower:
                matches.append((category, item))
                continue

            # Check food mappings
            for keyword in food_keywords:
                if keyword in food_mappings:
                    # Check if any mapped term is in the item
                    if any(term in item_name_lower or term in item_desc_lower for term in food_mappings[keyword]):
                        matches.append((category, item))
                        break
                # Direct keyword match
                elif keyword in item_name_lower or keyword in item_desc_lower:
                    matches.append((category, item))
                    break

    logger.debug(f"Found {len(matches)} matches for query: {query}")
    return matches


def get_tobi_response(prompt: str) -> str:
    """
    Generate Tobi's response based on keywords and menu context.

    Args:
        prompt: User's message

    Returns:
        Tobi's response string
    """
    prompt_lower = prompt.lower()

    # Check for greetings (only if it's JUST a greeting)
    greeting_words = ["hi", "hello", "hey", "sup", "yo"]
    words = prompt_lower.split()
    if len(words) <= 3 and any(word in greeting_words for word in words):
        return random.choice(TOBI_RESPONSES["greeting"])

    # Search for specific menu items FIRST (more specific)
    menu_matches = find_menu_item(prompt)

    if menu_matches:
        # Found menu items - describe them
        if len(menu_matches) == 1:
            category, item = menu_matches[0]
            surfer_adjectives = ["rad", "killer", "awesome", "sick", "gnarly", "stellar", "epic"]
            adj = random.choice(surfer_adjectives)

            price_str = f"${item['price']:.2f}"
            return (
                f"Oh dude, the {item['name']} is {adj}! It's {item['description']} - "
                f"totally worth the {price_str}. Want me to add it to your order?"
            )
        else:
            # Multiple matches
            item_names = [item[1]["name"] for item in menu_matches[:3]]
            if len(item_names) == 2:
                return (
                    f"Nice! We've got {item_names[0]} and {item_names[1]}. "
                    f"Both are super tasty bro! Which one sounds good?"
                )
            else:
                items_str = ", ".join(item_names[:-1]) + f", and {item_names[-1]}"
                return f"Dude, we've got {items_str}! All of them are awesome. What are you feeling?"

    # Check if asking about menu in general
    if any(word in prompt_lower for word in ["menu", "what do you have", "what do you serve"]):
        return random.choice(TOBI_RESPONSES["menu"])

    # Check for recommendations
    if any(word in prompt_lower for word in ["recommend", "suggest", "best", "popular"]):
        popular_items = [
            "The Short Rib Pappardelle is insane bro - super popular!",
            "Can't go wrong with our House Smash Burger - it's a crowd favorite!",
            "The Truffle Fries are a total hit, dude!",
            "Everyone loves the Lobster Mac & Cheese - it's next level!",
        ]
        return random.choice(popular_items)

    # Check for price-related questions
    if any(word in prompt_lower for word in ["price", "cost", "how much", "expensive"]):
        return (
            "Our prices are super fair dude! Starters are around $11-16, "
            "mains are $16-32, and drinks are $11-14. Want to see the full menu?"
        )

    # Default responses
    return random.choice(TOBI_RESPONSES["default"])


async def get_ai_response(prompt: str) -> str:
    """
    Get response from local AI model via llama-server.

    Args:
        prompt: User's message

    Returns:
        AI-generated response string
    """
    if not settings.llama_server_url:
        logger.warning("llama_server_url not configured, falling back to templates")
        return get_tobi_response(prompt)

    # Build menu context for the AI
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

    # Call llama-server API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.llama_server_url}/completion",
                json={
                    "prompt": f"{menu_context}\n\nCustomer: {prompt}\nTobi:",
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "stop": ["\n", "Customer:", "Tobi:"],
                },
            )
            response.raise_for_status()
            result = response.json()
            ai_text = result.get("content", "").strip()

            if not ai_text:
                logger.warning("AI returned empty response, using template fallback")
                return get_tobi_response(prompt)

            logger.info(f"AI response: {ai_text}")
            return ai_text

    except Exception as e:
        logger.error(f"Error calling llama-server: {e}")
        logger.info("Falling back to template responses")
        return get_tobi_response(prompt)


async def get_tobi_response_async(prompt: str) -> str:
    """
    Main entry point for getting Tobi's response.
    Uses AI if configured, otherwise uses templates.

    Args:
        prompt: User's message

    Returns:
        Tobi's response string
    """
    if settings.use_local_ai and settings.llama_server_url:
        return await get_ai_response(prompt)
    else:
        return get_tobi_response(prompt)
