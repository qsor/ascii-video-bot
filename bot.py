import asyncio
import tempfile
import logging
import cv2
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import converter
import config

logger = logging.getLogger("bot")

session = AiohttpSession(timeout=300)
bot = Bot(token=config.BOT_TOKEN, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class ProcessState(StatesGroup):
    waiting_for_quality = State()

def make_progress_bar(current, total, length=10):
    filled = int(current * length // total)
    return f"{'🟩'*filled}{'⬜'*(length-filled)} `{current}/{total} frames`"

async def safe_edit(msg, text, parse_mode="Markdown"):
    try:
        await msg.edit_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.debug(f"Edit failed: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "ASCII Video Bot HD\n\n"
        "Send video (up to 15 sec).\n"
        "Converts to colored symbols with audio.\n"
        "Choose quality after sending."
    )

@dp.message(F.video)
async def ask_quality(message: types.Message, state: FSMContext):
    if message.video.duration > config.MAX_DURATION_SEC:
        await message.answer(f"Video too long! Max: {config.MAX_DURATION_SEC} sec.")
        return

    await state.update_data(file_id=message.video.file_id, chat_id=message.chat.id)
    await state.set_state(ProcessState.waiting_for_quality)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Low", callback_data="quality:low", style="success"),
            InlineKeyboardButton(text="Medium", callback_data="quality:medium", style="primary"),
            InlineKeyboardButton(text="High", callback_data="quality:high", style="danger")
        ]
    ])
    await message.answer("Choose render quality:", reply_markup=kb)

@dp.callback_query(ProcessState.waiting_for_quality, F.data.startswith("quality:"))
async def start_processing(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    quality = callback.data.split(":")[1]
    data = await state.get_data()
    preset = config.QUALITY_PRESETS[quality]
    loop = asyncio.get_running_loop()

    def on_progress(cur, tot):
        asyncio.run_coroutine_threadsafe(
            safe_edit(status_msg, f"Step 3/4: Generating symbols...\nProgress: {make_progress_bar(cur, tot)}"),
            loop
        )

    status_msg = await callback.message.answer("Step 1/4: Loading video...\nProgress: `...`")

    with tempfile.TemporaryDirectory(dir=config.TEMP_DIR) as tmp:
        in_path = Path(tmp) / "in.mp4"
        out_path = Path(tmp) / "out.mp4"

        try:
            await bot.download(data["file_id"], destination=in_path)
            await safe_edit(status_msg, "Step 2/4: Extracting frames...")

            cap = cv2.VideoCapture(str(in_path))
            total_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            frames_iter = converter.extract_frames_iter(in_path, preset)
            await asyncio.to_thread(
                converter.render_ascii_video, 
                frames_iter, preset, in_path, out_path, on_progress, total_est
            )

            size_mb = out_path.stat().st_size / (1024**2)
            if size_mb > config.MAX_OUTPUT_MB:
                await safe_edit(status_msg, f"Size {size_mb:.1f} MB exceeds limit {config.MAX_OUTPUT_MB} MB. Try lower quality.")
                return

            await safe_edit(status_msg, "Step 4/4: Sending...")
            
            await callback.message.answer_video(
                video=FSInputFile(out_path, filename=f"ascii_{quality}.mp4"),
                caption=f"Done! Quality: {preset['label']}\nAudio preserved.",
                supports_streaming=True
            )
            await status_msg.delete()
            logger.info(f"Sent {quality} ({size_mb:.2f} MB)")

        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            await safe_edit(status_msg, f"Error: {str(e)[:150]}")
        finally:
            await state.clear()

async def main():
    logger.info("Starting ASCII Video Bot HD...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
