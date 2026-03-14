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

WEBINAR_URL = "https://forms.gle/Duc2yc5Mzzh8dRrr6"
CHANNEL_URL = "https://t.me/yukas_eng"

VARIANTS = {
    "v1": {
        "title": "Живой разговор — Natural English Test",
        "questions": [
            {"q": "1️⃣ Тяжёлый период начинает на вас сказываться.", "options": [("A", "It affects me a lot."), ("B", "It’s starting to get to me."), ("C", "It influences my emotional state.")], "correct": "B"},
            {"q": "2️⃣ Вы до сих пор не можете отпустить старую обиду.", "options": [("A", "I’m starting to resent it."), ("B", "I’m still upset about it."), ("C", "I still remember it.")], "correct": "C"},
            {"q": "3️⃣ Фильм оказался очень скучным.", "options": [("A", "It was very boring."), ("B", "It was a bit slow."), ("C", "It was a total snoozefest.")], "correct": "C"},
            {"q": "4️⃣ Вы успели буквально в последний момент.", "options": [("A", "I arrived at the last minute."), ("B", "I barely made it."), ("C", "I arrived very late.")], "correct": "B"},
            {"q": "5️⃣ Человеку нужно загладить вину.", "options": [("A", "He should apologize."), ("B", "He should make up for it."), ("C", "He should say sorry.")], "correct": "C"},
            {"q": "6️⃣ Разговор становится неловким.", "options": [("A", "This is awkward."), ("B", "It feels uncomfortable."), ("C", "The situation is not pleasant.")], "correct": "B"},
            {"q": "7️⃣ Вы эмоционально вымотаны отношениями.", "options": [("A", "It was stressful."), ("B", "It was very difficult for me emotionally."), ("C", "It drained me.")], "correct": "B"},
            {"q": "8️⃣ Вы начинаете понимать неприятную правду.", "options": [("A", "I understand now."), ("B", "It’s starting to sink in."), ("C", "Now I clearly realize everything.")], "correct": "A"},
            {"q": "9️⃣ Кто-то слишком остро реагирует.", "options": [("A", "He reacts too much."), ("B", "He’s overreacting."), ("C", "He is too emotional about this.")], "correct": "B"},
            {"q": "🔟 Вы хотите честно высказать мнение.", "options": [("A", "Honestly…"), ("B", "To tell the truth in this situation…"), ("C", "If I’m being honest…")], "correct": "B"},
            {"q": "1️⃣1️⃣ Человек ведёт себя подозрительно.", "options": [("A", "Something feels off."), ("B", "His behavior is strange."), ("C", "He is not honest.")], "correct": "A"},
            {"q": "1️⃣2️⃣ Вы не хотите портить атмосферу.", "options": [("A", "I don’t want conflict."), ("B", "I don’t want to ruin the vibe."), ("C", "I don’t want any problems.")], "correct": "B"},
            {"q": "1️⃣3️⃣ Вы начинаете раздражаться.", "options": [("A", "I’m getting annoyed."), ("B", "I’m angry."), ("C", "It’s starting to get on my nerves.")], "correct": "C"},
            {"q": "1️⃣4️⃣ Вы понимаете, что ситуация сложнее, чем казалось.", "options": [("A", "There’s more to it than I thought."), ("B", "It’s complicated."), ("C", "It is not simple as I believed.")], "correct": "B"},
            {"q": "1️⃣5️⃣ Вам нужно время всё переварить.", "options": [("A", "I need time to process this."), ("B", "I need to think."), ("C", "I need time.")], "correct": "A"},
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

    # Если вопросы закончились, завершаем
    if s.q_index >= len(variant["questions"]):
        await finish_quiz(target)
        return

    q = variant["questions"][s.q_index]
    
    # Логика текста: если это первый вопрос (индекс 0), добавляем инструкцию
    if s.q_index == 0:
        text = (
            "Выбери вариант, который скорее всего вы бы сказали в живом разговоре:\n\n"
            f"{q['q']}"
        )
    else:
        # Для всех остальных вопросов — только сам вопрос
        text = f"{q['q']}"
    
    markup = kb_question(q["options"])

    if isinstance(target, CallbackQuery):
        # Отправляем новый вопрос сообщением
        await target.message.answer(text, reply_markup=markup)
    else:
        # Если вызвано из команды (например, /start), отвечаем на сообщение
        await target.answer(text, reply_markup=markup)

def compute_result(variant_id: str, answers: List[str]) -> tuple[str, int]:
    questions = VARIANTS[variant_id]["questions"]
    score = 0
    
    for i, user_answer in enumerate(answers):
        if user_answer == questions[i]["correct"]:
            score += 1

    if score <= 5:
        res = "🟡 0–5 баллов\n«Безопасный говорящий»"
    elif score <= 10:
        res = "🟠 6–10 баллов\n«На границе перехода»"
    else:
        res = "🟢 11–15 баллов\n«Чувство языка есть»"
    
    # УБРАНО: теги <b> и </b> вокруг {res}
    text = f"{res}\n\nВаш результат: {score} из 15"
    return text, score

async def finish_quiz(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)
    result_text, score = compute_result(s.variant_id, s.answers)

    msg_obj = target.message if isinstance(target, CallbackQuery) else target
    
    # УБРАНО: теги <b> и </b> в строке ниже
    await msg_obj.answer(f"📌 Расшифровка → Результат\n\n{result_text}")

    final_text = AFTER_RESULT_LOW_SCORE_TEXT if score < 11 else "Хочешь прокачать живую речь ещё сильнее? 👇"
    await msg_obj.answer(final_text, reply_markup=kb_after_test())
    
    # Сброс сессии
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
    s = get_session(call.from_user.id)
    # Сразу назначаем вариант v1
    s.variant_id = "v1"
    s.q_index = 0
    s.answers = []
    
    await send_next_question(call)
    await call.answer()

@dp.callback_query(F.data.startswith("ans:"))
async def on_answer(call: CallbackQuery):
    s = get_session(call.from_user.id)
    if not s.variant_id:
        return
        
    ans_code = call.data.split(":")[1]
    s.answers.append(ans_code)
    s.q_index += 1
    
    await call.answer("Записал ✅")
    await send_next_question(call)

# ================== RUN ==================
async def main():
    bot = Bot(
        token=BOT_TOKEN, 
        default_bot_properties=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass