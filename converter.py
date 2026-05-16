import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess
import shutil
import logging
from pathlib import Path
import config

logger = logging.getLogger("converter")

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(config.FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.load_default()

def extract_frames_iter(video_path: Path, preset: dict):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("OpenCV cannot open video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    src_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    src_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_aspect = src_w / src_h if src_h > 0 else 16/9

    target_h = max(1, int(preset["width"] / src_aspect * 0.62))

    dur = total / fps if fps else 0
    if dur > config.MAX_DURATION_SEC:
        cap.release()
        raise ValueError(f"Duration {dur:.1f}s exceeds {config.MAX_DURATION_SEC}s")

    step = max(1, int(fps / preset["fps"]))
    idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            resized = cv2.resize(frame, (preset["width"], target_h), interpolation=cv2.INTER_LANCZOS4)
            yield cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        idx += 1
    cap.release()

def render_ascii_video(frames_iter, preset, audio_path, out_path, progress_callback=None, total_frames=None):
    first_frame = next(frames_iter, None)
    if first_frame is None:
        raise ValueError("No frames")

    preset_w = preset["width"]
    src_h, src_w, _ = first_frame.shape
    src_aspect = src_w / src_h if src_h > 0 else 16/9
    
    font = _load_font(max(8, int(preset_h := 1) * 1.1))
    tmp = Image.new("RGB", (1,1), (0,0,0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0,0), "M", font=font)
    cw, ch = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    font_aspect = cw / ch
    preset_h = max(1, int(preset_w / src_aspect * font_aspect))
    out_w, out_h = preset_w * cw, preset_h * ch

    glyphs = {}
    for char in config.ASCII_CHARS:
        char_img = Image.new("L", (cw, ch), 0)
        draw_char = ImageDraw.Draw(char_img)
        draw_char.text((0, 0), char, font=font, fill=255)
        glyphs[char] = np.array(char_img, dtype=np.float32) / 255.0

    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(6,6))
    chars = np.array(list(config.ASCII_CHARS))
    bg = np.array(config.BACKGROUND_COLOR, dtype=np.float32) / 255.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, preset["fps"], (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError("VideoWriter init failed")

    frame_buffer = [first_frame]
    frame_buffer.extend(frames_iter)
    total = len(frame_buffer)

    logger.info(f"Rendering {total} frames ({preset['label']})...")

    for i, frame in enumerate(frame_buffer):
        if frame.shape[0] != preset_h or frame.shape[1] != preset_w:
            frame = cv2.resize(frame, (preset_w, preset_h), interpolation=cv2.INTER_LANCZOS4)
            
        gray = clahe.apply(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY))
        idx_map = np.clip((gray.astype(np.float32)/255.0*(len(chars)-1)).astype(np.uint8), 0, len(chars)-1)
        grid = chars[idx_map]

        colors = frame.reshape(-1, 3).reshape(preset_h, preset_w, 3).astype(np.float32) / 255.0

        mask_rows = []
        for r in range(preset_h):
            row_masks = []
            for c in range(preset_w):
                row_masks.append(glyphs[grid[r, c]])
            mask_rows.append(np.hstack(row_masks))
        full_mask = np.vstack(mask_rows)

        full_color = np.repeat(np.repeat(colors, ch, axis=0), cw, axis=1)
        blended = bg * (1 - full_mask[:,:,None]) + full_color * full_mask[:,:,None]
        img_array = np.clip(blended * 255, 0, 255).astype(np.uint8)

        writer.write(cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

        if progress_callback:
            progress_callback(i+1, total_frames or total)

    writer.release()

    final_path = out_path.with_name(out_path.stem + "_final.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(out_path), "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(preset["crf"]),
        "-c:a", "aac", "-b:a", "96k", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-b:v", preset["maxrate"], "-maxrate", preset["maxrate"], "-bufsize", preset["bufsize"],
        "-tune", "stillimage",
        str(final_path)
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        if final_path.exists():
            out_path.unlink()
            final_path.rename(out_path)
            logger.info(f"Compressed: CRF={preset['crf']}, maxrate={preset['maxrate']}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"FFmpeg failed: {e.stderr.decode()}")
    except Exception as e:
        logger.warning(f"FFmpeg error: {e}")

    if progress_callback:
        progress_callback(total, total_frames or total)
    logger.info("Render complete")
