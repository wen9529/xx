import json
import os
from config import KEYS_FILE

def load_keys():
    if not os.path.exists(KEYS_FILE): return {}
    try:
        with open(KEYS_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f: json.dump(keys, f)
