"""
The Common House menu data.

This is the single source of truth for every menu item in the application.
It is used in three places:
  1. GET /menu endpoint  — returns this dict to the frontend for rendering the
                           menu modal.
  2. app/prompts.py      — injects the full menu into the Llama-3 system prompt
                           so the AI knows what to recommend and what prices to quote.
  3. app/tobi_ai.py      — the template fallback searches this dict to find items
                           that match a user's query (e.g. "do you have salmon?").

To add a new item: append a dict with "name", "description", and "price" to the
relevant category list.  No other code needs to change — prompts and search pick
it up automatically.

To add a new category: add a new key here and update the category loops in
prompts.py and tobi_ai.py to include it.
"""

from typing import Any

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

MENU_DATA: dict[str, Any] = {
    "restaurant_name": "The Common House",

    # -----------------------------------------------------------------------
    # Starters — $11–16
    # -----------------------------------------------------------------------
    "starters": [
        {"name": "Truffle Fries",            "description": "Parmesan, rosemary, truffle oil",                    "price": 12.00},
        {"name": "Spicy Tuna Tartare",        "description": "Ahi tuna, avocado, sesame-soy dressing",            "price": 16.00},
        {"name": "Crispy Brussels",           "description": "Balsamic glaze, chili flakes, lemon zest",          "price": 11.00},
        {"name": "Burrata & Tomato",          "description": "Heirloom tomato, basil oil, sea salt",              "price": 14.00},
        {"name": "Smoked Chicken Flatbread",  "description": "Arugula, goat cheese, roasted red pepper",          "price": 13.00},
    ],

    # -----------------------------------------------------------------------
    # Mains — $16–32
    # -----------------------------------------------------------------------
    "mains": [
        {"name": "Seared Salmon Bowl",                "description": "Brown rice, avocado, miso vinaigrette",          "price": 24.00},
        {"name": "Short Rib Pappardelle",             "description": "Red wine braise, parmesan, gremolata",           "price": 26.00},
        {"name": "Buttermilk Fried Chicken Sandwich", "description": "Pickles, garlic aioli, brioche bun",             "price": 18.00},
        {"name": "Miso Glazed Cod",                   "description": "Snap peas, jasmine rice, sesame",                "price": 28.00},
        {"name": "Steak Frites",                      "description": "8 oz sirloin, chimichurri, hand-cut fries",      "price": 32.00},
        {"name": "House Smash Burger",                "description": "Double patty, cheddar, caramelized onion",       "price": 16.00},
        {"name": "Roasted Mushroom Risotto",          "description": "Truffle oil, parmesan, thyme",                   "price": 22.00},
        {"name": "Grilled Chicken Cobb",              "description": "Bacon, egg, blue cheese, avocado ranch",         "price": 19.00},
        {"name": "Lobster Mac & Cheese",              "description": "Cavatappi, gruyère, breadcrumbs",                "price": 29.00},
        {"name": "Spaghetti Pomodoro",                "description": "San Marzano tomato, basil, pecorino",            "price": 17.00},
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
