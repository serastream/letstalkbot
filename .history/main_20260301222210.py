# main.py
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

WEBINAR_URL = "https://example.com/webinar"      # <-- замени
CHANNEL_URL = "https://t.me/example_channel"     # <-- замени

# Данные квиза: варианты -> 15 вопросов -> 3 ответа
VARIANTS = {
    "v1": {
        "title": "Живой разговор — Natural English Test",
        "questions": [
            {
                "q": "1️⃣ Тяжёлый период начинает на вас сказываться.",
                "options": [
                    ("A", "It affects me a lot."),
                    ("B", "It’s starting to get to me."),
                    ("C", "It influences my emotional state."),
                ],
            },
            {
                "q": "2️⃣ Вы до сих пор не можете отпустить старую обиду.",
                "options": [
                    ("A", "I’m still upset about it."),
                    ("B", "I still remember it."),
                    ("C", "I’m starting to resent it."),
                ],
            },
            {
                "q": "3️⃣ Фильм оказался очень скучным.",
                "options": [
                    ("A", "It was very boring."),
                    ("B", "It was a bit slow."),
                    ("C", "It was a total snoozefest."),
                ],
            },
            {
                "q": "4️⃣ Вы успели буквально в последний момент.",
                "options": [
                    ("A", "I arrived at the last minute."),
                    ("B", "I barely made it."),
                    ("C", "I arrived very late."),
                ],
            },
            {
                "q": "5️⃣ Человеку нужно загладить вину.",
                "options": [
                    ("A", "He should apologize."),
                    ("B", "He should say sorry."),
                    ("C", "He should make up for it."),
                ],
            },
            {
                "q": "6️⃣ Разговор становится неловким.",
                "options": [
                    ("A", "It feels uncomfortable."),
                    ("B", "This is awkward."),
                    ("C", "The situation is not pleasant."),
                ],
            },
            {
                "q": "7️⃣ Вы эмоционально вымотаны отношениями.",
                "options": [
                    ("A", "It was stressful."),
                    ("B", "It drained me."),
                    ("C", "It was very difficult for me emotionally."),
                ],
            },
            {
                "q": "8️⃣ Вы начинаете понимать неприятную правду.",
                "options": [
                    ("A", "I understand now."),
                    ("B", "It’s starting to sink in."),
                    ("C", "Now I clearly realize everything."),
                ],
            },
            {
                "q": "9️⃣ Кто-то слишком остро реагирует.",
                "options": [
                    ("A", "He reacts too much."),
                    ("B", "He’s overreacting."),
                    ("C", "He is too emotional about this."),
                ],
            },
            {
                "q": "🔟 Вы хотите честно высказать мнение.",
                "options": [
                    ("A", "Honestly…"),
                    ("B", "If I’m being honest…"),
                    ("C", "To tell the truth in this situation…"),
                ],
            },
            {
                "q": "1️⃣1️⃣ Человек ведёт себя подозрительно.",
                "options": [
                    ("A", "He is not honest."),
                    ("B", "Something feels off."),
                    ("C", "His behavior is strange."),
                ],
            },
            {
                "q": "1️⃣2️⃣ Вы не хотите портить атмосферу.",
                "options": [
                    ("A", "I don’t want conflict."),
                    ("B", "I don’t want to ruin the vibe."),
                    ("C", "I don’t want any problems."),
                ],
            },
            {
                "q": "1️⃣3️⃣ Вы начинаете раздражаться.",
                "options": [
                    ("A", "I’m getting annoyed."),
                    ("B", "I’m angry."),
                    ("C", "It’s starting to get on my nerves."),
                ],
            },
            {
                "q": "1️⃣4️⃣ Вы понимаете, что ситуация сложнее, чем казалось.",
                "options": [
                    ("A", "It’s complicated."),
                    ("B", "There’s more to it than I thought."),
                    ("C", "It is not simple as I believed."),
                ],
            },
            {
                "q": "1️⃣5️⃣ Вам нужно время всё переварить.",
                "options": [
                    ("A", "I need time to process this."),
                    ("B", "I need to think."),
                    ("C", "I need time."),
                ],
            },
        ],
        "result_texts": {
            "A": "Ты говоришь грамотно, но звучишь немного учебниково. Хорошая база, но разговорность можно усилить.",
            "B": "Ты звучишь естественно и живо. Почти native-уровень бытового английского.",
            "C": "Ты стремишься к выразительности, но иногда фразы звучат чуть перегруженно или формально.",
        },
    }
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


def compute_result(variant_id: str, answers: List[str]) -> tuple[str, int]:
    score = answers.count("B")  # баллы за "живые" формулировки

    if 0 <= score <= 5:
        text = (
            "🟡 0–5 баллов\n"
            "«Безопасный говорящий»\n\n"
            "Вы говорите правильно.\n"
            "Грамматика на месте.\n"
            "Словарный запас есть.\n"
            "Но вы почти всегда выбираете нейтральные, учебниковые формулировки.\n"
            "Вы звучите корректно — но без эмоциональной глубины.\n\n"
            "📌 Что это значит:\n"
            "• вы избегаете рисков\n"
            "• вы боитесь звучать “слишком”\n"
            "• вы переводите мысли, а не формулируете их chunk-ами\n\n"
            "Именно поэтому возникает ощущение:\n"
            "“Я всё понимаю, но говорю проще, чем хочу.”\n\n"
            "Это не проблема уровня.\n"
            "Это проблема типа лексики.\n\n"
            f"Ваш результат: {score} из 15"
        )
        return text, score

    if 6 <= score <= 10:
        text = (
            "🟠 6–10 баллов\n"
            "«На границе перехода»\n\n"
            "Вы чувствуете живую речь.\n"
            "Иногда выбираете естественные формулировки.\n"
            "Но в стрессовой ситуации возвращаетесь к безопасному варианту.\n\n"
            "📌 Это значит:\n"
            "• пассивно вы знаете больше, чем используете\n"
            "• активная речь отстаёт от понимания\n"
            "• вам не хватает среды, где можно закрепить это системно\n\n"
            "Вы уже не B1.\n"
            "Но ещё не звучите свободно.\n"
            "И это как раз та точка, где многие застревают годами.\n\n"
            f"Ваш результат: {score} из 15"
        )
        return text, score

    # 11–15
    text = (
        "🟢 11–15 баллов\n"
        "«Чувство языка есть»\n\n"
        "Вы интуитивно тянетесь к живым формулировкам.\n"
        "Вы понимаете разницу между:\n"
        "neutral English\n"
        "real-life English\n\n"
        "Но.\n"
        "Знание ≠ использование.\n\n"
        "Если вы не практикуете такие конструкции регулярно,\n"
        "они остаются пассивными.\n"
        "И тогда речь всё равно звучит проще, чем могла бы.\n\n"
        f"Ваш результат: {score} из 15"
    )
    return text, score


async def finish_quiz(target: Message | CallbackQuery):
    user_id = target.from_user.id
    s = get_session(user_id)

    result_text, score = compute_result(s.variant_id, s.answers)

    # 1) Сначала отправляем результат
    header = "📌 Расшифровка → Результат\n\n"
    if isinstance(target, CallbackQuery):
        await target.message.answer(header + result_text)
        await target.answer()
    else:
        await target.answer(header + result_text)

    # 2) Потом — доп. сообщение + кнопки (по условию)
    if score < 11:
        if isinstance(target, CallbackQuery):
            await target.message.answer(
                AFTER_RESULT_LOW_SCORE_TEXT,
                reply_markup=kb_after_test()
            )
        else:
            await target.answer(
                AFTER_RESULT_LOW_SCORE_TEXT,
                reply_markup=kb_after_test()
            )
    else:
        # Можно всё равно дать кнопки без текста — это удобно пользователю
        if isinstance(target, CallbackQuery):
            await target.message.answer(
                "Хочешь прокачать живую речь ещё сильнее? 👇",
                reply_markup=kb_after_test()
            )
        else:
            await target.answer(
                "Хочешь прокачать живую речь ещё сильнее? 👇",
                reply_markup=kb_after_test()
            )

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