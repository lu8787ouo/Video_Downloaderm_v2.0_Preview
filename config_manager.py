import os
import json

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "theme": "Dark",
    "language": "zh",
    "resolution": "1280x720",
    "download_path": os.getcwd(),
    "ad_image": ""
}

def load_config():
    """讀取設定檔，若不存在則建立預設設定檔並回傳預設值"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    """儲存設定檔"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
