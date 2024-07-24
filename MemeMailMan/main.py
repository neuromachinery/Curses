from os import remove,path,listdir
from sys import argv
from discord import File,Intents,Client, Interaction, app_commands,Object
from telebot.async_telebot import AsyncTeleBot
from telebot import ExceptionHandler
from threading import Thread,Event
from asyncio import run,sleep,Queue,QueueEmpty,create_task
import time
from dotenv import load_dotenv, dotenv_values
from discord import app_commands
from discord.ext import commands




from routing import ROUTING
log_queue = Queue()
get_queue = Queue()
req_queue = Queue()

def q_get(queue):
    try:return queue.get_nowait()
    except QueueEmpty:return None
#LOGGER = print
LOGGER = lambda *args:log_queue.put_nowait(args)
getData = lambda queue=get_queue: q_get(queue)
reqData = lambda *args:req_queue.put_nowait(args)


telegram_queue = Queue()
discord_queue = Queue()

import CLI
import FileManager
import sqlite3

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
TABLE_PARAMS = ("text TEXT, date TEXT",
                "nickname TEXT, text TEXT, media TEXT, date TEXT, channel INTEGER",
                "nickname TEXT, text TEXT, media TEXT, date TEXT, channel INTEGER",
                "ID_from INTEGER, ID_to INTEGER")
TABLE_INDEXES = (("idx_text","text"),
                 ("idx_name","nickname"),
                 ("idx_name","nickname"),
                 ("","")
                 )
CONTENT_LIMIT = 5000
CONTROL_THREAD_TIMEOUT = 0.1
CLI_START_FLAG = Event()
EXIT_FLAG = Event()
exitSignal = EXIT_FLAG.set

def readable_string(string:str): 
    return all(ord(char) < 128 or (1040 <= ord(char) <= 1103) for char in string)
def readable_iterable(strings,default:str):
    return next((item for item in strings if readable_string(item)), default)
def buffer_clear():
    [remove(file) for file in listdir(FileManager.Buffer)]
def now():
    return datetime.now().strftime("[%d.%m.%Y@%H:%M:%S]")
class Channel():
    def __init__(self,From,To) -> None:
        self.ID_from = From
        self.ID_to = To
    def __eq__(self, __value: object) -> bool:
        return self.ID_from == __value
class Model():
    def __init__(self,filename,log_queue,get_queue,req_queue) -> None:
        self.db = sqlite3.connect(filename)
        self.cur = self.db.cursor()
        self.table_names = TABLES
        self.log_queue = log_queue
        self.get_queue,self.req_queue = get_queue,req_queue
        self.table_params = {k:(p,i) for (k,p,i) in zip(TABLES,TABLE_PARAMS,TABLE_INDEXES)}
        for Key,(Param,Indexes) in self.table_params.items():
            self.cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {Key}(
            id INTEGER PRIMARY KEY,
            {Param}
            )    
            """)
            if(Indexes[0]):self.cur.execute(f"CREATE INDEX IF NOT EXISTS {Indexes[0]} ON {Key} ({Indexes[1]})")
        if not self.cur.execute("SELECT ID_FROM FROM Routing").fetchall():
            from routing import ROUTING
            for route in ROUTING:
                self.cur.execute(f"INSERT INTO Routing (ID_from,ID_to) VALUES (?,?)",(route.ID_from,route.ID_to))
            self.db.commit()
    def process_queue(self,queue):
        try:
            message = queue.get_nowait()
            return message
        except QueueEmpty:
            return
        except Exception as e: 
            self.DB_log(MISCELLANIOUS_LOGS_TABLE,(str(e),now()))
    def control_thread(self):
        try:
            while not EXIT_FLAG.is_set(): 
                time.sleep(CONTROL_THREAD_TIMEOUT)
                message = self.process_queue(log_queue)
                if message:
                    self.DB_log(*message)
                    self.get_queue.put_nowait(message)
                request = self.process_queue(req_queue)
                if not request: continue
                result = self.DB_list(*request)
                self.get_queue.put_nowait(result)
                pass

        except KeyboardInterrupt:
            print(self.DB_log(MISCELLANIOUS_LOGS_TABLE,("Shutdown",now())))
            self.DB_quit()
            raise KeyboardInterrupt
    def DB_log(self,table_name:str,message):
        "Logs whatever to one of logging tables"
        params = self.table_params[table_name][0].replace(" TEXT","").replace(" INTEGER","")
        params_len = len(params.split(","))
        try:
            command = f"INSERT INTO {table_name} ({params}) VALUES ({', '.join(['?']*params_len)})",[thing if str(thing) else "<nothing>" for thing in message[:params_len]]
            self.cur.execute(*command)
        except sqlite3.OperationalError as e:
            return "; ".join([str(e),table_name,*map(str,message),command[0]])
        self.DB_commit()
        return True
    def DB_count(self,table_name:str):
        return int(self.cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    def DB_remove(self,table_name:str,id):
        "Removes certain entries from database."
        self.cur.execute(f"DELETE FROM {table_name} WHERE id={id}") 
    def DB_list(self,table_name:str,limit:int=-1,offset:int=0):
        "Returns list of all entries in database"
        return self.cur.execute(f"SELECT {self.table_params[table_name][0]} FROM {table_name} LIMIT {limit} OFFSET {offset}").fetchall()
    def DB_get_byName(self,table_name:str,name):
        "Returns entries in database by name"
        return self.cur.execute(f"SELECT FROM {table_name} WHERE nickname={name}").fetchall()
    def DB_get_byID(self,table_name:str,id):
        "Returns entries in database by ID"
        return self.cur.execute(f"SELECT FROM {table_name} WHERE id={id}").fetchall()
    def DB_edit(self,table_name:str,id,field,value):
        "Edits entries in database"
        self.cur.execute(f"UPDATE {table_name} SET {field}={value} WHERE id={id}")
    def DB_commit(self):
        self.db.commit()
    def DB_quit(self):
        self.db.commit()
        self.db.close()
class Telegram():
    def __init__(self,telegram_queue:Queue, discord_queue:Queue,exception_handler:ExceptionHandler) -> None:
        self.bot = AsyncTeleBot(TELEGRAM_TOKEN,exception_handler=exception_handler)
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
            while not EXIT_FLAG.is_set():
                if(self.discord_queue.empty()):
                    await sleep(1)
                    continue
                text,Path,channel = await self.discord_queue.get()
                if(not Path):
                    await self.bot.send_message(GROUP_ID,text=text,message_thread_id=channel)
                    self.discord_queue.task_done()
                    continue
                ext = Path.split('.')[-1].lower()
                try:
                    with open(Path,"br") as file:
                        await self.MEDIA_METHODS.get(ext,self.bot.send_document)(GROUP_ID,file,message_thread_id=channel,caption=text)
                    remove(Path)
                except Exception as E:
                    LOGGER(MISCELLANIOUS_LOGS_TABLE,(str(E),now()))
                finally:self.discord_queue.task_done()
        @self.bot.message_handler(commands=["start"])
        async def start(message):
            cmds = ";\n".join(["/"+cmd.replace('<arg>',locale('arg')) for cmd in T_COMMANDS])
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
                LOGGER(MISCELLANIOUS_LOGS_TABLE,(zips,time))
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
                LOGGER(MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
                return
            channel = ROUTING[ROUTING.index(channel)].ID_to
            text = message.text if message.text else message.caption
            text = "" if not text else text
            user = message.from_user
            user = readable_iterable((user.full_name,user.first_name,user.last_name,user.username),user.id)
            if(not (message.photo or message.video or message.sticker)):
                LOGGER(TELEGRAM_LOGS_TABLE,(user,message.text,"",time,message.message_thread_id))
                await self.telegram_queue.put((f"{user}:{text}\n{time}",None,channel))
                return
            ext = "png" if message.photo or (message.sticker and not message.sticker.is_video) else "mp4"
            media = next((var for var in (message.photo,message.video,message.sticker) if var),None) # define media by what there is in the message.
            media = media[-1] if isinstance(media,list) else media # if it's message.photo
            LOGGER(TELEGRAM_LOGS_TABLE,(user,text,media.file_unique_id,time,message.message_thread_id))
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
            LOGGER(MISCELLANIOUS_LOGS_TABLE,(f"{channel} не смотрим",time))
            return
        file_path = None
        user = message.author
        user = readable_iterable((user.display_name,user.name,user.global_name),user.id)
        for attachment in message.attachments:
            file_path = path.join(CWD,"media",attachment.filename)
            await attachment.save(file_path)
            LOGGER(DISCORD_LOGS_TABLE,(user,"",attachment.filename,time,channel))
            await self.discord_queue.put((f"{user}:{attachment.filename}",file_path,ROUTING[ROUTING.index(message.channel.id)].ID_to))
        LOGGER(DISCORD_LOGS_TABLE,(user,message.content,"",time,channel))
        await self.discord_queue.put((f"{user}:{message.content} {time}","",ROUTING[ROUTING.index(message.channel.id)].ID_to))
    async def check_queue_and_send(self):
        while not EXIT_FLAG.is_set():
            if self.telegram_queue.empty():
                await sleep(1)
                continue
            await self.send_file(*await self.telegram_queue.get())
            self.telegram_queue.task_done()
bot = DiscordBot(telegram_queue,discord_queue,intents=DISCORD_PERMISSIONS)
@bot.tree.command(
    name="list",
    description=locale("discord_list_desc"),
    guild=Object(id=DISCORD_SERVER)
)
async def list_cmd(interaction):
    files = ";\n".join(FileManager.dirList(FILES_DIRECTORY))
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
        LOGGER(MISCELLANIOUS_LOGS_TABLE,(zips,time))
        buffer_clear()
        return
    zips_amount = len(zips)
    await interaction.followup.send(f"{locale('sending')}{zips_amount}")
    for i,zipfile in enumerate(zips,start=1):
        with open(zipfile,"br") as file:
            await interaction.followup.send(f"{i}/{zips_amount}",file=File(file))
        remove(zipfile)
@bot.event
async def on_ready():
    _ = bot.loop.create_task(bot.check_queue_and_send())
    await bot.tree.sync(guild=Object(id=DISCORD_SERVER))
    CLI_START_FLAG.set()
model = Model("MMM.db",log_queue,get_queue,req_queue)
ROUTING = [Channel(*route) for route in model.DB_list("Routing")]
pages_args = [(table,"",f"0/{model.DB_count(table)}/{CONTENT_LIMIT}") for table in TABLES]
for i,table in enumerate(TABLES):
    count = model.DB_count(table)
    content = model.DB_list(table,count,count-CONTENT_LIMIT)
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
class exception_handler(ExceptionHandler):
    def handle(self,exception,*args,**kwargs):
        LOGGER(MISCELLANIOUS_LOGS_TABLE,(str(exception)+";".join(map(str,args)),now()))
        return True
Thread(target=Telegram(telegram_queue,discord_queue,exception_handler()).main,daemon=True,name="TELEGRAM").start() 
Thread(target=bot.run,args=[DISCORD_TOKEN],kwargs={"log_handler":None},daemon=True,name="DISCORD").start()
cliBot = CLI.CLIBot(reqData,getData,exitSignal)
CLI_START_FLAG.wait()
print("started")
Thread(target=cliBot.run,args=[pages_args],daemon=True,name="CLI").start()
try:model.control_thread()
except KeyboardInterrupt:
    EXIT_FLAG.set()
    buffer_clear()
    quit()