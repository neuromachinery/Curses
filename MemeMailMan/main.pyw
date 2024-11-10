from os import remove,path,listdir
from sys import argv
from discord import File,Intents,Client, Interaction, app_commands,Object
from telebot.async_telebot import AsyncTeleBot
from telebot import ExceptionHandler
from telebot.apihelper import ApiTelegramException
from threading import Thread,Event
from asyncio import run,sleep,Queue,QueueEmpty,create_task
import time
from dotenv import load_dotenv, dotenv_values
from discord import app_commands
from discord.ext import commands


CLI_START_FLAG = Event()
EXIT_FLAG = Event()
exitSignal = EXIT_FLAG.set

PROCESS_DELAY = 0.5

from routing import ROUTING,HOSTS
log_queue = Queue()
get_queue = Queue()
req_queue = Queue()
def get_queue_f():
    try:return get_queue.get_nowait()
    except QueueEmpty:return None

import CLI
import FileManager
from DBconnect import SocketTransiever

DB_Transiever = SocketTransiever(target=HOSTS["MMM"])
DB_Transiever.connect()
LOGGER = lambda *args:log_queue.put_nowait(args)
getData = get_queue_f
reqData = lambda *args:req_queue.put_nowait(args)
def process_queues():
    while not EXIT_FLAG.is_set():
        run(sleep(PROCESS_DELAY))
        try:
            data = log_queue.get_nowait()
            print(data)
            DB_Transiever.send_message(DB_Transiever.target_sock,data[0],"LOG",data[1:])
        except QueueEmpty:pass

        try:
            data = req_queue.get_nowait()
            print(data)
            DB_Transiever.send_message(DB_Transiever.target_sock,data[0],"LST",data[1:])
            get_queue.put_nowait(DB_Transiever.receive_message(DB_Transiever.target_sock))
        except QueueEmpty:pass


telegram_queue = Queue()
discord_queue = Queue()

from datetime import datetime

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

FILES_DIRECTORY = FileManager.SharedDirectory
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
        LOGGER("Main",MISCELLANIOUS_LOGS_TABLE,(str(exception)+";".join(map(str,args)),now()))
        return True
class Telegram():
    def __init__(self,telegram_queue:Queue, discord_queue:Queue,exception_handler:ExceptionHandler) -> None:
        self.name = "Telegram"
        self.bot = AsyncTeleBot(TELEGRAM_TOKEN,exception_handler=exception_handler)
        self.telegram_queue = telegram_queue
        self.discord_queue = discord_queue
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
        async def queue_monitor(self):
            while not EXIT_FLAG.is_set():
                if(self.discord_queue.empty()):
                    await sleep(1)
                    continue
                text,Path,channel = await self.discord_queue.get()
                keyword_args = {"chat_id":GROUP_ID,"message_thread_id":channel} if type(channel)==int else {"chat_id":channel}
                if(not Path):
                    await self.bot.send_message(**keyword_args,text=text)
                    self.discord_queue.task_done()
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
                finally:self.discord_queue.task_done()
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
        @self.bot.message_handler(content_types=["text","sticker","photo","video","gif"])
        async def messages(message):
            time = now()
            if(not (channel:=message.message_thread_id) in ROUTING):
                LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
                return
            channel = ROUTING[ROUTING.index(channel)].ID_to
            text = message.text if message.text else message.caption
            text = "" if not text else text
            user = message.from_user
            user = readable_iterable((user.full_name,user.first_name,user.last_name,user.username),user.id)
            if(not (message.photo or message.video or message.sticker)):
                LOGGER(self.name,TELEGRAM_LOGS_TABLE,(user,message.text,"",time,message.message_thread_id))
                await self.telegram_queue.put((f"{user}:{text}\n{time}",None,channel))
                return
            ext = "png" if message.photo or (message.sticker and not message.sticker.is_video) else "mp4"
            media = next((var for var in (message.photo,message.video,message.sticker) if var),None) # define media by what there is in the message.
            media = media[-1] if isinstance(media,list) else media # if it's message.photo
            LOGGER(self.name,TELEGRAM_LOGS_TABLE,(user,text,media.file_unique_id,time,message.message_thread_id))
            Path = path.join(CWD,"media",f"{media.file_unique_id}.{ext}")
            with open(Path,"wb") as pic:
                file = await self.bot.get_file(media.file_id)
                pic.write(await self.bot.download_file(file.file_path))
            await self.telegram_queue.put((f"{user}:{text}\n{time}",Path,channel))
        _ = create_task(queue_monitor(self))
        await self.bot.polling() 
    def main(self): 
        while not EXIT_FLAG.is_set():
            try:
                run(self.bot_thread())
            except Exception as E:
                LOGGER(MISCELLANIOUS_LOGS_TABLE,(str(E),now()))
                EXIT_FLAG.set()
class DiscordBot(Client):
    def __init__(self, telegram_queue:Queue, discord_queue:Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Discord"
        self.tree = app_commands.CommandTree(self)
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
        time = now()
        if (not (channel:=message.channel.id) in ROUTING):
            LOGGER(self.name,MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
            return
        file_path = None
        user = message.author
        user = readable_iterable((user.display_name,user.name,user.global_name),user.id)
        for attachment in message.attachments:
            file_path = path.join(CWD,"media",attachment.filename)
            await attachment.save(file_path)
            LOGGER(self.name,DISCORD_LOGS_TABLE,(user,"",attachment.filename,time,channel))
            await self.discord_queue.put((f"{user}:{attachment.filename}",file_path,ROUTING[ROUTING.index(message.channel.id)].ID_to))
        LOGGER(self.name,DISCORD_LOGS_TABLE,(user,message.content,"",time,channel))
        await self.discord_queue.put((f"{user}:{message.content} {time}","",ROUTING[ROUTING.index(message.channel.id)].ID_to))
    async def check_queue_and_send(self):
        while not EXIT_FLAG.is_set():
            if self.telegram_queue.empty():
                await sleep(1)
                continue
            await self.send_file(*await self.telegram_queue.get())
            self.telegram_queue.task_done()
        self.close()
bot = DiscordBot(telegram_queue,discord_queue,intents=DISCORD_PERMISSIONS)
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
def startCLI():
    cliBot = CLI.CLIBot(reqData,getData,exitSignal)
    pages_args = []
    table_counts = []
    for i,table in enumerate(TABLES):
        DB_Transiever.send_message(DB_Transiever.target_sock,"Main","CNT",(table,))
        table_counts.append(DB_Transiever.receive_message(DB_Transiever.target_sock)["message"])
        pages_args.append((table,"",f"0/{table_counts[i]}/{CONTENT_LIMIT}"))
    for i,table in enumerate(TABLES):
        count = table_counts[i]
        DB_Transiever.send_message(DB_Transiever.target_sock,"Main","LST",(table,count,count-CONTENT_LIMIT))
        content = DB_Transiever.receive_message(DB_Transiever.target_sock)["message"]
        if not content:
            pages_args[i] = (table,"No content",pages_args[i][2])
            continue
        content.reverse()
        if type(content[0])==tuple:
            content = [" | ".join(map(str,entry)) for entry in content]
        try:
            pages_args[i] = [table,"\n".join(content),f"{str(len(content))}/{count}/{CONTENT_LIMIT}"]
        except TypeError as e:
            print(str(e))
            print(content)
    CLI_START_FLAG.wait()
    Thread(target=cliBot.run,args=[pages_args],daemon=True,name="CLI").start()

Thread(target=Telegram(telegram_queue,discord_queue,exception_handler()).main,daemon=True,name="TELEGRAM").start() 
Thread(target=bot.run,args=[DISCORD_TOKEN],kwargs={"log_handler":None},daemon=True,name="DISCORD").start()
#startCLI()
print("started")
try:process_queues()
except KeyboardInterrupt:
    EXIT_FLAG.set()
    run(bot.close())
    buffer_clear()
    quit()