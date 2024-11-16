from os import remove,path,listdir
from sys import argv
from discord import File,Intents,Client, Interaction, app_commands,Object
from telebot.async_telebot import AsyncTeleBot
from telebot import ExceptionHandler
from telebot.apihelper import ApiTelegramException
from threading import Thread,Event
from asyncio import run,sleep,Queue,QueueEmpty,create_task
from traceback import format_exc
from dotenv import load_dotenv, dotenv_values
from discord import app_commands
from discord.ext import commands
from socketio import AsyncClient,exceptions

CLI_START_FLAG = Event()
EXIT_FLAG = Event()
exitSignal = EXIT_FLAG.set

PROCESS_DELAY = 0.5
HOST = "127.0.0.1"
MMM_PORT = 54323
DB_PORT = 54321
SITE_PORT = 54322 
ADDRESS_DICT = {
    "DB":(HOST,DB_PORT),
    "MMM":(HOST,MMM_PORT),
    "SITE":(HOST,SITE_PORT)
}

from routing import ROUTING
log_queue = Queue()
get_queue = Queue()
req_queue = Queue()
def get_queue_f():
    try:return get_queue.get_nowait()
    except QueueEmpty:return None

import FileManager
from DBconnect import SocketTransiever

Transiever = SocketTransiever()
LOGGER = lambda *args:Transiever.send_message(sock=ADDRESS_DICT["DB"],sender_name=args[0],message_type="LOG",message=args[1:])
#getData = get_queue_f
#reqData = lambda *args:req_queue.put_nowait(args)


telegram_queue = Queue()
discord_queue = Queue()
site_queue = Queue()
queues = {telegram_queue,site_queue}
#queues = {telegram_queue,discord_queue,site_queue}
from datetime import datetime

load_dotenv()
config = dotenv_values(".env")

#CWD = path.dirname(argv[0])
CWD = path.dirname(path.realpath(__file__))
SITE_URL = config["SITE_URL"]
DISCORD_TOKEN = config["DISCORD_TOKEN"]
DISCORD_SERVER = int(config["DISCORD_SERVER"])
DISCORD_PERMISSIONS = Intents()
DISCORD_PERMISSIONS.messages=True
DISCORD_PERMISSIONS.message_content = True
DISCORD_PERMISSIONS.members = True
DISCORD_PERMISSIONS.guilds = True

TELEGRAM_TOKEN = config["TELEGRAM_TOKEN"]
GROUP_ID = config["TELEGRAM_GROUP"]

FILES_DIRECTORY = FileManager.SharedDirectory
MEDIA_PATH = path.join(CWD,"media")
LOCALE = {
    "RU":{
        "default":"<ошибка>",
        "file_list":"Список всех доступных директорий: ",
        "help":"Список команд: ",
        "arg":"параметр",
        "packing":"Упаковываем файлы",
        "sending":"Отправляем файлы. Кол-во: ",
        "discord_download_desc":"Скачать директорию используя несколько архивов",
        "discord_list_desc":"Отображение доступных директорий",
        "discord_download_param_desc":"Выбранная директория",
        "file_channel_ban":"В этом канале нельзя срать файлами",
        "file_not_found":"Директория не найдена",
        "me_desc":"Ваш ID: ",
        "":"",
        "":"",
        },
    "EN":{
        "default":"<error>",
        "file_list":"List of accessable directories: ",
        "help":"List of commands: ",
        "arg":"argument",
        "packing":"Packing files",
        "sending":"Sending files. File count: ",
        "discord_download_desc":"Download directory using zip volumes",
        "discord_download_param_desc":"Directory of choice",
        "discord_list_desc":"List of downloadable directories",
        "file_channel_ban":"File-shitting is prohibited for this channel",
        "file_not_found":"Directory not found",
        "me_desc":"Your ID: ",
        "":"",
        "":"",
        }
    }
locale = lambda arg:LOCALE[DEFAULT_LOCALE].get(arg,LOCALE[DEFAULT_LOCALE]["default"])
DEFAULT_LOCALE = "RU"
FILES_DISCORD_BLACKLIST = [
    936569889999699988,
    922499261319499867,
    1072222440295497748,
    808073771532812301,
    812618354732695574,
    1233431876870606972,
    867905016223105034,
    812614680409276438,
    867803368071495750,
    868491996052983818,
    808077556070219806,
]
FILES_TELEGRAM_BLACKLIST = [
    1,
    32,
    30,
    28,
    418,
    124,
    977,
    34,
]
T_COMMANDS = [
    "download <arg>",
    "list"
]

DISCORD_FILE_LIMIT=int(24.99*1024*1024)
TELEGRAM_FILE_LIMIT=int(49.9*1024*1024)

MISCELLANIOUS_LOGS_TABLE = "LogsMisc"
TELEGRAM_LOGS_TABLE = "LogsTelegram"
DISCORD_LOGS_TABLE =  "LogsDiscord"
ROUTING_TABLE = "Routing"
TABLES = (MISCELLANIOUS_LOGS_TABLE,
          TELEGRAM_LOGS_TABLE,
          DISCORD_LOGS_TABLE,
          ROUTING_TABLE)
CONTENT_LIMIT = 30

def readable_string(string:str): 
    return all(ord(char) < 128 or (1040 <= ord(char) <= 1103) for char in string)
def readable_iterable(strings,default:str):
    return next((item for item in strings if readable_string(item)), default)
def buffer_clear():
    [remove(file) for file in listdir(FileManager.Buffer)]
def now():
    return datetime.now().strftime("[%d.%m.%Y@%H:%M:%S]")

class exception_handler(ExceptionHandler):
    def handle(self,exception,*args,**kwargs):
        LOGGER("MMM",MISCELLANIOUS_LOGS_TABLE,(str(exception)+";".join(map(str,args)),now()))
        return True
class Telegram():
    def __init__(self,telegram_queue:Queue,exception_handler:ExceptionHandler) -> None:
        self.name = "Telegram"
        self.bot = AsyncTeleBot(TELEGRAM_TOKEN,exception_handler=exception_handler)
        self.queue = telegram_queue
        self.subscribers = queues.difference({self.queue})
        self.MEDIA_METHODS = {
            'jpg': (self.bot.send_photo,"photo"),
            'jpeg':(self.bot.send_photo,"photo"),
            'png': (self.bot.send_photo,"photo"),
            'gif': (self.bot.send_animation,""),
            'mp4': (self.bot.send_video,),
            'mov': (self.bot.send_video,),
            'avi': (self.bot.send_video,)
        }
    async def bot_thread(self):
        async def queue_monitor(self:Telegram):
            while not EXIT_FLAG.is_set():
                if(self.queue.empty()):
                    await sleep(1)
                    continue
                message,Path,channel = await self.queue.get()
                channel = ROUTING[ROUTING.index(channel)].ID_to
                user,text,msg_time = message
                text = f"{user} {msg_time}: \n  {text}"
                keyword_args = {"chat_id":GROUP_ID,"message_thread_id":channel} if type(channel)==int else {"chat_id":channel}
                if(not Path):
                    await self.bot.send_message(**keyword_args,text=text)
                    self.queue.task_done()
                    continue
                ext = Path.split('.')[-1].lower()
                try:
                    with open(Path,"br") as file:
                        method,argument_name = self.MEDIA_METHODS.get(ext,self.bot.send_document)
                        keyword_args.update({argument_name:file})
                        await method(**keyword_args,caption=text)
                    remove(Path)
                except Exception as E:
                    LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(str(E),now()))
                finally:self.queue.task_done()
        @self.bot.message_handler(commands=["me"])
        async def me(message):
            await self.bot.send_message(message.chat.id,f"{LOCALE[DEFAULT_LOCALE]['me_desc']}{message.chat.id}")
        @self.bot.message_handler(commands=["start"])
        async def start(message):
            cmds = "\n".join(["/"+cmd.replace('<arg>',locale('arg')) for cmd in T_COMMANDS])
            await self.bot.send_message(message.chat.id,f"{locale('help')}\n{cmds}")
        @self.bot.message_handler(commands=["download"])
        async def file_download(message):
            time = now()
            ret_id = message.chat.id
            if ret_id in FILES_TELEGRAM_BLACKLIST:
                return
            dirname = message.text.removeprefix("/download").strip()
            if not dirname in FileManager.dirList(FILES_DIRECTORY):
                return
            bot_message = await self.bot.send_message(ret_id,locale("packing"),reply_to_message_id=message.message_id)
            zips = FileManager.filePack(dirname,TELEGRAM_FILE_LIMIT)
            if type(zips)==str:
                LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(zips,time))
                buffer_clear()
                return
            zips_amount = len(zips)
            await self.bot.edit_message_text(f"{locale('sending')}{zips_amount}",ret_id,bot_message.message_id)
            for i,zipfile in enumerate(zips,start=1):
                with open(zipfile,"br") as file:
                    await self.bot.send_document(ret_id,file,reply_to_message_id=message.message_id,caption=f"{i}/{zips_amount}")
                remove(zipfile)
        @self.bot.message_handler(commands=["files","list"])
        async def file_list(message):
            ret_id = message.chat.id
            files = ";\n".join(FileManager.dirList(FILES_DIRECTORY))
            text = f'{locale("file_list")}\n{files}'
            await self.bot.send_message(ret_id,text)
        @self.bot.message_handler(commands=["test"])
        async def test(message):
            try:
                request = ((message.from_user.username,message.text,now()),None,30)
                [await queue.put(request) for queue in self.subscribers]
            except Exception as E:
                LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(str(E),now()))
        @self.bot.message_handler(content_types=["text","sticker","photo","video","gif"])
        async def messages(message):
            time = now()
            if(not (channel:=message.message_thread_id) in ROUTING):
                LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
                return
            text = message.text if message.text else message.caption
            text = "" if not text else text
            user = message.from_user
            user = readable_iterable((user.full_name,user.first_name,user.last_name,user.username),user.id)
            if(not (message.photo or message.video or message.sticker)):
                LOGGER(self.name,TELEGRAM_LOGS_TABLE,(user,message.text,"",time,message.message_thread_id))
                request = ((user,text,time),None,channel)
                [await queue.put(request) for queue in self.subscribers]
                return
            ext = "png" if message.photo or (message.sticker and not message.sticker.is_video) else "mp4"
            media = next((var for var in (message.photo,message.video,message.sticker) if var),None) # define media by what there is in the message.
            media = media[-1] if isinstance(media,list) else media # if it's message.photo
            LOGGER(self.name,TELEGRAM_LOGS_TABLE,(user,text,media.file_unique_id,time,message.message_thread_id))
            Path = path.join(MEDIA_PATH,f"{media.file_unique_id}.{ext}")
            with open(Path,"wb") as pic:
                file = await self.bot.get_file(media.file_id)
                pic.write(await self.bot.download_file(file.file_path))
            request = ((user,text+f" [{media.file_unique_id}.{ext}]",time),Path,channel)
            [await queue.put(request) for queue in self.subscribers]
        _ = create_task(queue_monitor(self))
        await self.bot.polling() 
    def main(self): 
        while not EXIT_FLAG.is_set():
            try:
                run(self.bot_thread())
            except Exception as E:
                LOGGER(MISCELLANIOUS_LOGS_TABLE,(str(E),now()))
                EXIT_FLAG.set()
class Site():
    def __init__(self,site_queue:Queue,*args,**kwargs):
        self.name = "MMM_SITE"
        self.server_url = SITE_URL
        self.queue = site_queue
        self.subscribers = queues.difference({self.queue})
        self.sio = AsyncClient()

        # Регистрация обработчиков событий
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('receive_message', self.on_message)

    async def connect(self):
        await self.sio.connect(self.server_url)
    async def disconnect(self):
        await self.sio.disconnect()
    async def send_message(self, message):
        await self.sio.emit('send_message', message)

    def on_connect(self):
        print('Server connected')

    def on_disconnect(self):
        print("Server disconnected")

    def on_message(self, data):
        if "external" in data and data["external"]:
            return
        request = ((data["name"],data["message"],data["time"]),data["unique_id"],data["channel"])
        [queue.put_nowait(request) for queue in self.subscribers]
    async def process_queue(self):
        while not EXIT_FLAG.is_set():
            try:
                await self.connect()
                while not EXIT_FLAG.is_set():
                    if(self.queue.empty()):
                        await sleep(0.5)
                        continue
                    thing = await self.queue.get()
                    message,path,channel = thing
                    user,text,time = message
                    if not channel in ROUTING or ROUTING[::-1][ROUTING.index(channel)].ID_to != -1:
                        continue
                    await self.send_message({"name":user,"time":time,"message":text,"unique_id":path,"channel":channel,"external":True})
                    self.queue.task_done()
            except exceptions.ConnectionError:
                pass
            except Exception:
                E = format_exc()
                LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(E,now()))
                print(E)
            finally:
                await self.disconnect()
    
    def start(self):
        try:
            run(self.process_queue())
        except KeyboardInterrupt:quit()


class DiscordBot(Client):
    def __init__(self, discord_queue:Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Discord"
        self.tree = app_commands.CommandTree(self)
        self.queue = discord_queue
        self.subscribers = queues.difference({self.queue})
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
        time = now()
        if (not (channel:=message.channel.id) in ROUTING):
            LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
            return
        file_path = None
        user = message.author
        user = readable_iterable((user.display_name,user.name,user.global_name),user.id)
        for attachment in message.attachments:
            file_path = path.join(MEDIA_PATH,attachment.filename)
            await attachment.save(file_path)
            LOGGER(self.name,DISCORD_LOGS_TABLE,(user,"",attachment.filename,time,channel))
            request = ((user,attachment.filename,time),file_path,channel)
            [await queue.put(request) for queue in self.subscribers]
        LOGGER(self.name,DISCORD_LOGS_TABLE,(user,message.content,"",time,channel))
        request = ((user,message.content,time),None,channel)
        [await queue.put(request) for queue in self.subscribers]
    async def check_queue_and_send(self):
        while not EXIT_FLAG.is_set():
            if self.queue.empty():
                await sleep(1)
                continue
            message,path,channel = await self.queue.get()
            user,text,msg_time = message
            channel = ROUTING[ROUTING.index(channel)].ID_to
            await self.send_file(f"{user} {msg_time}: \n  {text}",path,channel)
            self.queue.task_done()
        self.close()
bot = DiscordBot(discord_queue,intents=DISCORD_PERMISSIONS)
@bot.tree.command(
    name="list",
    description=locale("discord_list_desc"),
    guild=Object(id=DISCORD_SERVER)
)
async def list_cmd(interaction):
    files = "\n".join(FileManager.dirList(FILES_DIRECTORY))
    text = f'{locale("file_list")}\n{files}'
    await interaction.response.send_message(text)
@bot.tree.command(
    name="download",
    description=locale("discord_download_desc"),
    guild=Object(id=DISCORD_SERVER)
)
async def download_cmd(interaction,directory:str):
    time = now()
    ret_id = interaction.channel_id
    if ret_id in FILES_DISCORD_BLACKLIST:
        text = locale("file_channel_ban")
        await interaction.response.send_message(text)
        return
    dirname = directory
    if not dirname in FileManager.dirList(FILES_DIRECTORY):
        text = locale("file_not_found")
        await interaction.response.send_message(text)
        return
    await interaction.response.send_message(locale("packing"))
    zips = FileManager.filePack(dirname,DISCORD_FILE_LIMIT)
    if type(zips)==str:
        await interaction.followup.send(zips)
        LOGGER(bot.name,MISCELLANIOUS_LOGS_TABLE,(zips,time))
        buffer_clear()
        return
    zips_amount = len(zips)
    await interaction.followup.send(f"{locale('sending')}{zips_amount}")
    for i,zipfile in enumerate(zips,start=1):
        with open(zipfile,"br") as file:
            #await interaction.followup.send(f"{i}/{zips_amount}",file=File(file))
            await interaction.followup.send(file=File(file))
        remove(zipfile)
@bot.event
async def on_ready():
    _ = bot.loop.create_task(bot.check_queue_and_send())
    await bot.tree.sync(guild=Object(id=DISCORD_SERVER))
    CLI_START_FLAG.set()
Thread(target=Telegram(telegram_queue,exception_handler()).main,daemon=True,name="TELEGRAM").start() 
#Thread(target=bot.run,args=[DISCORD_TOKEN],kwargs={"log_handler":None},daemon=True,name="DISCORD").start()
print("started")
try:Site(site_queue).start()
except KeyboardInterrupt:
    EXIT_FLAG.set()
    run(bot.close())
    buffer_clear()
    quit()