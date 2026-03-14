# main.py
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "7603599436:AAGGyJZgTy5V2ubAeqBYg-wdVGkuQI3kRM4PASTE_YOUR_TOKEN_HERE"

WEBINAR_URL = "https://example.com/webinar"      # <-- замени
CHANNEL_URL = "https://t.me/example_channel"     # <-- замени

# Данные квиза: варианты -> 15 вопросов -> 3 ответа
VARIANTS = {
    "v1": {
        "title": "Вариант 1",
        "questions": [
            {
                "q": "1) Какой формат тебе комфортнее всего?",
                "options": [
                    ("A", "Короткие видео и практика"),
                    ("B", "Текст + примеры"),
                    ("C", "Созвоны и разборы"),
                ],
            },
            {
                "q": "2) Когда тебе легче учиться?",
                "options": [
                    ("A", "По 10–15 минут каждый день"),
                    ("B", "Сессиями по 1–2 часа"),
                    ("C", "Когда есть дедлайн и группа"),
                ],
            },
            {
                "q": "3) Что сильнее мотивирует?",
                "options": [
                    ("A", "Сразу сделать и увидеть результат"),
                    ("B", "Понять систему и логику"),
                    ("C", "Поддержка/обратная связь от наставника"),
                ],
            },
            # ---- ДОБАВЬ СЮДА ЕЩЁ 12 ВОПРОСОВ (итого 15) ----
            # Копируй блоки выше и меняй текст.
            {"q": "4) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "5) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "6) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "7) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "8) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "9) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "10) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "11) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "12) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "13) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "14) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
            {"q": "15) (добавь вопрос)", "options": [("A", "вариант"), ("B", "вариант"), ("C", "вариант")]},
        ],
        "result_texts": {
            "A": "Твой стиль — быстрые итерации и практика. Тебе зайдут короткие задания и чек-листы.",
            "B": "Твой стиль — системность. Тебе зайдут структуры, конспекты и методички.",
            "C": "Твой стиль — обучение через диалог. Тебе зайдут разборы и вебинары.",
        },
    },
    "v2": {
        "title": "Вариант 2",
        "questions": [
            # Быстро: можешь временно продублировать вопросы из v1
            # и потом заменить тексты.
            *([]),
        ],
        "result_texts": {
            "A": "Результат A для варианта 2.",
            "B": "Результат B для варианта 2.",
            "C": "Результат C для варианта 2.",
        },
    },
}

POST_TEST_TEXT = (
    "✅ Тест завершён!\n\n"
    "Приходи на вебинар — разберём твой результат и соберём план действий.\n"
)

# ================== ПАМЯТЬ СОСТОЯНИЯ (RAM) ==================
@dataclass
class UserSession:
    variant_id: Optional[str] = None
    q_index: int = 0
    answers: List[str] = field(default_factory=list)

SESSIONS: Dict[int, UserSession] = {}


def get_session(user_id: int) -> UserSession:
    if user_id not in SESSIONS:
        SESSIONS[user_id] = UserSession()
    return SESSIONS[user_id]


# ================== КЛАВИАТУРЫ ==================
def kb_choose_variant():
    kb = InlineKeyboardBuilder()
    for vid, v in VARIANTS.items():
        # пропускаем пустые/не заполненные варианты, чтобы не ломать UX
        if not v.get("questions"):
            continue
        kb.button(text=v["title"], callback_data=f"variant:{vid}")
    kb.adjust(1)
    return kb.as_markup()


def kb_question(options: List[Tuple[str, str]]):
    kb = InlineKeyboardBuilder()
    for code, text in options:
        kb.button(text=f"{code}) {text}", callback_data=f"ans:{code}")
    kb.adjust(1)
    return kb.as_markup()


def kb_after_test():
    kb = InlineKeyboardBuilder()
    kb.button(text="🗓 Зарегистрироваться на вебинар", url=WEBINAR_URL)
    kb.button(text="📣 Подписаться на Telegram-канал", url=CHANNEL_URL)
    kb.adjust(1)
    return kb.as_markup()


# ================== ЛОГИКА ==================
async def send_next_question(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)

    if not s.variant_id or s.variant_id not in VARIANTS:
        text = "Привет! Выбери вариант 👇"
        if isinstance(target, CallbackQuery):
            await target.message.answer(text, reply_markup=kb_choose_variant())
            await target.answer()
        else:
            await target.answer(text, reply_markup=kb_choose_variant())
        return

    variant = VARIANTS[s.variant_id]
    questions = variant["questions"]

    if len(questions) < 15:
        msg = "⚠️ В этом варианте пока меньше 15 вопросов. Заполни VARIANTS в main.py."
        if isinstance(target, CallbackQuery):
            await target.message.answer(msg)
            await target.answer()
        else:
            await target.answer(msg)
        return

    if s.q_index >= 15:
        await finish_quiz(target)
        return

    q = questions[s.q_index]
    text = f"{q['q']}\n\nВыбери ответ:"
    markup = kb_question(q["options"])

    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


def compute_result(variant_id: str, answers: List[str]) -> str:
    counts = {"A": 0, "B": 0, "C": 0}
    for a in answers:
        if a in counts:
            counts[a] += 1
    winner = max(counts, key=counts.get)

    variant = VARIANTS[variant_id]
    base = variant["result_texts"].get(winner, "Спасибо за ответы!")
    detail = f"\n\nТвои баллы: A={counts['A']}, B={counts['B']}, C={counts['C']}."
    return base + detail


async def finish_quiz(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)

    result_text = compute_result(s.variant_id, s.answers)
    text = (
        "📌 Расшифровка → Результат\n\n"
        f"{result_text}\n\n"
        f"{POST_TEST_TEXT}"
    )

    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=kb_after_test())
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb_after_test())

    # сброс
    SESSIONS[user_id] = UserSession()


# ================== HANDLERS ==================
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    SESSIONS[message.from_user.id] = UserSession()
    text = (
        "/START\n\n"
        "Привет!\n"
        "Выбери вариант.\n\n"
        "Тест: 15 вопросов и по три варианта ответов.\n"
        "Расшифровка → Результат\n\n"
        "После теста — приглашение на вебинар и кнопки."
    )
    await message.answer(text, reply_markup=kb_choose_variant())


@dp.callback_query(F.data.startswith("variant:"))
async def on_variant(call: CallbackQuery):
    user_id = call.from_user.id
    s = get_session(user_id)

    vid = call.data.split(":", 1)[1]
    if vid not in VARIANTS or not VARIANTS[vid].get("questions"):
        await call.answer("Этот вариант пока не настроен 🤔", show_alert=True)
        return

    s.variant_id = vid
    s.q_index = 0
    s.answers = []

    await call.message.answer(f"Выбран: {VARIANTS[vid]['title']}\nПоехали! 🚀")
    await call.answer()
    await send_next_question(call)


@dp.callback_query(F.data.startswith("ans:"))
async def on_answer(call: CallbackQuery):
    user_id = call.from_user.id
    s = get_session(user_id)

    if not s.variant_id:
        await call.answer("Сначала выбери вариант 🙌", show_alert=True)
        await call.message.answer("Выбери вариант 👇", reply_markup=kb_choose_variant())
        return

    ans = call.data.split(":", 1)[1]
    if ans not in ("A", "B", "C"):
        await call.answer("Неверный ответ", show_alert=True)
        return

    s.answers.append(ans)
    s.q_index += 1

    await call.answer("Записал ✅")
    await send_next_question(call)


# ================== RUN ==================
async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())