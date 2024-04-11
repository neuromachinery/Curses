import sqlite3
import curses
import json
from os import access,F_OK
from os.path import join,realpath,dirname
CWD = realpath(dirname(__name__))
SETTINGS_FILENAME = "config.json"
def JSONLoad(filename,cwd=CWD):	
    path = join(cwd,filename)
    try:
        access(path, F_OK)
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except:
        return False
def JSONSave(data,filename,cwd=CWD):
    with open(join(cwd,filename), "w", encoding="UTF-8") as f: 
        json.dump(data,f)   
def Print(str, i, scrn):
    scrn.move(i,1)
    scrn.clrtoeol()
    scrn.box()
    scrn.addstr(i,1,str)
    scrn.refresh()
def AttrCheck(scrn,pos,attribute):
    return scrn.inch(pos[0], pos[1])&0xFFFF0000 == attribute
def GetKeyByValue(dict,value): return list(dict.keys())[list(dict.values()).index(value)]
def FindFunc(name,list): # find index of function in a list by a function name
    return [func.__name__ for func in list].index(name)

def ManualSetup(scrn,filename=SETTINGS_FILENAME):
        curses.echo()
        settings = {"COMMANDS":{},"COLORS":[]}
        def clearln():
            y,_ = scrn.getyx()
            scrn.move(y-1 if(y!=0) else y,0)
            scrn.clrtoeol()
            scrn.move(y-1 if(y!=0) else y,0)
        scrn.addstr("Default command hotkeys? (Y/N) ")
        scrn.refresh()
        if(scrn.getkey().upper()=="N"):
            clearln()
            for i, command in enumerate(COMMANDS):
                scrn.addstr(f"character hotkey for {command.__name__}: ")
                scrn.refresh()
                key = scrn.getkey()
                y,_ = scrn.getyx()
                scrn.move(y,0)
                scrn.clrtoeol()
                settings["COMMANDS"][key] = i
                scrn.addstr(f"{key} -> {command.__name__}\n")
        else:
            settings["COMMANDS"]={"Q": 0, "S": 1, "W": 2, "A": 3}
        settings["COLORS"] = [
            [curses.COLOR_RED,curses.COLOR_BLACK],
            [curses.COLOR_YELLOW,curses.COLOR_BLACK],
            [curses.COLOR_GREEN,curses.COLOR_BLACK],
            [curses.COLOR_BLUE,curses.COLOR_BLACK],
            [curses.COLOR_MAGENTA,curses.COLOR_BLACK],
            [curses.COLOR_RED,curses.COLOR_WHITE],
            [curses.COLOR_YELLOW,curses.COLOR_WHITE],
            [curses.COLOR_GREEN,curses.COLOR_WHITE],
            [curses.COLOR_BLUE,curses.COLOR_WHITE],
            [curses.COLOR_MAGENTA,curses.COLOR_WHITE],
            [curses.COLOR_BLACK,curses.COLOR_RED],
            [curses.COLOR_WHITE,curses.COLOR_RED],
            [curses.COLOR_BLACK,curses.COLOR_YELLOW],
            [curses.COLOR_WHITE,curses.COLOR_YELLOW],
            [curses.COLOR_BLACK,curses.COLOR_BLACK],
            [curses.COLOR_WHITE,curses.COLOR_WHITE],
        ]
        JSONSave(settings,filename)
        scrn.erase()
        return settings

class Model():
    def __init__(self,filename) -> None:
        self.db = sqlite3.connect(filename)
        self.cur = self.db.cursor()
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS Players(
        id INTEGER PRIMARY KEY,
        nickname TEXT NOT NULL,
        money INTEGER,
        location_id INTEGER                                                                
        )    
        """)
        self.methods = [FindFunc(func) for func in dir(self) if callable(getattr(self, func)) and not func.startswith("__")]
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_name ON Players (nickname)")
    def DB_add(cur,properties):
        "Adds new entries to database."
        for property in properties:
            cur.execute("INSERT INTO Players (nickname,money,location_id) VALUES (?,?,?)",(property[0],property[1],property[2]))
    def DB_remove(cur,id):
        "Removes certain entries from database."
        cur.execute(f"DELETE FROM Players WHERE id={id}") 
    def DB_list(cur):
        "Returns list of all entries in database"
        return cur.execute("SELECT COUNT(*) FROM Players")
    def DB_get_byName(cur,name):
        "Returns entries in database by name"
        return cur.execute(f"SELECT FROM Players WHERE nickname={name}")
    def DB_get_byID(cur,id):
        "Returns entries in database by ID"
        return cur.execute(f"SELECT FROM Players WHERE id={id}")
    def DB_edit(cur,id,field,value):
        "Edits entries in database"
        cur.execute(f"UPDATE Players SET {field}={value} WHERE id={id}")
class Presenter():
    def __init__(self,model:Model) -> None:
        self.model = model
        self.methods = [FindFunc(func) for func in dir(self) if callable(getattr(self, func)) and not func.startswith("__")]
    def Database(setting)

class View():
    def __init__(self,stdscr) -> None:
        self.stdscr = stdscr
        Y,X = stdscr.getmaxyx()
        curses.start_color()
        curses.cbreak()
        curses.curs_set(0)
        self.SETTINGS = JSONLoad(SETTINGS_FILENAME)
        if not self.SETTINGS:
            stdscr.addstr("!SETTINGS FILE NOT FOUND! Create new file? (Y/N)",curses.color_pair(1))
            if(stdscr.getkey().upper() == "Y"):
                stdscr.move(0,0)
                stdscr.clrtoeol()
                self.SETTINGS = ManualSetup(stdscr)
            else:
                quit()
        self.DEFAULT_NEWWIN = [round(Y*0.9),round(X*0.5),round(Y*0.1),round(X*0.1)]
        for i,color in enumerate(self.SETTINGS["COLORS"],start=1):
            curses.init_pair(i,*color)

        self.presenter = Presenter(Model("PlayerDB.db"))
    def Quit():
        "Quit program"
        quit() #because "quit" doesn't have __name__ and __doc__ attribute
    def CommandSetup(self):
        "Re-assign command hotkeys"
        scrn = curses.newwin(*self.DEFAULT_NEWWIN)
        scrn.clear()
        scrn.box()
        scrn.addstr(1,1,"This window lets edit command hotkeys. Continue? (Y/any)",curses.color_pair(2))
        scrn.refresh()
        if(scrn.getkey()!="Y"):return
        self.settings["COMMANDS"] = {}
        for i, command in enumerate(COMMANDS):
            scrn.addstr(1,1,f"character hotkey for {command.__name__}: ")
            scrn.refresh()
            key = scrn.getkey()
            y,_ = scrn.getyx()
            scrn.move(y,1)
            scrn.clrtoeol()
            scrn.box()
            self.settings["COMMANDS"][key] = i
            scrn.addstr(i+2,1,f"{key} -> {command.__name__}\n")
        JSONSave(self.settings,SETTINGS_FILENAME)
    def WindowSettings(self):
        "Settings for GUI."
        COLORS = [
            [curses.COLOR_BLACK,"Black"],
            [curses.COLOR_BLUE,"Blue"],
            [curses.COLOR_CYAN,"Cyan (light greenish blue)"],
            [curses.COLOR_GREEN,"Green"],
            [curses.COLOR_MAGENTA,"Magenta (purplish red)"],
            [curses.COLOR_RED,"Red"],
            [curses.COLOR_WHITE,"White"],
            [curses.COLOR_YELLOW,"Yellow"]
        ]
        curses.echo()
        newscrn = curses.newwin(*DEFAULT_NEWWIN)
        newscrn.clear()
        newscrn.box()
        newscrn.addstr(1,1,"Settings for coloring windows. This one included.",curses.color_pair(2))
        newscrn.addstr(2,2,"Continue? (Y/any)",curses.color_pair(4))
        newscrn.refresh()
        if(newscrn.getkey()!="Y"):return

        if(curses.has_colors()==False):
            newscrn.clear()
            newscrn.box()
            newscrn.addstr(1,1,"This terminal unfortunatly does not support colors. *sadface*",curses.color_pair(1))
            curses.napms(3000)
            return
        def ColorPick(i):
            try:
                preset = self.settings["COLORS"][i].copy()
                yxpos = list(map(lambda x:round(x*0.9),DEFAULT_NEWWIN))
                colscr = curses.newwin(*yxpos)
                colscr.clear()
                colscr.box()
                colscr.addstr(1,1,"Pick foreground color. Q to exit")
                for y,colorPair in enumerate(COLORS[:len(COLORS)//2]):
                    curses.init_pair(255-y,colorPair[0],curses.COLOR_BLACK)
                    colscr.addstr(y+2,2,f"({y+1}) ##COLOR## {colorPair[1]}",curses.color_pair(255-y))
                for y,colorPair in enumerate(COLORS[len(COLORS)//2:]):
                    curses.init_pair(251-y,colorPair[0],curses.COLOR_BLACK)
                    colscr.addstr(y+2,50,f"({y+5}) ##COLOR## {colorPair[1]}",curses.color_pair(251-y))
                colscr.refresh()
                key = colscr.getkey()
                if(key=="Q"):raise KeyboardInterrupt
                preset[0] = COLORS[int(key)-1][0]
                colscr.move(1,1)
                colscr.clrtoeol()
                colscr.box()
                colscr.addstr(1,1,"Pick background color.")
                for y,colorPair in enumerate(COLORS[:len(COLORS)//2]):
                    curses.init_pair(255-y,colorPair[0],curses.COLOR_BLACK)
                    colscr.addstr(y+2,2,f"({y+1}) ##COLOR## {colorPair[1]}",curses.color_pair(255-y))
                for y,colorPair in enumerate(COLORS[len(COLORS)//2:]):
                    curses.init_pair(251-y,colorPair[0],curses.COLOR_BLACK)
                    colscr.addstr(y+2,50,f"({y+5}) ##COLOR## {colorPair[1]}",curses.color_pair(251-y))
                colscr.refresh()
                key = colscr.getkey()
                if(key=="Q"):raise KeyboardInterrupt
                preset[1] = COLORS[int(key)-1][0]
                try:curses.init_pair(i,preset[0],preset[1])
                except curses.error:
                    from random import randint
                    colscr.clear()
                    colscr.box()
                    colscr.addstr(1,1,"Congratulations! You've found THE SECRET! :)")
                    for i in range(30):
                        for x in range(44):
                            colscr.chgat(1,x+1,curses.color_pair(randint(1,16)))
                            colscr.refresh()
                        curses.napms(1500)
                    quit()
                return preset
            except IndexError:
                return False
        while True:
            newscrn.move(1,1)
            newscrn.clrtoeol()
            newscrn.box()
            newscrn.addstr(1,1,"Settings for coloring windows. This one included.",curses.color_pair(2))
            newscrn.addstr(2,1,"     Choose which preset to edit for entire application.(Type 'done' to exit)",curses.color_pair(3))
            for x in [0,1]:
                for y in range(1,8):
                    newscrn.addstr(y+3,(x*30)+2,f"({y+x*9}) ! COLORFUL TEXT \\0/ !",curses.color_pair(y+x*9))
            newscrn.refresh()
            newscrn.move(2,1)
            while True:
                input = newscrn.getstr().decode("utf-8")
                if(input.upper()=="DONE"):return
                result = ColorPick(int(input))
                if(result):break
            newscrn.clear()
            newscrn.box()
            newscrn.addstr(1,1,f"This is your customized preset №{input}. Save it? (Y/any)",curses.color_pair(int(input)))
            newscrn.refresh()
            try:key = newscrn.getkey()
            except KeyboardInterrupt:return
            if(key == "Y"):
                self.settings["COLORS"][int(input)] = [result[0],result[1]]
                JSONSave(self.settings,SETTINGS_FILENAME)
            else:
                curses.init_pair(int(input),self.settings["COLORS"][int(input)-1][0],self.settings["COLORS"][int(input)-1][1])
                newscrn.clear()
    def Help(self):
        "Display help menu"
        newscrn = curses.newwin(*DEFAULT_NEWWIN)
        newscrn.clear()
        newscrn.box()
        newscrn.addstr(1,1,"All hotkeys for commands. Press Q to go back.",curses.color_pair(5))
        for key,value in self.settings["COMMANDS"].items():
            commandKey = list(COMMANDS.keys())[value]
            newscrn.addstr(value+2,2,f"'{key}' -> {commandKey.__name__}. '{COMMANDS[commandKey][0]}'.",curses.color_pair(0))
        while True: 
            if(newscrn.getkey()=="Q"):return

    def main(self):
        stdscr = self.stdscr
        stdscr.clear()
        stdscr.addstr(f" DB Control by NeuroDevil. Press {self.presenter.methods[-1]} for help. Press {self.presenter.methods[0]} to exit.",curses.color_pair(4))
        while True:
            stdscr.refresh()
            stdscr.move(0,0)
            try: 
                key = stdscr.getkey()
                stdscr.move(0,0)
                try:
                    i = int(self.settings["COMMANDS"][key])
                    commandKey = list(COMMANDS.keys())[i] # key is function object
                    try:commandKey(*COMMANDS[commandKey][1])
                    except KeyboardInterrupt:pass
                    curses.noecho()
                    stdscr.move(0,0)
                    stdscr.touchwin()
                    stdscr.refresh()
                except KeyError:
                    pass
            except KeyboardInterrupt:
                quit()
if __name__ == "__main__":
    try:curses.wrapper(View)
    except KeyboardInterrupt:pass

