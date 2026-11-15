import asyncio
import json
import logging
import os
import sqlite3
import time
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. .env faylga bot tokenini kiriting.")

ROOT = Path(__file__).parent
DB_PATH = ROOT / "results.db"
QUESTIONS_PATH = ROOT / "data" / "questions.json"
QUESTION_TIME = 60

with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
    BANKS = json.load(f)

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Active sessions are kept in memory; results are saved in SQLite.
sessions = {}

def db_init():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT,
                username TEXT,
                test_type TEXT NOT NULL,
                score REAL NOT NULL,
                correct INTEGER NOT NULL,
                total INTEGER NOT NULL,
                finished_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
db_init()

def level_for(score):
    if score < 35:
        return "A1 — Beginner"
    if score < 50:
        return "A2 — Elementary"
    if score < 65:
        return "B1 — Intermediate"
    if score < 80:
        return "B2 — Upper-Intermediate"
    return "C1 — Advanced"

def home_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="🟢 Beginner testi", callback_data="start:beginner")
    b.button(text="🔵 Intermediate testi", callback_data="start:intermediate")
    b.adjust(1)
    return b.as_markup()

def question_keyboard(index, total, selected=None):
    b = InlineKeyboardBuilder()
    for key in ("A", "B", "C", "D"):
        prefix = "🔘 " if selected == key else ""
        b.button(text=f"{prefix}{key}", callback_data=f"answer:{key}")
    b.adjust(4)
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingisi", callback_data="nav:prev"))
    if index < total - 1:
        nav.append(InlineKeyboardButton(text="Keyingisi ➡️", callback_data="nav:next"))
    if nav:
        b.row(*nav)
    b.row(InlineKeyboardButton(text="🏁 Yakunlash", callback_data="finish"))
    return b.as_markup()

def get_question_text(session):
    questions = session["questions"]
    i = session["index"]
    q = questions[i]
    remaining = max(0, int(session["deadline"] - time.time()))
    lines = [
        f"<b>{session['label']}</b>",
        f"📘 Savol <b>{i+1}/{len(questions)}</b>",
        f"⏳ Qolgan vaqt: <b>{remaining} soniya</b>",
        "",
        q["question"],
        ""
    ]
    for key, value in q["options"].items():
        lines.append(f"<b>{key})</b> {value}")
    lines += ["", "Javobni tanlang. Har bir savol uchun 60 soniya beriladi."]
    return "\n".join(lines)

async def show_question(target, session, edit=False):
    text = get_question_text(session)
    markup = question_keyboard(session["index"], len(session["questions"]),
                               session["answers"].get(session["index"]))
    try:
        if edit and isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=markup)
        else:
            await target.answer(text, reply_markup=markup)
    except Exception:
        if isinstance(target, CallbackQuery):
            await target.message.answer(text, reply_markup=markup)

async def timer_watch(user_id, message, question_index, deadline):
    await asyncio.sleep(QUESTION_TIME)
    session = sessions.get(user_id)
    if not session or session["index"] != question_index:
        return
    if session["deadline"] != deadline or time.time() < deadline:
        return
    # Time expired: unanswered question is left blank and the test advances.
    if question_index < len(session["questions"]) - 1:
        session["index"] += 1
        session["deadline"] = time.time() + QUESTION_TIME
        await show_question(message, session, edit=True)
        asyncio.create_task(timer_watch(user_id, message, session["index"], session["deadline"]))
    else:
        await message.answer("⏰ Vaqt tugadi. Test yakunlandi.")
        await finish_test(user_id, session["user"], message)

async def begin_question_timer(user_id, message, session):
    idx = session["index"]
    deadline = session["deadline"]
    asyncio.create_task(timer_watch(user_id, message, idx, deadline))

async def finish_test(user_id, user, message):
    session = sessions.pop(user_id, None)
    if not session:
        return
    questions = session["questions"]
    raw_max = sum(q["points"] for q in questions)
    raw_score = sum(q["points"] for i, q in enumerate(questions)
                    if session["answers"].get(i) == q["correct_answer"])
    score = round((raw_score / raw_max) * 100) if raw_max else 0
    correct = sum(1 for i, q in enumerate(questions)
                  if session["answers"].get(i) == q["correct_answer"])
    total = len(questions)
    level = level_for(score)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO results(user_id, full_name, username, test_type, score, correct, total) VALUES(?,?,?,?,?,?,?)",
            (user_id, user.full_name, user.username, session["test_type"], score, correct, total)
        )
    label = session["label"]
    text = (
        "🏆 <b>Test yakunlandi!</b>\n\n"
        f"Test: <b>{label}</b>\n"
        f"Natija: <b>{score}/100</b>\n"
        f"To‘g‘ri javoblar: <b>{correct}/{total}</b>\n\n"
        f"🎓 Sizning taxminiy darajangiz:\n<b>{level}</b>\n\n"
        "Natija Nova West LC boshlang‘ich baholash testi asosida hisoblandi."
    )
    await message.answer(text, reply_markup=home_keyboard())

@dp.message(CommandStart())
async def start(message: Message):
    sessions.pop(message.from_user.id, None)
    await message.answer(
        "👋 <b>Nova West LC</b> rasmiy bilimni aniqlash botiga xush kelibsiz!\n\n"
        "Ingliz tili darajangizni aniqlash uchun test turini tanlang.\n"
        "Har bir savolga javob berish uchun 1 daqiqa vaqt ajratiladi.",
        reply_markup=home_keyboard()
    )

@dp.callback_query(F.data.startswith("start:"))
async def start_test(call: CallbackQuery):
    test_type = call.data.split(":", 1)[1]
    questions = [q for q in BANKS[test_type] if q.get("active", True)]
    if not questions:
        await call.answer("Bu testda hozircha savollar yo‘q.", show_alert=True)
        return
    label = "Beginner testi" if test_type == "beginner" else "Intermediate testi"
    session = {
        "test_type": test_type,
        "user": call.from_user,
        "label": label,
        "questions": questions,
        "index": 0,
        "answers": {},
        "deadline": time.time() + QUESTION_TIME
    }
    sessions[call.from_user.id] = session
    await call.answer()
    await show_question(call, session)
    await begin_question_timer(call.from_user.id, call.message, session)

@dp.callback_query(F.data.startswith("answer:"))
async def answer_question(call: CallbackQuery):
    session = sessions.get(call.from_user.id)
    if not session:
        await call.answer("Avval testni boshlang.", show_alert=True)
        return
    if time.time() >= session["deadline"]:
        await call.answer("Bu savol uchun vaqt tugadi.", show_alert=True)
        return
    key = call.data.split(":", 1)[1]
    session["answers"][session["index"]] = key
    await call.answer(f"{key} javobi belgilandi.")
    await show_question(call, session, edit=True)

@dp.callback_query(F.data.startswith("nav:"))
async def navigate(call: CallbackQuery):
    session = sessions.get(call.from_user.id)
    if not session:
        await call.answer("Faol test topilmadi.", show_alert=True)
        return
    direction = call.data.split(":", 1)[1]
    new_index = session["index"] - 1 if direction == "prev" else session["index"] + 1
    if not 0 <= new_index < len(session["questions"]):
        await call.answer()
        return
    session["index"] = new_index
    session["deadline"] = time.time() + QUESTION_TIME
    await call.answer()
    await show_question(call, session, edit=True)
    await begin_question_timer(call.from_user.id, call.message, session)

@dp.callback_query(F.data == "finish")
async def finish_callback(call: CallbackQuery):
    session = sessions.get(call.from_user.id)
    if not session:
        await call.answer("Faol test topilmadi.", show_alert=True)
        return
    await call.answer()
    await finish_test(call.from_user.id, call.from_user, call.message)

@dp.message(Command("cancel"))
async def cancel(message: Message):
    sessions.pop(message.from_user.id, None)
    await message.answer("Test bekor qilindi. Qayta boshlash uchun /start buyrug‘ini yuboring.")

@dp.message(Command("result"))
async def latest_result(message: Message):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT test_type, score, correct, total, finished_at FROM results WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (message.from_user.id,)
        ).fetchone()
    if not row:
        await message.answer("Hozircha saqlangan natijangiz yo‘q.")
        return
    test_name = "Beginner" if row[0] == "beginner" else "Intermediate"
    await message.answer(
        f"📊 <b>Oxirgi natijangiz</b>\nTest: {test_name}\nBall: <b>{row[1]}/100</b>\n"
        f"To‘g‘ri javoblar: {row[2]}/{row[3]}\nDaraja: <b>{level_for(row[1])}</b>\nSana: {row[4]}"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
