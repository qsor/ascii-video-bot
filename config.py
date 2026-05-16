import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ascii_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found in .env")
    raise ValueError("Specify BOT_TOKEN in .env")

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")

QUALITY_PRESETS = {
    "low": {
        "width": 70, "fps": 12, "crf": 30, "maxrate": "1.2M", "bufsize": "2.5M",
        "label": "Low", "style": "success", "icon": None,
        "target_mb": 12
    },
    "medium": {
        "width": 95, "fps": 15, "crf": 26, "maxrate": "2.0M", "bufsize": "4M",
        "label": "Medium", "style": "primary", "icon": None,
        "target_mb": 25
    },
    "high": {
        "width": 110, "fps": 15, "crf": 24, "maxrate": "2.8M", "bufsize": "5M", 
        "label": "High", "style": "danger", "icon": None,
        "target_mb": 38
    }
}

ASCII_CHARS = " .,-;:i!lI?/|()1{}[]$*#%&8@"

BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
MAX_DURATION_SEC = 15
MAX_OUTPUT_MB = 40
BACKGROUND_COLOR = (10, 10, 10)
GAMMA = 2.2
