import logging
from db import DB
import requests
import re
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import BoundFilter, Text

API_TOKEN = ""

# Configure logging
logging.basicConfig(level=logging.INFO)


class LinkStates(StatesGroup):
    username = State()
    password = State()
    title = State()
    content = State()
    priority = State()
    deadline = State()
    
    
class IsLinkedFilter(BoundFilter):
    key = "linked"

    def __init__(self, linked: bool):
        self.linked = linked

    async def check(self, message: types.Message):
        telegram_id = message.from_id
        payload = {"telegram_id": telegram_id}
        r = requests.get("http://127.0.0.1:5000/check_tg", params=payload)
        content = r.json()
        return content.get("status", False) is self.linked
        

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.filters_factory.bind(IsLinkedFilter)

class RegisterStates(StatesGroup):
    login = State()
    password = State()

kbd = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [types.KeyboardButton(text="🟥"), types.KeyboardButton(text="🟧")],
    [types.KeyboardButton(text="🟨"), types.KeyboardButton(text="🟩")]
])

@dp.message_handler(commands=["add_task"], linked=True)
async def add_task(message: types.Message, state: FSMContext):
    await message.answer("Введіть назву задачі:")
    await LinkStates.title.set()

@dp.message_handler(state=LinkStates.title)
async def process_title(message: types.Message, state: FSMContext):
    title = message.text
    await state.update_data(title=title)
    await message.answer("Введіть вміст задачі:")
    await LinkStates.content.set()

@dp.message_handler(state=LinkStates.content)
async def process_content(message: types.Message, state: FSMContext):
    content = message.text
    await state.update_data(content=content)
    await message.answer("Оберіть пріоритет задачі", reply_markup=kbd)
    await LinkStates.priority.set()

priority_colors = {
    "🟥": 4,
    "🟧": 3,
    "🟨": 2,
    "🟩": 1
}

@dp.message_handler(state=LinkStates.priority)
async def process_priority(message: types.Message, state: FSMContext):
    priority = message.text
    if priority not in ["🟥", "🟧", "🟨", "🟩"]:
        await message.answer("Невірний пріоритет. Введіть 1, 2, 3 або 4 (1 - можна відкласти на потім, 4 - ЗРОБИТИ НЕГАЙНО!)")
        return

    await state.update_data(priority=priority_colors.get(priority))
    await message.answer("Введіть дедлайн задачі (у форматі YYYY-MM-DD HH:MM):", reply_markup=types.ReplyKeyboardRemove())
    await LinkStates.deadline.set()

@dp.message_handler(state=LinkStates.deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}"
    deadline = message.text
    b = re.search(pattern, deadline)
    if not b:
        await message.answer("Невірний формат дедлайну. Введіть у форматі YYYY-MM-DD HH:MM.")
        return
    
    await state.update_data(deadline=deadline)
    data = await state.get_data()
    params = {
        "title": data.get("title"),
        "content": data.get("content"),
        "priority": data.get("priority"),
        "deadline": data.get("deadline"),
        "telegram_id": message.from_id,
    }
    try:
        r = requests.post("http://127.0.0.1:5000/add_task", data=params)
        print(r.content)
        response = r.json()
        if "error" in response:
            await message.answer(text=response.get("error"))
        else:
            await message.answer(text=response.get("status"))
    except Exception as e:
        await message.answer("Виникла помилка під час додавання задачі. Будь ласка, спробуйте ще раз.")

    await state.finish()



@dp.message_handler(commands="register", linked=False)
async def start_register_process(message: types.Message, state: FSMContext):
    await message.answer("Вітаю. Введіть свій майбутній логін на сайті")
    await RegisterStates.login.set()

@dp.message_handler(state=RegisterStates.login)
async def register_login(message: types.Message, state: FSMContext):
    login = message.text
    await state.update_data(login=login)
    await message.answer("Чудово, тепер вигадай собі пароль")
    await RegisterStates.password.set()
    
@dp.message_handler(state=RegisterStates.password)
async def register_finish(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    login = data.get("login")
    telegram_id = message.from_id
    params = {"username": login, "password": password, "telegram_id": telegram_id}
    r = requests.post("http://127.0.0.1:5000/register_tg", data=params)
    response = r.json()
    if "error" in response:
        await message.answer(text=response.get("error"))
        await message.answer("Напиши ще раз /register")
    else:
        await message.answer("Ви зареєструвались")
    await state.finish()
    
    
@dp.message_handler(commands=["link"], linked=False)
async def link(message: types.Message, state: FSMContext):
    await message.answer("Ваш логін на сайті: ")
    await LinkStates.username.set()


@dp.message_handler(state=LinkStates.username, content_types=[types.ContentType.TEXT])
async def process_username(message: types.Message, state: FSMContext):
    username = message.text
    await state.update_data(username=username)
    await message.answer("Чудово! Тепер введіть ваш пароль: ")
    await LinkStates.password.set()


@dp.message_handler(content_types=[types.ContentType.TEXT], state=LinkStates.password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    async with state.proxy() as data:
        username = data.get("username")
    telegram_id = message.from_id

    data = {
        "username": username,
        "password": password,
        "telegram_id": telegram_id,
    }
    try:
        r = requests.post("http://127.0.0.1:5000/link_tg", data=data)
        response = r.json()
        msg = response.get("message")
        error = response.get("error")
        if msg:
            await message.answer(msg)
            await state.finish()
        elif error:
            await message.answer(error)
            await LinkStates.username.set()

    except Exception as e:
        await message.answer("Виникла помилка під час обробки запиту. Будь ласка, спробуйте ще раз.")
        await LinkStates.username.set()

priorities = {
    1: "🟩",
    2: "🟨🟨",
    3: "🟧🟧🟧",
    4: "🟥🟥🟥🟥"
}


@dp.message_handler(commands=["notes"], linked=True)
async def show_notes(message: types.Message): 
    data = {"telegram_id": message.from_id}
    r = requests.get("http://127.0.0.1:5000/notes_list", params=data)
    notes = r.json().get("notes")
    for note in notes:
        await message.answer(f"<b>{note[1]}</b>\n<i>{note[2]}</i>\nPriority: {priorities.get(note[5])}\n"
                             f"Created at: {note[3]}\nDeadline: <b>{note[4]}</b>", parse_mode="html")
    
        
@dp.message_handler(commands=["delete"], linked=True)
async def delete_note(message: types.Message):
    data = {"telegram_id": message.from_id}
    r = requests.get("http://127.0.0.1:5000/notes_list", params=data)
    notes = r.json().get("notes")
    kbd = types.InlineKeyboardMarkup()
    for note in notes:
        kbd.row(types.InlineKeyboardButton(text=f"❌ {note[1]} ❌", callback_data=f"delete_{note[0]}"))
    await message.answer("Обери нотаток який видалити", reply_markup=kbd)
    
@dp.callback_query_handler(Text(startswith="delete_"))
async def delete_note(call: types.CallbackQuery):
    note_id = call.data.split("_")[-1]
    params = {"note_id": note_id}
    r = requests.post("http://127.0.0.1:5000/del_note", data=params)
    await call.answer(text="Замітка видалена", show_alert=True)
    
    
@dp.message_handler(commands=["unlink"], linked=True)
async def unlink(message: types.Message):
    data = {"telegram_id": message.from_id}
    r = requests.get("http://127.0.0.1:5000/unlink", params=data)
    await message.answer("Ви успішно вийшли з акаунта")
        

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)