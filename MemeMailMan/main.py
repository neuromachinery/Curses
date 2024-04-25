from os import remove,path
from sys import argv
from discord import File,Intents,Client
from telebot.async_telebot import AsyncTeleBot
from threading import Thread
from asyncio import run,sleep,Queue,create_task
from dotenv import load_dotenv, dotenv_values
from routing import ROUTING
load_dotenv()
config = dotenv_values(".env")

CWD = path.dirname(argv[0])

DISCORD_TOKEN = config["DISCORD_TOKEN"]
DISCORD_SERVER = int(config["DISCORD_SERVER"])
DISCORD_PERMISSIONS = Intents()
DISCORD_PERMISSIONS.messages=True
DISCORD_PERMISSIONS.message_content = True
DISCORD_PERMISSIONS.members = True
DISCORD_PERMISSIONS.guilds = True

TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
GROUP_ID = config["TELEGRAM_GROUP"]

def readable_string(string:str): 
    return all(ord(char) < 128 or (1040 <= ord(char) <= 1103) for char in string)
def readable_iterable(strings,default:str):
    return next((item for item in strings if readable_string(item)), default)
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
            'avi': self.bot.send_video
        }
    async def bot_thread(self):
        async def queue_monitor(self):
            while True:
                if(not self.discord_queue.empty()):
                    text,Path,channel = await self.discord_queue.get()
                    if(not Path):
                        await self.bot.send_message(GROUP_ID,text=text,message_thread_id=channel)
                        self.discord_queue.task_done()
                        continue
                    ext = Path.split('.')[-1].lower()
                    try:
                        with open(Path,"br") as file:
                            await self.MEDIA_METHODS[ext](GROUP_ID,file,message_thread_id=channel,caption=text)
                        remove(Path)
                    except KeyError:pass
                    except Exception as E:print(str(E))
                    finally:self.discord_queue.task_done()
                await sleep(1)
        @self.bot.message_handler(content_types=["text","sticker","photo","video","gif"])
        async def _(message):
            if(not (channel:=message.message_thread_id) in ROUTING):
                print(f"{channel} не смотрим")
                return
            channel = ROUTING[ROUTING.index(channel)].ID_to
            text = message.text if message.text else message.caption
            text = "" if not text else text
            user = message.from_user
            user = readable_iterable((user.full_name,user.first_name,user.last_name,user.username),user.id)
            if(not (message.photo or message.video or message.sticker)):
                print(f"{user}:{message.text}")
                await self.telegram_queue.put((f"{user}:{text}",None,channel))
                return
            ext = "png" if message.photo or not message.sticker.is_video else "mp4"
            media = next((var for var in (message.photo,message.video,message.sticker) if var),None) # define media by what there is in the message.
            media = media[-1] if isinstance(media,list) else media # if it's message.photo
            print(f"{user}:{ext} ({message.message_thread_id} -> {channel}) ")
            Path = path.join(CWD,"media",f"{media.file_unique_id}.{ext}")
            with open(Path,"wb") as pic:
                file = await self.bot.get_file(media.file_id)
                pic.write(await self.bot.download_file(file.file_path))
            await self.telegram_queue.put((f"{user}:{text}",Path,channel))
        _ = create_task(queue_monitor(self))
        await self.bot.polling() 
    def main(self): 
        while True:
            try:run(self.bot_thread())
            except Exception as E:
                print(str(E))

class DiscordBot(Client):
    def __init__(self, telegram_queue:Queue, discord_queue:Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_queue = telegram_queue
        self.discord_queue = discord_queue

    async def send_file(self, text, file_path, channel):
        channel = self.get_channel(channel)
        if not channel:return
        if text: await channel.send(text)
        if file_path: 
            await channel.send(file=File(file_path))
            remove(file_path)
    async def on_message(self,message): 
        if (message.author == self.user):
            return
        if (not (channel:=message.channel.id) in ROUTING):
            print(f"{channel} не смотрим")
            return
        file_path = None
        for attachment in message.attachments:
            file_path = path.join(CWD,"media",attachment.filename)
            await attachment.save(file_path)
        user = message.author
        user = readable_iterable((user.display_name,user.name,user.global_name),user.id)
        print(f"{user}:'{message.content}' ({channel} -> {ROUTING[ROUTING.index(channel)].ID_to})")
        await self.discord_queue.put((f"{user}:{message.content}",file_path,ROUTING[ROUTING.index(message.channel.id)].ID_to))
    async def check_queue_and_send(self):
        while True:
            if not self.telegram_queue.empty():
                await self.send_file(*await self.telegram_queue.get())
                self.telegram_queue.task_done()
            await sleep(1)
telegram_queue = Queue()
discord_queue = Queue()
bot = DiscordBot(telegram_queue,discord_queue,intents=DISCORD_PERMISSIONS)
@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе\nМониторим каналы({[channel.ID_from for channel in ROUTING]}) отправляем в {[channel.ID_to for channel in ROUTING]}')
    bot.loop.create_task(bot.check_queue_and_send())
Thread(target=Telegram(telegram_queue,discord_queue).main,daemon=True,name="TELEGRAM").start()
Thread(target=bot.run,args=[DISCORD_TOKEN],daemon=True,name="DISCORD").start()
try:
    while True:
        input()
except KeyboardInterrupt: 
    quit()