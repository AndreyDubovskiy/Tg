import sys

from telebot.async_telebot import AsyncTeleBot
from telebot import types
import pickle
import asyncio
import classes.SubprocessController

bot_token = '6801070603:AAEfDOvxybsd3ebLa6Pvo7ub31pWN3Jsj5g'
api_id = 24209092
api_hash = '822ed15f01ee35ae8a50d750d3e8451d'

class TgBotConfigurator:
    def __init__(self, token: str = bot_token, subprocess_controller: classes.SubprocessController = None):
        self.token = token
        self.bot = AsyncTeleBot(self.token)
        self.bots = [] # {api_id: int, api_hash: str, session_name: str, proxy: dict = None, message_text: str = "Test message"}
        self.proxies = [] # {name: str, ip: str, port: int, type: str , login: str , password: str }
        self.user_dates = {} # {user_id: last_message_date}
        self.subprocess_controller = subprocess_controller
        self.id_admin = 0
        self.admin_password = "admin"
        self.loop = asyncio.get_event_loop()
        self.time_to_answer = 60

        self.load_bots()
        self.load_proxies()
        self.load_id_admin_and_password()
        for bot in self.bots:
            self.subprocess_controller.add_bot(bot)
        self.start_bots(self.bots)

        @self.bot.message_handler(commands=['help', 'start'])
        async def send_welcome(message):
            await self.bot.reply_to(message, "/menu for start")

        @self.bot.message_handler(commands=['editpassword'])
        async def edit_password(message):
            user_id = message.chat.id
            password = message.text.split(" ")[1]
            if user_id == self.id_admin:
                self.admin_password = password
                await self.bot.reply_to(message, "Пароль змінено!")
                self.save_id_admin_and_password()
            else:
                await self.bot.reply_to(message, "Для доступу до меню введіть пароль /login [пароль]")

        @self.bot.message_handler(commands=['login'])
        async def login(message):
            user_id = message.chat.id
            password = message.text.split(" ")[1]
            if password == self.admin_password:
                self.id_admin = user_id
                await self.bot.reply_to(message, "Ви увійшли як адміністратор. /menu for start")
                self.save_id_admin_and_password()
            else:
                await self.bot.reply_to(message, "Не вірний пароль")

        @self.bot.message_handler(commands=['menu'])
        async def send_menu(message):
            user_id = message.chat.id
            if user_id == self.id_admin:
                await self.bot.reply_to(message, "Menu", reply_markup=self.gen_markup_with_menu())
            else:
                await self.bot.reply_to(message, "Для доступу до меню введіть пароль /login [пароль]")


        @self.bot.callback_query_handler(func=lambda call: True)
        async def callback_inline(call):
            if call.message:
                if call.data == "list_bots":
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Список ботів", reply_markup=self.markup_list_bots())
                    self.user_dates[call.message.chat.id] = {"prev_command": "list_bots"}
                elif call.data in self.get_list_proxy_names() and self.user_dates[call.message.chat.id]["prev_command"] == "pick_proxy_for_bot":
                    self.user_dates[call.message.chat.id]["prev_command"] = ""
                    self.add_bot(
                            {"api_id": api_id, "api_hash": api_hash,
                             "session_name": self.user_dates[call.message.chat.id]["session_name"],
                             "proxy": self.proxies[self.get_list_proxy_names().index(call.data)]})
                    self.start_bot(self.bots[-1])
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Бота додано!")
                elif call.data == "Без проксі" and self.user_dates[call.message.chat.id]["prev_command"] == "pick_proxy_for_bot":
                    self.user_dates[call.message.chat.id]["prev_command"] = ""
                    self.add_bot(
                        {"api_id": api_id, "api_hash": api_hash,
                         "session_name": self.user_dates[call.message.chat.id]["session_name"]})
                    self.start_bot(self.bots[-1])
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Бота додано!")
                elif call.data == "list_proxies":
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Список проксі", reply_markup=self.markup_list_proxy())
                    self.user_dates[call.message.chat.id] = {"prev_command": "list_proxies"}
                elif call.data == "cancel":
                    user_id = call.message.chat.id
                    if user_id in self.user_dates:
                        self.user_dates.__delitem__(user_id)
                elif call.data == "add_bot":
                    self.user_dates[call.message.chat.id] = {"prev_command": "add_bot_session_name"}
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Введіть назву бота:")
                elif call.data == "del_bot":
                    self.del_bot(self.user_dates[call.message.chat.id]["bot_index"])
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Бота видалено!")
                    self.user_dates[call.message.chat.id]["prev_command"] = ""
                elif call.data == "edit_bot":
                    self.user_dates[call.message.chat.id]["prev_command"] = "edit_bot_session_name"
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Введіть назву бота (напишіть крапку '.' щоб залишити минуле значення):")
                elif call.data == "add_proxy":
                    self.user_dates[call.message.chat.id] = {"prev_command": "add_proxy_name"}
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Введіть назву проксі:")
                elif call.data == "del_proxy":
                    for bot in self.bots:
                        if bot["proxy"] == self.proxies[self.user_dates[call.message.chat.id]["proxy_index"]]:
                            bot["proxy"] = None
                            self.edit_bot(self.bots.index(bot), bot)
                            self.restart_bot(bot)
                    self.proxies.pop(self.user_dates[call.message.chat.id]["proxy_index"])
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Проксі видалено!")
                    self.save_bots()
                    self.save_proxies()
                    self.user_dates[call.message.chat.id]["prev_command"] = ""
                elif call.data == "edit_proxy":
                    self.user_dates[call.message.chat.id]["prev_command"] = "edit_proxy_name"
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Введіть назву проксі (напишіть крапку '.' щоб залишити минуле значення):")
                elif call.data == "bot_restart":
                    self.restart_all_bots()
                elif call.data == "add_bot_proxy":
                    self.user_dates[call.message.chat.id]["prev_command"] = "add_bot_proxy"
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Оберіть бота", reply_markup=self.markup_simple_list_bots())
                elif call.data in self.get_list_bot_session_names() and self.user_dates[call.message.chat.id]["prev_command"] == "add_bot_proxy":
                    self.bots[self.get_list_bot_session_names().index(call.data)]["proxy"] = self.proxies[self.user_dates[call.message.chat.id]["proxy_index"]]
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Проксі додано!")
                    self.edit_bot(self.get_list_bot_session_names().index(call.data), self.bots[self.get_list_bot_session_names().index(call.data)])
                    self.restart_bot(self.bots[self.get_list_bot_session_names().index(call.data)])
                    self.user_dates[call.message.chat.id]["prev_command"] = ""
                    self.save_bots()
                elif call.data in self.get_list_bot_session_names():
                    self.user_dates[call.message.chat.id] = {"prev_command": "bot_one", "bot_index": self.get_list_bot_session_names().index(call.data)}
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Бот: " + call.data, reply_markup=self.markup_bot_menu())
                elif call.data in self.get_list_proxy_names():
                    self.user_dates[call.message.chat.id] = {"prev_command": "proxy_one", "proxy_index": self.get_list_proxy_names().index(call.data)}
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Проксі: " + call.data, reply_markup=self.markup_proxy_menu())
                elif call.data == "edit_bot_msg":
                    self.user_dates[call.message.chat.id]["prev_command"] = "edit_bot_msg"
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Введіть нове повідомлення:")
                elif call.data == "restart_bot":
                    self.restart_bot(self.bots[self.user_dates[call.message.chat.id]["bot_index"]])
                    await self.bot.send_message(chat_id=call.message.chat.id, text="Бот буде перезапущено протягом 15-20 секунд!")
                elif call.data == "time_change":
                    self.user_dates[call.message.chat.id]["prev_command"] = "time_change"
                    await self.bot.send_message(chat_id=call.message.chat.id,
                                                text="Напишіть час для відповіді: (у секундах)")

                await self.bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


        @self.bot.message_handler(func=lambda message: True)
        async def echo_message(message):
            text = message.text
            user_id = message.chat.id
            print(text)
            if user_id in self.user_dates:
                if self.user_dates[user_id]["prev_command"] == "add_bot_session_name":
                    self.user_dates[user_id]["prev_command"] = "pick_proxy_for_bot"
                    self.user_dates[user_id]["session_name"] = text
                    #self.add_bot(
                    #    {"api_id": api_id, "api_hash": api_hash,
                    #     "session_name": self.user_dates[user_id]["session_name"]})
                    await self.bot.send_message(chat_id=user_id, text="Оберіть проксі", reply_markup=self.markup_simple_list_proxy())
                   # self.start_bot(self.bots[-1])
                elif self.user_dates[user_id]["prev_command"] == "edit_bot_session_name":
                    if text != ".":
                        self.user_dates[user_id]["session_name"] = text
                    else:
                        self.user_dates[user_id]["session_name"] = self.bots[self.user_dates[user_id]["bot_index"]]["session_name"]
                    self.user_dates[user_id]["prev_command"] = "edit_bot_api_id"
                    await self.bot.send_message(chat_id=user_id, text="Введіть api_id (напишіть крапку '.' щоб залишити минуле значення):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "edit_bot_api_id":
                    if text != ".":
                        self.user_dates[user_id]["api_id"] = text
                    else:
                        self.user_dates[user_id]["api_id"] = self.bots[self.user_dates[user_id]["bot_index"]]["api_id"]
                    self.user_dates[user_id]["prev_command"] = "edit_bot_api_hash"
                    await self.bot.send_message(chat_id=user_id, text="Введіть api_hash (напишіть крапку '.' щоб залишити минуле значення):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "edit_bot_api_hash":
                    if text != ".":
                        self.user_dates[user_id]["api_hash"] = text
                    else:
                        self.user_dates[user_id]["api_hash"] = self.bots[self.user_dates[user_id]["bot_index"]]["api_hash"]
                    self.user_dates[user_id]["prev_command"] = ""
                    self.edit_bot(self.user_dates[user_id]["bot_index"], {"api_id": self.user_dates[user_id]["api_id"], "api_hash": self.user_dates[user_id]["api_hash"], "session_name": self.user_dates[user_id]["session_name"]})
                    await self.bot.send_message(chat_id=user_id, text="Бота відредаговано!")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                    self.restart_bot(self.bots[self.user_dates[user_id]["bot_index"]])
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_name":
                    self.user_dates[user_id]["prev_command"] = "add_proxy_ip"
                    self.user_dates[user_id]["name"] = text
                    await self.bot.send_message(chat_id=user_id, text="Введіть ip:")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_ip":
                    self.user_dates[user_id]["prev_command"] = "add_proxy_port"
                    self.user_dates[user_id]["ip"] = text
                    await self.bot.send_message(chat_id=user_id, text="Введіть port:")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_port":
                    self.user_dates[user_id]["prev_command"] = "add_proxy_type"
                    self.user_dates[user_id]["port"] = text
                    #self.proxies.append({"name": self.user_dates[user_id]["name"], "ip": self.user_dates[user_id]["ip"], "port": self.user_dates[user_id]["port"]})
                    await self.bot.send_message(chat_id=user_id, text="Напишіть тип проксі (socks5, http, socks4):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                    #self.save_proxies()
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_type":
                    self.user_dates[user_id]["prev_command"] = "add_proxy_login"
                    self.user_dates[user_id]["type"] = text
                    await self.bot.send_message(chat_id=user_id, text="Напишіть логін для проксі (якщо немає, просто поставте крапку '.'):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_login":
                    self.user_dates[user_id]["prev_command"] = "add_proxy_password"
                    self.user_dates[user_id]["login"] = text
                    await self.bot.send_message(chat_id=user_id, text="Напишіть пароль для проксі (якщо немає, просто поставте крапку '.'):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "add_proxy_password":
                    self.user_dates[user_id]["prev_command"] = ""
                    self.user_dates[user_id]["password"] = text
                    if self.user_dates[user_id]["login"] == ".":
                        self.proxies.append(
                            {"name": self.user_dates[user_id]["name"], "ip": self.user_dates[user_id]["ip"],
                             "port": self.user_dates[user_id]["port"], "type": self.user_dates[user_id]["type"]})
                    else:
                        self.proxies.append({"name": self.user_dates[user_id]["name"], "ip": self.user_dates[user_id]["ip"], "port": self.user_dates[user_id]["port"], "type": self.user_dates[user_id]["type"], "login": self.user_dates[user_id]["login"], "password": self.user_dates[user_id]["password"]})
                    await self.bot.send_message(chat_id=user_id, text="Проксі додано!")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                    self.save_proxies()
                elif self.user_dates[user_id]["prev_command"] == "edit_proxy_name":
                    if text != ".":
                        self.user_dates[user_id]["name"] = text
                    else:
                        self.user_dates[user_id]["name"] = self.proxies[self.user_dates[user_id]["proxy_index"]]["name"]
                    self.user_dates[user_id]["prev_command"] = "edit_proxy_ip"
                    await self.bot.send_message(chat_id=user_id, text="Введіть ip (напишіть крапку '.' щоб залишити минуле значення):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "edit_proxy_ip":
                    if text != ".":
                        self.user_dates[user_id]["ip"] = text
                    else:
                        self.user_dates[user_id]["ip"] = self.proxies[self.user_dates[user_id]["proxy_index"]]["ip"]
                    self.user_dates[user_id]["prev_command"] = "edit_proxy_port"
                    await self.bot.send_message(chat_id=user_id, text="Введіть port (напишіть крапку '.' щоб залишити минуле значення):")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                elif self.user_dates[user_id]["prev_command"] == "edit_proxy_port":
                    if text != ".":
                        self.user_dates[user_id]["port"] = text
                    else:
                        self.user_dates[user_id]["port"] = self.proxies[self.user_dates[user_id]["proxy_index"]]["port"]
                    self.user_dates[user_id]["prev_command"] = ""
                    self.proxies[self.user_dates[user_id]["proxy_index"]] = {"name": self.user_dates[user_id]["name"], "ip": self.user_dates[user_id]["ip"], "port": self.user_dates[user_id]["port"]}
                    await self.bot.send_message(chat_id=user_id, text="Проксі відредаговано!")
                    await self.bot.delete_message(chat_id=user_id, message_id=message.message_id)
                    self.save_proxies()
                elif self.user_dates[user_id]["prev_command"] == "enter_phone":
                    if text.count("+") > 0 and len(text) == 13:
                        await self.bot.send_message(chat_id=user_id, text="Телефон введений!")
                        self.subprocess_controller.add_answer(self.user_dates[user_id]["bot_index"], text)
                    else:
                        await self.bot.send_message(chat_id=user_id, text="Телефон повинний бути у форматі +380123456789! Введіть ще раз:")
                elif self.user_dates[user_id]["prev_command"] == "enter_code":
                    await self.bot.send_message(chat_id=user_id, text="Код введений!")
                    text = text.replace("-", "").replace(".", "")
                    self.subprocess_controller.add_answer(self.user_dates[user_id]["bot_index"], text)
                    self.user_dates[user_id]["prev_command"] = ""
                elif self.user_dates[user_id]["prev_command"] == "edit_bot_msg":
                    self.user_dates[user_id]["prev_command"] = ""
                    self.bots[self.user_dates[user_id]["bot_index"]]["message_text"] = text
                    self.edit_bot(self.user_dates[user_id]["bot_index"], self.bots[self.user_dates[user_id]["bot_index"]])
                    await self.bot.send_message(chat_id=user_id, text="Повідомлення відредаговано! (Зачейкайте секунд 15, щоб бот перезавантажився)")
                    self.restart_bot(self.bots[self.user_dates[user_id]["bot_index"]])
                elif self.user_dates[user_id]["prev_command"] == "time_change":
                    self.user_dates[user_id]["prev_command"] = ""
                    try:
                        self.time_to_answer = int(text)
                        await self.bot.send_message(chat_id=user_id,
                                                    text="Час для відповіді змінено! Зачекайте секунд 15-20, поки перезавантажаться боти")
                        for bot in self.bots:
                            index = self.bots.index(bot)
                            bot['time'] = self.time_to_answer
                            self.edit_bot(index, bot)
                        self.restart_all_bots()
                    except Exception as ex:
                        await self.bot.send_message(chat_id=user_id,
                                                    text="Сталася помилка!")



    def get_list_bot_session_names(self):
        list_bot_session_names = []
        for bot in self.bots:
            list_bot_session_names.append(bot['session_name'])
        return list_bot_session_names

    def get_list_proxy_names(self):
        list_proxy_names = []
        for proxy in self.proxies:
            list_proxy_names.append(proxy['name'])
        return list_proxy_names

    def gen_markup_with_menu(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(text="Список ботів", callback_data="list_bots"))
        markup.add(types.InlineKeyboardButton(text="Список проксі", callback_data="list_proxies"))
        markup.add(types.InlineKeyboardButton(text="Перезапуск ботів", callback_data="bot_restart"))
        markup.add(types.InlineKeyboardButton(text="Зміна часу відповіді", callback_data="time_change"))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup

    def markup_bot_menu(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(text="Видалити бота", callback_data="del_bot"))
        markup.add(types.InlineKeyboardButton(text="Редагувати повідомлення", callback_data="edit_bot_msg"))
        markup.add(types.InlineKeyboardButton(text="Перезапуск бота (для застосування змін)", callback_data="restart_bot"))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup


    def markup_list_bots(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for bot in self.bots:
            markup.add(types.InlineKeyboardButton(text=bot['session_name'], callback_data=bot['session_name']))
        markup.add(types.InlineKeyboardButton(text="Додати бота", callback_data="add_bot"))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup

    def markup_list_proxy(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for proxy in self.proxies:
            markup.add(types.InlineKeyboardButton(text=proxy['name'], callback_data=proxy['name']))
        markup.add(types.InlineKeyboardButton(text="Додати проксі", callback_data="add_proxy"))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup

    def markup_simple_list_bots(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for bot in self.bots:
            markup.add(types.InlineKeyboardButton(text=bot['session_name'], callback_data=bot['session_name']))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup

    def markup_simple_list_proxy(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        for proxy in self.proxies:
            markup.add(types.InlineKeyboardButton(text=proxy['name'], callback_data=proxy['name']))
        markup.add(types.InlineKeyboardButton(text="Без проксі", callback_data="Без проксі"))
        return markup

    def markup_proxy_menu(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton(text="Видалити проксі", callback_data="del_proxy"))
        markup.add(types.InlineKeyboardButton(text="Редагувати проксі", callback_data="edit_proxy"))
        markup.add(types.InlineKeyboardButton(text="Додати проксі до бота", callback_data="add_bot_proxy"))
        markup.add(types.InlineKeyboardButton(text="Відміна", callback_data="cancel"))
        return markup

    def add_bot(self, bot):
        self.bots.append(bot)
        self.subprocess_controller.add_bot({"api_id": bot["api_id"], "api_hash": bot["api_hash"], "session_name": bot["session_name"], "proxy": bot.get("proxy", None), "message_text": bot.get("message_text", "Test message"), "time": bot.get("time", self.time_to_answer)})
        self.save_bots()

    def del_bot(self, index: int):
        bot = self.bots.pop(index)
        self.subprocess_controller.del_bot(self.subprocess_controller.get_bot(self.subprocess_controller.get_bot_index_by_session_name(bot["session_name"])))
        self.save_bots()

    def edit_bot(self, index: int, bot):
        self.bots[index] = bot
        self.subprocess_controller.edit_bot(self.subprocess_controller.get_bot(
            self.subprocess_controller.get_bot_index_by_session_name(bot["session_name"])), {"api_id": bot["api_id"], "api_hash": bot["api_hash"], "session_name": bot["session_name"], "proxy": bot.get("proxy", None), "message_text": bot.get("message_text", "Test message"), "time": bot.get("time", self.time_to_answer)})
        self.save_bots()

    def save_bots(self):
        with open('bots.pickle', 'wb') as f:
            pickle.dump(self.bots, f)

    def load_bots(self):
        try:
            with open('bots.pickle', 'rb') as f:
                self.bots = pickle.load(f)
        except Exception as e:
            pass

    def save_proxies(self):
        with open('proxies.pickle', 'wb') as f:
            pickle.dump(self.proxies, f)

    def load_proxies(self):
        try:
            with open('proxies.pickle', 'rb') as f:
                self.proxies = pickle.load(f)
        except Exception as e:
            pass

    def save_id_admin_and_password(self):
        with open('id_admin_and_password.pickle', 'wb') as f:
            pickle.dump({"id_admin": self.id_admin, "admin_password": self.admin_password}, f)

    def load_id_admin_and_password(self):
        try:
            with open('id_admin_and_password.pickle', 'rb') as f:
                tmp = pickle.load(f)
                self.id_admin = tmp["id_admin"]
                self.admin_password = tmp["admin_password"]
        except Exception as e:
            pass

    def stop_bot(self, bot):
        self.subprocess_controller.stop_bot(self.subprocess_controller.get_bot(
            self.subprocess_controller.get_bot_index_by_session_name(bot["session_name"])))

    def start_bot(self, bot):
        self.loop.create_task(
        self.subprocess_controller.start_bot(self.subprocess_controller.get_bot(
            self.subprocess_controller.get_bot_index_by_session_name(bot["session_name"]))))
    def start_bots(self, bots):
        for bot in bots:
            self.start_bot(bot)

    def restart_all_bots(self):
        self.subprocess_controller.restart_all_bots()

    def restart_bot(self, bot):
        self.subprocess_controller.restart_bot(self.subprocess_controller.get_bot(
            self.subprocess_controller.get_bot_index_by_session_name(bot["session_name"])))

    async def wait_tasks(self):
        while True:
            if self.user_dates.get(self.id_admin, None) == None:
                self.user_dates[self.id_admin] = {}
            await asyncio.sleep(1)
            if len(self.subprocess_controller.tasks) > 0:
                task = self.subprocess_controller.tasks[0]
                bot_index = task["bot_index"]
                bot_tmp = self.subprocess_controller.get_bot(bot_index)
                task_text = task["task"]
                if task_text == "phone" and self.user_dates[self.id_admin].get("prev_command", "") != "enter_phone":
                    await self.bot.send_message(chat_id=self.id_admin, text="Введіть номер телефону бота з назвою "+bot_tmp["session_name"]+":")
                    self.user_dates[self.id_admin] = {"prev_command": "enter_phone", "bot_index": bot_index}
                elif task_text == "code" and self.user_dates[self.id_admin].get("prev_command", "") == "enter_phone":
                    await self.bot.send_message(chat_id=self.id_admin,
                                                text="На акаунт бота було надіслано код, введіть його (приклад код 123456, ви вводите 1-2-3-4-5-6, або 1.2.3.4.5.6). Бот з назвою " + bot_tmp[
                                                    "session_name"] + ":")
                    self.user_dates[self.id_admin] = {"prev_command": "enter_code", "bot_index": bot_index}

    async def try_start_polling(self):
        try:
            await self.bot.polling()
        except Exception as ex:
            sys.exit(1)

    def start(self):
        self.loop.create_task(self.try_start_polling())
        self.loop.create_task(self.wait_tasks())
        print("STARTED TG")