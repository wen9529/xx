import json
import os
import uuid
from config import BASE_DIR, logger

CACHE_FILE = os.path.join(BASE_DIR, "path_cache.json")
MAX_CACHE_SIZE = 2000

# 内存缓存，启动时从文件加载
_mem_cache = {}

def load_cache():
    global _mem_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                _mem_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load path cache: {e}")
            _mem_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_mem_cache, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save path cache: {e}")

def cache_path(path):
    """
    将路径存入缓存，返回短 ID。
    如果路径已存在，直接返回旧 ID。
    """
    # 反向查找：检查路径是否已有 ID
    for uid, p in _mem_cache.items():
        if p == path:
            return uid
            
    # 清理缓存 (简单的 FIFO 逻辑，实际只需保持大小不过大)
    if len(_mem_cache) > MAX_CACHE_SIZE:
        # 删除 1/3 旧数据
        keys_to_del = list(_mem_cache.keys())[:int(MAX_CACHE_SIZE/3)]
        for k in keys_to_del:
            del _mem_cache[k]
    
    # 生成新 ID
    short_id = str(uuid.uuid4())[:8]
    _mem_cache[short_id] = path
    save_cache()
    return short_id

def get_path(short_id):
    """根据短 ID 获取路径"""
    return _mem_cache.get(short_id)

# 初始化加载
load_cache()
