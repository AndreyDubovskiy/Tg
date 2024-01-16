from telethon import TelegramClient, events, sync
import os
import time
import asyncio
import pickle
import python_socks
from telethon.tl.types import PeerUser, PeerChat

message_text_def = "https://t.me/+lnPE5CffxQ45ZDcy\nЦе чат для робочих щоб не обяснять кожному  про роботу і  що потрібно робить. Там все написано, якщо підходить то постав + і свій номер."
class ClientObject:
    def __init__(self, api_id: int, api_hash: str, session_name: str, proxy: dict = None, message_text: str = message_text_def, time_to_answer: int = 60):
        with open('sync'+session_name, 'wb') as f:
            pickle.dump("on", f)
        if message_text == None or message_text == "Test message":
            self.message_text = message_text_def
        else:
            self.message_text = message_text
        self.message_text = self.message_text.replace("\\n", "\n")
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.proxy = proxy
        self.loop = asyncio.get_event_loop()
        self.user_dates = {} # {user_id: last_message_date}
        self.user_answered = [] # [user_id]
        self.load_all()
        self.time_to_answer = time_to_answer # seconds
        if time_to_answer == None:
            self.time_to_answer = 60
        else:
            self.time_to_answer = int(time_to_answer)
        self.client = None
        if self.proxy:
            type_proxy = 0
            if self.proxy['proxy_type'] == 'socks4':
                type_proxy = python_socks.ProxyType.SOCKS4
            elif self.proxy['proxy_type'] == 'socks5':
                type_proxy = python_socks.ProxyType.SOCKS5
            elif self.proxy['proxy_type'] == 'http':
                type_proxy = python_socks.ProxyType.HTTP
            if self.proxy.get('proxy_login', None) != None:
                print(type_proxy, self.proxy['proxy_ip'], int(self.proxy['proxy_port']), True, self.proxy['proxy_login'], self.proxy['proxy_password'])
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash, proxy=(type_proxy, self.proxy['proxy_ip'], int(self.proxy['proxy_port']), True, self.proxy['proxy_login'], self.proxy['proxy_password']))
            else:
                print(type_proxy, self.proxy['proxy_ip'], int(self.proxy['proxy_port']))
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash, proxy=(
                type_proxy, self.proxy['proxy_ip'], int(self.proxy['proxy_port'])))
        else:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        self.client.start()
        self.init_file_sync()

        @self.client.on(events.NewMessage(incoming=True, outgoing=None))
        async def handler(event):
            if event.__class__.__name__ in ["UpdateShortMessage", "UpdateNewMessage"]:
                if event.__class__.__name__ == "UpdateShortMessage":
                    tmp = event
                    user_id = event.user_id
                else:
                    tmp = event.message
                    user_id = event.message.peer_id.user_id
                try:
                    if not tmp.out:
                        if user_id not in self.user_dates and user_id not in self.user_answered:
                            self.user_dates[user_id] = time.time()
                            entyty = await self.client.get_input_entity(PeerUser(user_id))
                            self.loop.create_task(self.wait_to_answer(user_id, entity=entyty))
                        self.user_dates[user_id] = time.time()
                except Exception as e:
                    pass

        self.client.add_event_handler(handler)

    def delete_saved_data(self):
        if os.path.exists('user_answered'+self.session_name):
            os.remove('user_answered'+self.session_name)

    def load_all(self):
        if os.path.exists('user_answered'+self.session_name):
            self.load_user_answered()
        else:
            self.save_user_answered()

    def save_user_answered(self):
        with open('user_answered'+self.session_name, 'wb') as f:
            pickle.dump(self.user_answered, f)

    def load_user_answered(self):
        with open('user_answered'+self.session_name, 'rb') as f:
            self.user_answered = pickle.load(f)

    def init_file_sync(self):
        with open('sync'+self.session_name, 'wb') as f:
            pickle.dump("on", f)
        self.loop.create_task(self.check_sync())

    def sync(self):
        tmp = ""
        with open('sync'+self.session_name, 'rb') as f:
            tmp = pickle.load(f)
        return tmp

    async def start(self):
        await self.client.run_until_disconnected()

    async def check_sync(self):
        while True:
            await asyncio.sleep(10)
            if self.sync() == "off":
                with open('sync'+self.session_name, 'wb') as f:
                    pickle.dump("off_finished", f)
                exit(0)


    async def wait_to_answer(self, user_id: str, entity = None):
        while True:
            await asyncio.sleep(10)
            if time.time() - self.user_dates[user_id] > self.time_to_answer:
                if entity == None:
                    await self.send_message(user_id, self.message_text)
                else:
                    await self.send_message(entity, self.message_text)
                self.user_answered.append(user_id)
                self.user_dates.pop(user_id)
                self.save_user_answered()
                break

    async def send_message(self, user_id, message: str):
        await self.client.send_message(user_id, message)