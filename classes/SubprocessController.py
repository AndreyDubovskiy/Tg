import asyncio
import os
import pickle

class SubprocessController:
    def __init__(self):
        self.bots = [] # { "api_id": 123, "api_hash": "123", "session_name": "session_name" }
        self.proccesses = []
        self.last_console_msg = []
        self.loop = asyncio.get_event_loop()
        self.tasks = [] # { "bot_index": bot_index, "task": task }
        self.answers = [] # { "bot_index": bot_index, "answer": answer }

    def get_bot_index_by_session_name(self, session_name):
        for bot in self.bots:
            if bot['session_name'] == session_name:
                return self.bots.index(bot)
        return None

    def get_bot(self, bot_index):
        return self.bots[bot_index]
    def add_bot(self, bot):
        self.bots.append(bot)
        self.last_console_msg.append("")
        self.proccesses.append(None)

    def del_bot(self, bot):
        self.stop_bot(bot)
        index = self.bots.index(bot)
        self.bots.pop(index)
        self.last_console_msg.pop(index)
        self.proccesses.pop(index)
        self.loop.create_task(self.wait_for_delete_file(bot))



    def edit_bot(self, bot, new_bot):
        index = self.bots.index(bot)
        self.bots[index] = new_bot

    def get_task(self, bot_index):
        for task in self.tasks:
            if task['bot_index'] == bot_index:
                return task
        return None

    def get_answer(self, bot_index):
        for answer in self.answers:
            if answer['bot_index'] == bot_index:
                return answer
        return None

    def add_answer(self, bot_index, answer):
        self.answers.append({"bot_index": bot_index, "answer": answer})

    def del_answer(self, index):
        self.answers.pop(index)

    def add_task(self, bot_index, task):
        self.tasks.append({"bot_index": bot_index, "task": task})

    def del_task(self, index):
        self.tasks.pop(index)

    async def wait_answer(self, bot_index):
        while True:
            await asyncio.sleep(1)
            answer = self.get_answer(bot_index)
            if answer:
                self.del_answer(bot_index)
                self.del_task(bot_index)
                return answer['answer']


    async def while_msg_console(self, process):
        while True:
            print("read")
            try:
                await asyncio.sleep(1)
                stdout = await process.stdout.read(100)
                index = self.proccesses.index(process)
                if stdout:
                    self.last_console_msg[index] = stdout.decode()
                    if stdout.decode().count("Please enter your phone (or bot token):") > 0:
                        print("phone")
                        self.add_task(index, "phone")
                        answer = await self.wait_answer(index)
                        process.stdin.write((answer+"\n").encode())
                    elif stdout.decode().count("Please enter the code you received:") > 0:
                        print("code")
                        self.add_task(index, "code")
                        answer = await self.wait_answer(index)
                        process.stdin.write((answer+"\n").encode())
                        break
            except Exception as e:
                break
    async def start_bot(self, bot):
        with open('sync'+bot['session_name'], 'wb') as f:
            pickle.dump("on", f)
        process = None
        if bot.get('proxy') and bot.get('message_text'):
            process = await asyncio.create_subprocess_shell("python classes/ClientSubProcess.py" + " -a " + str(bot['api_id']) + " -ah " + bot['api_hash'] + " -s " + bot['session_name'] + " -pi " + bot['proxy']['ip'] + " -pp " + bot['proxy']['port'] + " -pt " + bot['proxy']['type'] + " -pl " + bot['proxy'].get('login', '.') + " -ppass " + bot['proxy'].get('password', '.') + " -m \"" + bot['message_text'].replace("\n", "\\n")+ "\""+" -time " + str(bot.get('time', 60)),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        elif bot.get('proxy'):
            process = await asyncio.create_subprocess_shell("python classes/ClientSubProcess.py" + " -a " + str(bot['api_id']) + " -ah " + bot['api_hash'] + " -s " + bot['session_name'] + " -pi " + bot['proxy']['ip'] + " -pp " + bot['proxy']['port'] + " -pt " + bot['proxy']['type'] + " -pl " + bot['proxy'].get('login', '.') + " -ppass " + bot['proxy'].get('password', '.')+" -time " + str(bot.get('time', 60)),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        elif bot.get('message_text'):
            process = await asyncio.create_subprocess_shell("python classes/ClientSubProcess.py" + " -a " + str(bot['api_id']) + " -ah " + bot['api_hash'] + " -s " + bot['session_name'] + " -m \"" + bot['message_text'].replace("\n", "\\n")+ "\""+" -time " + str(bot.get('time', 60)),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            process = await asyncio.create_subprocess_shell("python classes/ClientSubProcess.py" + " -a " + str(bot['api_id']) + " -ah " + bot['api_hash'] + " -s " + bot['session_name']+" -time " + str(bot.get('time', 60)),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )


        print("Start with", bot)
        index = self.bots.index(bot)
        self.proccesses[index] = process
        await self.while_msg_console(process)

    def start_all_bots(self):
        for bot in self.bots:
            self.loop.create_task(self.start_bot(bot))

    def restart_all_bots(self):
        for bot in self.bots:
            self.restart_bot(bot)

    def stop_bot(self, bot):
        tmp = ""
        with open('sync' + bot['session_name'], 'rb') as f:
            tmp = pickle.load(f)
        if tmp != "off":
            print("STOP", bot)
            with open('sync'+bot['session_name'], 'wb') as f:
                pickle.dump("off", f)

    async def wait_for_delete_file(self, bot):
        while True:
            await asyncio.sleep(5)
            tmp = ""
            with open('sync'+bot['session_name'], 'rb') as f:
                tmp = pickle.load(f)
            if tmp == "off_finished":
                try:
                    os.remove('sync' + bot['session_name'])
                except Exception as e:
                    print("ERROR delete sync file")
                try:
                    os.remove('user_answered' + bot['session_name'])
                except Exception as e:
                    print("ERROR delete user_answered file")
                try:
                    os.remove(bot['session_name'] + '.session')
                except Exception as e:
                    print("ERROR delete session file")
                print("DELETED BOT", bot)
                break
    async def wait_for_restart(self, bot):
        while True:
            await asyncio.sleep(5)
            tmp = ""
            with open('sync'+bot['session_name'], 'rb') as f:
                tmp = pickle.load(f)
            if tmp == "off_finished":
                self.loop.create_task(self.start_bot(bot))
                break

    def restart_bot(self, bot):
        self.stop_bot(bot)
        self.loop.create_task(self.wait_for_restart(bot))