import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "6749725988:AAFfAxz-2mODZ6wAm3ML_LKi1I0PIcGTsw4"

AFTER_RESULT_LOW_SCORE_TEXT = (
    "Если вы набрали меньше 11 баллов —\n"
    "вы не “плохо знаете английский”.\n"
    "Вы просто учили академический язык, а не живой.\n\n"
    "На вебинаре я покажу, почему взрослые студенты с уровнем B1–B2 "
    "застревают именно здесь —\n"
    "и как за 10 недель перейти к более естественной, эмоциональной речи"
)

WEBINAR_URL = "https://example.com/webinar"
CHANNEL_URL = "https://t.me/yukas_eng"

VARIANTS = {
    "v1": {
        "title": "Живой разговор — Natural English Test",
        "questions": [
            {"q": "1️⃣ Тяжёлый период начинает на вас сказываться.", "options": [("A", "It affects me a lot."), ("B", "It’s starting to get to me."), ("C", "It influences my emotional state.")]},
            {"q": "2️⃣ Вы до сих пор не можете отпустить старую обиду.", "options": [("A", "I’m still upset about it."), ("B", "I still remember it."), ("C", "I’m starting to resent it.")]},
            {"q": "3️⃣ Фильм оказался очень скучным.", "options": [("A", "It was very boring."), ("B", "It was a bit slow."), ("C", "It was a total snoozefest.")]},
            {"q": "4️⃣ Вы успели буквально в последний момент.", "options": [("A", "I arrived at the last minute."), ("B", "I barely made it."), ("C", "I arrived very late.")]},
            {"q": "5️⃣ Человеку нужно загладить вину.", "options": [("A", "He should apologize."), ("B", "He should say sorry."), ("C", "He should make up for it.")]},
            {"q": "6️⃣ Разговор становится неловким.", "options": [("A", "It feels uncomfortable."), ("B", "This is awkward."), ("C", "The situation is not pleasant.")]},
            {"q": "7️⃣ Вы эмоционально вымотаны отношениями.", "options": [("A", "It was stressful."), ("B", "It drained me."), ("C", "It was very difficult for me emotionally.")]},
            {"q": "8️⃣ Вы начинаете понимать неприятную правду.", "options": [("A", "I understand now."), ("B", "It’s starting to sink in."), ("C", "Now I clearly realize everything.")]},
            {"q": "9️⃣ Кто-то слишком остро реагирует.", "options": [("A", "He reacts too much."), ("B", "He’s overreacting."), ("C", "He is too emotional about this.")]},
            {"q": "🔟 Вы хотите честно высказать мнение.", "options": [("A", "Honestly…"), ("B", "If I’m being honest…"), ("C", "To tell the truth in this situation…")]},
            {"q": "1️⃣1️⃣ Человек ведёт себя подозрительно.", "options": [("A", "He is not honest."), ("B", "Something feels off."), ("C", "His behavior is strange.")]},
            {"q": "1️⃣2️⃣ Вы не хотите портить атмосферу.", "options": [("A", "I don’t want conflict."), ("B", "I don’t want to ruin the vibe."), ("C", "I don’t want any problems.")]},
            {"q": "1️⃣3️⃣ Вы начинаете раздражаться.", "options": [("A", "I’m getting annoyed."), ("B", "I’m angry."), ("C", "It’s starting to get on my nerves.")]},
            {"q": "1️⃣4️⃣ Вы понимаете, что ситуация сложнее, чем казалось.", "options": [("A", "It’s complicated."), ("B", "There’s more to it than I thought."), ("C", "It is not simple as I believed.")]},
            {"q": "1️⃣5️⃣ Вам нужно время всё переварить.", "options": [("A", "I need time to process this."), ("B", "I need to think."), ("C", "I need time.")]},
        ]
    }
}

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
        if v.get("questions"):
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
    kb.button(text="🗓 Регистрация на вебинар", url=WEBINAR_URL)
    kb.button(text="📣 Мой тг канал", url=CHANNEL_URL)
    kb.adjust(1)
    return kb.as_markup()

# ================== ЛОГИКА ==================
async def send_next_question(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)
    
    variant = VARIANTS.get(s.variant_id)
    if not variant: return

    if s.q_index >= len(variant["questions"]):
        await finish_quiz(target)
        return

    q = variant["questions"][s.q_index]
    text = f"<b>{q['q']}</b>\n\nВыбери ответ:"
    markup = kb_question(q["options"])

    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)

def compute_result(answers: List[str]) -> tuple[str, int]:
    score = answers.count("B")
    if score <= 5:
        res = "🟡 0–5 баллов\n«Безопасный говорящий»"
    elif score <= 10:
        res = "🟠 6–10 баллов\n«На границе перехода»"
    else:
        res = "🟢 11–15 баллов\n«Чувство языка есть»"
    
    text = f"<b>{res}</b>\n\nВаш результат: {score} из 15"
    return text, score

async def finish_quiz(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)
    result_text, score = compute_result(s.answers)

    msg_obj = target.message if isinstance(target, CallbackQuery) else target
    await msg_obj.answer(f"📌 <b>Расшифровка → Результат</b>\n\n{result_text}")

    final_text = AFTER_RESULT_LOW_SCORE_TEXT if score < 11 else "Хочешь прокачать живую речь ещё сильнее? 👇"
    await msg_obj.answer(final_text, reply_markup=kb_after_test())
    
    SESSIONS[user_id] = UserSession()

# ================== HANDLERS ==================
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    SESSIONS[message.from_user.id] = UserSession()
    
    text = (
        "Привет! 👋\n\n"
        "Бывает такое: вроде учишь английский годами, знаешь правила, но в разговоре "
        "чувствуешь себя роботом? 🤖\n\n"
        "Этот тест не про скучную грамматику. Он про то, как вы звучите в реальной жизни — "
        "там, где люди смеются, спорят и выражают эмоции.\n\n"
        "Здесь нет «ошибок». Есть только выбор: звучать как сухой учебник или как живой человек.\n\n"
        "В конце ты узнаешь свой результат и поймешь, почему речь может звучать «плоско», "
        "даже если в ней нет грамматических ошибок.\n\n"
        "Готов(а) проверить себя? 👇"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Начать тест", callback_data="start_quiz")
    
    await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_quiz")
async def on_start_quiz(call: CallbackQuery):
    await call.message.edit_text("Выбери вариант теста 👇", reply_markup=kb_choose_variant())
    await call.answer()

@dp.callback_query(F.data.startswith("variant:"))
async def on_variant(call: CallbackQuery):
    s = get_session(call.from_user.id)
    s.variant_id = call.data.split(":")[1]
    s.q_index = 0
    s.answers = []
    await call.message.answer(f"Выбран: <b>{VARIANTS[s.variant_id]['title']}</b>\nПоехали! 🚀")
    await send_next_question(call)
    await call.answer()

@dp.callback_query(F.data.startswith("ans:"))
async def on_answer(call: CallbackQuery):
    s = get_session(call.from_user.id)
    if not s.variant_id: return
    s.answers.append(call.data.split(":")[1])
    s.q_index += 1
    await call.answer("Записал ✅")
    await send_next_question(call)

async def main():
    bot = Bot(token=BOT_TOKEN, default_bot_properties=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())