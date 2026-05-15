# ASCII Video Bot HD

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-orange.svg)](https://ffmpeg.org)

Telegram bot that converts short videos into color ASCII art while preserving the original audio. Built with `aiogram 3.x`, `OpenCV`, `Pillow`, `NumPy`, and `FFmpeg`.

## Features
- Precise color mapping using a 48-level character gradient
- Automatic audio extraction and multiplexing into the final video
- Memory-efficient processing: frame generator instead of full RAM loading
- Vectorized NumPy rendering: 6-10x faster than traditional PIL loops
- Dynamic aspect ratio correction based on source video and font metrics
- Real-time progress updates and status messages
- Three quality presets with strict output size limits for Telegram
- Configurable debug mode and log levels via `.env`

## Tech Stack
- `aiogram 3.x` – Asynchronous Telegram Bot API framework
- `OpenCV` – Video I/O and frame extraction
- `Pillow` – Font rasterization and glyph generation
- `NumPy` – Vectorized mask blending and color composition
- `FFmpeg` – H.264/AAC encoding, bitrate control, and audio muxing
- `python-dotenv` – Secure environment configuration

## Prerequisites
- Python 3.10+
- **FFmpeg** must be installed on the host system and available in `$PATH`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: [Download](https://ffmpeg.org/download.html) and add `bin` to system `PATH`
  - Alpine (Docker): `apk add ffmpeg`

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/ascii-video-bot.git
   cd ascii-video-bot
2. Create a virtual environment and install dependencies
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
  Configure environment variables
   ```bash
     cp .env.example .env
```
4. Open .env and set your bot token:
   ```bash
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
   DEBUG_MODE=false
   LOG_LEVEL=INFO
5. Run the bot
   ```bash
   python bot.py


 Limitations

    Maximum video duration: 15 seconds
    Maximum output file size: 40 MB (Telegram upload limit)
    Rendering runs in a thread pool to avoid blocking the async event loop
    MemoryStorage is used by default; switch to RedisStorage for production deployments
