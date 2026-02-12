import json
import os
import logging
from config import KEYS_FILE

logger = logging.getLogger("StreamForge")

def load_keys():
    if not os.path.exists(KEYS_FILE): return {}
    try:
        with open(KEYS_FILE, 'r') as f: return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load keys: {e}")
        return {}

def save_keys(keys):
    try:
        with open(KEYS_FILE, 'w') as f: json.dump(keys, f)
        logger.info("Keys saved successfully")
    except Exception as e:
        logger.error(f"Failed to save keys: {e}")
