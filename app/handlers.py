import random
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from sqlalchemy import select,delete
from database.models import Word, async_session
from aiogram.utils.keyboard import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup



class QuizStates(StatesGroup):
    waiting_for_answer = State()
    waiting_for_next_word = State()
    waiting_for_english_word = State()  # Для ожидания английского слова
    waiting_for_russian_translation = State()  # Для ожидания русского перевода
    waiting_for_word_to_delete = State()  # Для ожидания слова, которое нужно удалить


router = Router()
@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer("Данный бот создан для изучения английских слов в рамках курса python разработчика.\n\nДекабрь 2024", reply_markup=keyboard_start)

keyboard_start = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/start")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await send_word(message, state)


async def send_word(message: Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(Word))
        words = result.scalars().all()

    if not words:
        await message.answer("В базе данных нет слов.")
        return

    random_word = random.choice(words)
    correct_translation = random_word.translation

    wrong_translations = random.sample(
        [word.translation for word in words if word.translation != correct_translation], 3
    )

    options = [correct_translation] + wrong_translations
    random.shuffle(options)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=option) for option in options],
            [KeyboardButton(text="Следующее слово")],
            [KeyboardButton(text="Добавить слово")],
            [KeyboardButton(text="Удалить слово")]
        ],
        resize_keyboard=True
    )

    await message.answer(f"Как переводится слово '{random_word.word}'?", reply_markup=keyboard)
    await state.update_data(correct_translation=correct_translation)
    await state.set_state(QuizStates.waiting_for_answer)


@router.message(QuizStates.waiting_for_answer, F.text)
async def check_answer(message: Message, state: FSMContext):
    user_answer = message.text.strip()
    data = await state.get_data()
    correct_translation = data.get('correct_translation')

    if correct_translation and user_answer.lower() == correct_translation.lower():
        await message.answer("Молодец!")
    else:
        await message.answer(f"Попробуй еще. Правильный ответ: {correct_translation}.")

    await state.set_state(QuizStates.waiting_for_next_word)


@router.message(QuizStates.waiting_for_next_word, F.text == "Следующее слово")
async def next_word(message: Message, state: FSMContext):
    await send_word(message, state)


@router.message(QuizStates.waiting_for_next_word, F.text == "Добавить слово")
async def add_word_prompt(message: Message, state: FSMContext):
    await message.answer("Введите английское слово:")
    await state.set_state(QuizStates.waiting_for_english_word)


@router.message(QuizStates.waiting_for_english_word)
async def get_english_word(message: Message, state: FSMContext):
    english_word = message.text.strip()
    await state.update_data(english_word=english_word)
    await message.answer("Теперь введите перевод на русский:")
    await state.set_state(QuizStates.waiting_for_russian_translation)


@router.message(QuizStates.waiting_for_russian_translation)
async def get_russian_translation(message: Message, state: FSMContext):
    russian_translation = message.text.strip()
    data = await state.get_data()
    english_word = data.get('english_word')

    # Сохранение нового слова в базе данных
    async with async_session() as session:
        new_word = Word(word=english_word, translation=russian_translation)
        session.add(new_word)
        await session.commit()

    await message.answer(f"Слово '{english_word}' с переводом '{russian_translation}' добавлено!")
    await cmd_start(message, state)  # Возвращаемся к началу


@router.message(QuizStates.waiting_for_next_word, F.text == "Удалить слово")
async def remove_word_prompt(message: Message, state: FSMContext):
    await message.answer("Введите английское слово, которое хотите удалить:")
    await state.set_state(QuizStates.waiting_for_word_to_delete)


@router.message(QuizStates.waiting_for_word_to_delete)
async def delete_word(message: Message, state: FSMContext):
    word_to_delete = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(Word).where(Word.word == word_to_delete))
        word = result.scalars().first()

        if word:
            await session.execute(delete(Word).where(Word.id == word.id))
            await session.commit()
            await message.answer(f"Слово '{word_to_delete}' было успешно удалено из базы данных.")
        else:
            await message.answer(f"Слово '{word_to_delete}' не найдено в базе данных.")

    await cmd_start(message, state)  # Возвращаемся к началу