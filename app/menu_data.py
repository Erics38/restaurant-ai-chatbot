"""
Menu data loader.

On startup, get_menu() is called once and the result is cached in MENU_DATA.

Two sources are supported:
  1. MENU_URL env var — fetch JSON from a public URL (custom restaurant menu)
  2. Built-in default  — The Common House menu defined at the bottom of this file

Expected JSON structure for a custom menu:
  {
    "restaurant_name": "My Restaurant",
    "starters":  [{"name": "...", "description": "...", "price": 0.00}, ...],
    "mains":     [...],
    "desserts":  [...],
    "drinks":    [...]
  }

Any categories present in the JSON will be displayed. Missing categories are
ignored. Extra fields are passed through to the frontend unchanged.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MENU_DATA
# ---------------------------------------------------------------------------
# Structure:
#   {
#     "restaurant_name": str,
#     "<category>": [
#       {"name": str, "description": str, "price": float},
#       ...
#     ],
#     ...
#   }
#
# Categories: starters | mains | desserts | drinks
# Prices are in USD.
# ---------------------------------------------------------------------------

_DEFAULT_MENU: dict[str, Any] = {
    "restaurant_name": "The Common House",

    # -----------------------------------------------------------------------
    # Starters — $11–16
    # -----------------------------------------------------------------------
    "starters": [
        {"name": "Truffle Fries", "description": "Parmesan, rosemary, truffle oil", "price": 12.00},
        {"name": "Spicy Tuna Tartare", "description": "Ahi tuna, avocado, sesame-soy dressing", "price": 16.00},
        {"name": "Crispy Brussels", "description": "Balsamic glaze, chili flakes, lemon zest", "price": 11.00},
        {"name": "Burrata & Tomato", "description": "Heirloom tomato, basil oil, sea salt", "price": 14.00},
        {"name": "Smoked Chicken Flatbread", "description": "Arugula, goat cheese, roasted red pepper", "price": 13.00},
    ],

    # -----------------------------------------------------------------------
    # Mains — $16–32
    # -----------------------------------------------------------------------
    "mains": [
        {"name": "Seared Salmon Bowl", "description": "Brown rice, avocado, miso vinaigrette", "price": 24.00},
        {"name": "Short Rib Pappardelle", "description": "Red wine braise, parmesan, gremolata", "price": 26.00},
        {"name": "Buttermilk Fried Chicken Sandwich",
         "description": "Pickles, garlic aioli, brioche bun", "price": 18.00},
        {"name": "Miso Glazed Cod", "description": "Snap peas, jasmine rice, sesame", "price": 28.00},
        {"name": "Steak Frites", "description": "8 oz sirloin, chimichurri, hand-cut fries", "price": 32.00},
        {"name": "House Smash Burger", "description": "Double patty, cheddar, caramelized onion", "price": 16.00},
        {"name": "Roasted Mushroom Risotto", "description": "Truffle oil, parmesan, thyme", "price": 22.00},
        {"name": "Grilled Chicken Cobb", "description": "Bacon, egg, blue cheese, avocado ranch", "price": 19.00},
        {"name": "Lobster Mac & Cheese", "description": "Cavatappi, gruyère, breadcrumbs", "price": 29.00},
        {"name": "Spaghetti Pomodoro", "description": "San Marzano tomato, basil, pecorino", "price": 17.00},
    ],

    # -----------------------------------------------------------------------
    # Desserts — $7–9
    # -----------------------------------------------------------------------
    "desserts": [
        {"name": "Warm Chocolate Torte",   "description": "Sea salt, vanilla cream",              "price": 9.00},
        {"name": "Olive Oil Cake",         "description": "Lemon glaze, whipped mascarpone",      "price": 8.00},
        {"name": "Salted Caramel Pudding", "description": "Toasted pecans, chantilly",            "price": 7.00},
    ],

    # -----------------------------------------------------------------------
    # Drinks (cocktails) — $11–14
    # -----------------------------------------------------------------------
    "drinks": [
        {"name": "Old Fashioned",    "description": "Bourbon, bitters, sugar, orange peel",   "price": 12.00},
        {"name": "Espresso Martini", "description": "Vodka, espresso, coffee liqueur",         "price": 14.00},
        {"name": "Negroni",          "description": "Gin, Campari, sweet vermouth",            "price": 13.00},
        {"name": "Margarita",        "description": "Tequila, lime, orange liqueur",           "price": 11.00},
        {"name": "Whiskey Sour",     "description": "Bourbon, lemon, egg white",               "price": 12.00},
    ],
}


def _load_menu() -> dict[str, Any]:
    """
    Return the menu to use for this deployment.

    If MENU_URL is set, fetch JSON from that URL and return it.
    Falls back to the built-in default menu on any error.
    """
    from app.config import settings
    if not settings.menu_url:
        return _DEFAULT_MENU

    try:
        import urllib.request
        import json
        logger.info(f"Loading custom menu from {settings.menu_url}")
        with urllib.request.urlopen(settings.menu_url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        logger.info(f"Custom menu loaded: {list(data.keys())}")
        return data
    except Exception as e:
        logger.error(f"Failed to load menu from {settings.menu_url}: {e} — using default menu")
        return _DEFAULT_MENU


# Single shared instance — loaded once at startup
MENU_DATA: dict[str, Any] = _load_menu()
