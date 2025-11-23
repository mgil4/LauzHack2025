import json
import os

PREF_FILE = "preferences.json"

DEFAULT_PREFS = {
    "family": True,
    "mail": True,
    "suspicious": True,
    "nighttime": True
}

def load_prefs():
    """Load preferences from JSON file, or create it if not found."""
    if not os.path.exists(PREF_FILE):
        save_prefs(DEFAULT_PREFS)
        return DEFAULT_PREFS.copy()

    with open(PREF_FILE, "r") as f:
        return json.load(f)

def save_prefs(prefs):
    """Save preferences to JSON file."""
    with open(PREF_FILE, "w") as f:
        json.dump(prefs, f, indent=4)

def get_prefs():
    """Return current machine preferences."""
    return load_prefs()

def set_pref(pref_name, value):
    """Update one preference."""
    prefs = load_prefs()
    prefs[pref_name] = value
    save_prefs(prefs)
