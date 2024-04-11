from os import remove,environ
from discord import File,Intents,Client
from telebot.async_telebot import AsyncTeleBot
from threading import Thread
from asyncio import run,sleep,Queue,create_task
DISCORD_TOKEN = environ["DISCORD_TOKEN"]
DISCORD_SERVER = environ["DISCORD_SERVER"]
DISCORD_CHANNEL = environ["DISCORD_CHANNEL"]
DISCORD_PERMISSIONS = Intents()
DISCORD_PERMISSIONS.messages=True
DISCORD_PERMISSIONS.message_content = True
DISCORD_PERMISSIONS.members = True
DISCORD_PERMISSIONS.guilds = True
TELEGRAM_TOKEN = environ["TELEGRAM_TOKEN"]
GROUP_ID = environ["TELEGRAM_GROUP"]
SEND_THREAD_ID = environ["TELEGRAM_SEND_THREAD"]
RECIEVE_THREAD_ID_LIST = (environ["TELEGRAM_RECV_THREAD"],)

class Telegram():
    def __init__(self,telegram_queue:Queue, discord_queue:Queue) -> None:
        self.bot = AsyncTeleBot(TELEGRAM_TOKEN)
        self.telegram_queue = telegram_queue
        self.discord_queue = discord_queue
        self.MEDIA_METHODS = {
            'jpg': self.bot.send_photo,
            'jpeg':self.bot.send_photo,
            'png': self.bot.send_photo,
            'gif': self.bot.send_animation,
            'mp4': self.bot.send_video,
            'mov': self.bot.send_video,
            'avi': self.bot.send_video,
        }
    async def bot_thread(self):
        async def queue_monitor(self):
            while True:
                if(not self.discord_queue.empty()):
                    path = await self.discord_queue.get()
                    ext = path.split('.')[-1].lower()
                    try:
                        with open(path,"br") as file:
                            await self.MEDIA_METHODS[ext](GROUP_ID,file,message_thread_id=SEND_THREAD_ID)
                    except KeyError:pass
                    except Exception as E:print(str(E))
                    finally:self.discord_queue.task_done()
                await sleep(1)
        @self.bot.message_handler(content_types=["photo"])
        async def _3c(message):
            if(not message.message_thread_id in RECIEVE_THREAD_ID_LIST):
                print(f"{message.message_thread_id}")
                return
            print(f"Отправляем мем {message.from_user.username}")
            path = f"{message.photo[-1].file_unique_id}.png"
            with open(f"{message.photo[-1].file_unique_id}.png","wb") as pic:
                file = await self.bot.get_file(message.photo[-1].file_id)
                pic.write(await self.bot.download_file(file.file_path))
            await self.telegram_queue.put(path)
        @self.bot.message_handler(content_types=["video"])
        async def _3c(message):
            if(not message.message_thread_id in RECIEVE_THREAD_ID_LIST):
                print(f"Из канала '{message.message_thread_id}' не отправляем")
                return
            print(f"Отправляем мем {message.from_user.username} из канала '{message.message_thread_id}'")
            path = f"{message.video.file_unique_id}.mp4"
            with open(path,"wb") as vid:
                file = await self.bot.get_file(message.video.file_id)
                vid.write(await self.bot.download_file(file.file_path))
            await self.telegram_queue.put(path)
        
        _ = create_task(queue_monitor(self))
        await self.bot.polling() 
    def main(self): 
        run(self.bot_thread())
class DiscordBot(Client):
    def __init__(self, telegram_queue:Queue, discord_queue:Queue, channel_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_queue = telegram_queue
        self.discord_queue = discord_queue
        self.channel_id = channel_id

    async def send_file(self, file_path):
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send(file=File(file_path))
        remove(file_path)
    async def on_message(self,message): 
        if (message.author == self.user) or (Len:=len(message.attachments)==0):
            return
        print(f"Отправляем мем{'ы' if Len>1 else ''} {message.author} в количестве {Len}") 
        for attachment in message.attachments:
            file_path = attachment.filename
            await attachment.save(file_path)
            await self.discord_queue.put(file_path)
    async def check_queue_and_send(self):
        while True:
            if not self.telegram_queue.empty():
                await self.send_file(await self.telegram_queue.get())
                self.telegram_queue.task_done()
            await sleep(1)
telegram_queue = Queue()
discord_queue = Queue()
bot = DiscordBot(telegram_queue,discord_queue, DISCORD_CHANNEL,intents=DISCORD_PERMISSIONS)
@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе')
    bot.loop.create_task(bot.check_queue_and_send())
Thread(target=Telegram(telegram_queue,discord_queue).main,daemon=True,name="TELEGRAM").start()
Thread(target=bot.run,args=[DISCORD_TOKEN],daemon=True,name="DISCORD").start()
try:
    while True:
        input()
except KeyboardInterrupt: 
    quit()