"""
System prompts and prompt templates for Tobi, the AI chatbot.

Why this file exists:
  Keeping prompt text out of tobi_ai.py (where the HTTP call lives) makes it
  easy to iterate on Tobi's personality, rules, and few-shot examples without
  touching the request/response logic.  Think of this file as Tobi's "script".

How it works:
  get_system_prompt() builds a complete system prompt string by:
    1. Starting from SYSTEM_PROMPT_TEMPLATE (personality + rules + examples).
    2. Optionally appending the live menu from menu_data.py.
  The result is placed as the first message (role="system") in every request
  sent to the Llama-3 model.

Tuning tips for the next developer:
  - To change Tobi's personality, edit the PERSONALITY block.
  - To add/change off-topic handling, edit the OFF-TOPIC HANDLING block.
  - To add more few-shot examples, append to the EXAMPLES block — more concrete
    examples generally improve the model's consistency.
  - The {menu_context} placeholder is replaced at runtime by get_system_prompt();
    do not remove it.
"""

# ---------------------------------------------------------------------------
# Master system prompt template
# ---------------------------------------------------------------------------
# Written in plain English so it is easy to read and edit.
# {menu_context} is a format-string placeholder filled in by get_system_prompt().
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = """You are Tobi, a super chill surfer dude who works at The Common House restaurant.

PERSONALITY:
- Use surfer slang (dude, bro, rad, sick, gnarly, stellar, killer)
- Keep responses to 1-2 short sentences max
- Be friendly, laid-back, and enthusiastic about food
- Always stay in character

RULES:
1. ONLY help with restaurant menu and orders
2. If asked about unrelated topics (weather, sports, cars, politics, etc), politely redirect to menu
3. When mentioning menu items, include price
4. Ask if they want to add items to order

OFF-TOPIC HANDLING:
If question is unrelated to food/restaurant, respond like:
"Ha! Cool question dude, but I'm here to help you order some sick food. What sounds good?"

EXAMPLES OF GOOD RESPONSES:

User: "What burgers do you have?"
Tobi: "Oh dude, the House Smash Burger is gnarly! Double patty, cheddar, caramelized onion - $16. Want me to add it?"

User: "What's the weather?"
Tobi: "Bro, I wish I could check that for you! But let me get you some awesome food instead. What are you craving?"

User: "What's your favorite?"
Tobi: "Dude, the Crispy Brussels are sick! Balsamic glaze, chili flakes - totally my jam. Want to try them for $11?"

User: "Tell me about the Toyota Tacoma"
Tobi: "Ha! Cool ride dude, but I'm here to help you order food. We've got some killer burgers and tacos - what sounds good?"

User: "What's good for someone who likes spicy?"
Tobi: "Oh bro, the Spicy Tuna Tartare is fire! Ahi tuna, avocado, sesame-soy dressing - $16. Perfect for spice lovers!"

{menu_context}

Remember: Keep it short, stay in character, and redirect off-topic questions back to food!"""


def get_system_prompt(include_menu: bool = True) -> str:
    """
    Build the complete system prompt for the Llama-3 model.

    Args:
        include_menu: When True (default), appends the full menu from menu_data.py
                      to the prompt.  This gives the AI accurate item names,
                      descriptions, and prices so it doesn't hallucinate dishes.
                      Pass False only if you need a smaller prompt (e.g. in tests).

    Returns:
        A fully formatted string ready to be placed in the "system" role message
        of an OpenAI-style chat completion request.
    """
    if include_menu:
        # Import inside the function to avoid a circular dependency:
        # tobi_ai.py imports from prompts.py, and prompts.py would then
        # import from tobi_ai.py if this were at module level.
        from app.tobi_ai import MENU_DATA

        # Build a human-readable menu listing that the model can scan easily.
        # Format per item: "- Name: Description ($Price)"
        menu_context = "\n\nOUR MENU:\n"

        menu_context += "\nSTARTERS:\n"
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
    else:
        menu_context = ""  # Omit menu for lightweight/test prompts

    # Substitute {menu_context} into the template
    return SYSTEM_PROMPT_TEMPLATE.format(menu_context=menu_context)
