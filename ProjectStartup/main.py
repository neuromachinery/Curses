import os
import json
from os.path import join
import curses
CWD = os.path.realpath(os.path.dirname(__name__))
SETTINGS_FILENAME = "config.ini"
def JSONLoad(filename,cwd=CWD):	
    path = join(cwd,filename)
    try:
        os.access(path, os.F_OK)
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
def ManualSetup(scrn,settings={"COMBINATIONS":{},"COMMANDS":{},"GROUPS":{}},filename=SETTINGS_FILENAME):
    curses.echo()
    scrn.addstr("Type in characters, filenames and paths:\nWhen you are done setting up, type in 'done'\n")
    def clearln():
        y,_ = scrn.getyx()
        scrn.move(y-1 if(y!=0) else y,0)
        scrn.clrtoeol()
    def input(Str):
        scrn.addstr(Str)
        Str = scrn.getstr()
        Str = Str.decode("utf-8")
        clearln()
        if(Str.upper()=="DONE"): raise StopIteration
        return Str
    while True:
        try:character,path,name = input("character hotkey: "),input("path to executable: "),input("short name for executable: ")
        except KeyboardInterrupt:quit()
        except StopIteration:break
        settings["COMBINATIONS"][character] = [path,name]
        scrn.addstr(f"{character} -> '{name}' @ {path}\n")
    scrn.erase()
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
        settings["COMMANDS"]={"Q": 0, "E": 1, "R": 2, "W": 3, "F": 4, "S": 5, "D": 6, "~": 7, "V": 8, "A": 9}
    settings["GROUPS"] = {}
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
def AddHotkey(stdscr, settings): #test
    newscrn = curses.newwin(*DEFAULT_NEWWIN)
    newscrn.clear()
    newscrn.box()
    newscrn.addstr(1,1,"This window lets add new hotkeys. Continue? (Y/any)",curses.color_pair(2))
    if(newscrn.getkey()!="Y"):return
    newscrn.addstr(1,1,"Adding hotkeys.",curses.color_pair(2))
    i = 2
    while True:
        curses.noecho()
        newscrn.addstr(i,1,"Press hotkey (CTRL+S to quit):",curses.color_pair(3))
        newscrn.refresh()
        key = newscrn.getkey()
        if(key in RESTRICTED_KEYS):continue
        if(key=="\u0013"):break
        curses.echo()
        Print("Type in path:",i,newscrn)
        path = newscrn.getstr().decode("utf-8")
        Print("Type in short name:",i,newscrn)
        name = newscrn.getstr().decode("utf-8")
        Print(f"{key} -> '{name}' @ {path}",i,newscrn)
        settings["COMBINATIONS"][key] = [path,name]
        i+=1
        if(i>round(Y*0.7)):i=2
    JSONSave(settings,SETTINGS_FILENAME)
    stdscr.clear()
    stdscr.touchwin()
    stdscr.refresh()
    stdscr.addstr(f" Choose which programs to run. Hotkey help @ {list(settings['COMMANDS'].keys())[-1]}. CTRL+C to kill program (may throw errors).")
    for key,value in settings["COMBINATIONS"].items(): 
        stdscr.addstr(f"\n({key}) {value[1]}",curses.A_NORMAL)
    stdscr.refresh()
def AttrCheck(scrn,pos,attribute):
    return scrn.inch(pos[0], pos[1])&0xFFFF0000 == attribute
def GetKeyByValue(dict,value): return list(dict.keys())[list(dict.values()).index(value)]
def FindFunc(name,list): # find index of function in a list by a function name
    return [func.__name__ for func in list].index(name)
def Quit():
    quit()
def Run(highlighted,settings):
    programs = [settings["COMBINATIONS"][key][0] for key in highlighted]
    for program in programs:
        os.system(f"'{program}'")
    quit()
def DelHighlight(stdscr,highlight,settings):
    for key in highlight.copy():
        del settings["COMBINATIONS"][key]
        highlight.remove(key)
    JSONSave(settings,SETTINGS_FILENAME)
    stdscr.clear()
    stdscr.addstr(f" Choose which programs to run. Hotkey help @ {list(settings['COMMANDS'].keys())[-1]}. CTRL+C to kill program (may throw errors).")
    for key,value in settings["COMBINATIONS"].items(): 
        stdscr.addstr(f"\n({key}) {value[1]}",curses.A_NORMAL)
def CommandSetup(settings):
    scrn = curses.newwin(*DEFAULT_NEWWIN)
    scrn.clear()
    scrn.box()
    scrn.addstr(1,1,"This window lets edit command hotkeys. Continue? (Y/any)",curses.color_pair(2))
    scrn.refresh()
    if(scrn.getkey()!="Y"):return
    settings["COMMANDS"] = {}
    for i, command in enumerate(COMMANDS):
        scrn.addstr(1,1,f"character hotkey for {command.__name__}: ")
        scrn.refresh()
        key = scrn.getkey()
        y,_ = scrn.getyx()
        scrn.move(y,1)
        scrn.clrtoeol()
        scrn.box()
        settings["COMMANDS"][key] = i
        scrn.addstr(i+2,1,f"{key} -> {command.__name__}\n")
    JSONSave(settings,SETTINGS_FILENAME)
def ClearHighlight(scrn,highlighted,settings):
    keys = highlighted.copy()
    for key in keys:
        scrn.chgat(list(settings["COMBINATIONS"].keys()).index(key)+1,1,1,curses.A_NORMAL)
        highlighted.remove(key)      
def SaveGroup(highlighted,settings):
    newscrn = curses.newwin(*DEFAULT_NEWWIN)
    curses.echo()
    newscrn.clear()
    newscrn.box()
    newscrn.addstr(1,1,"This window is for saving selections in groups for later. Continue? (Y/any)",curses.color_pair(2))
    if(newscrn.getkey()!="Y"):return
    newscrn.addstr(1,1,"Type in group save slot: ",curses.color_pair(3))
    newscrn.refresh()
    key = newscrn.getstr().decode("utf-8")
    newscrn.addstr(1,1,f"Save {len(highlighted)} items to slot {key}? (Y/N){' '*10}",curses.color_pair(3))
    newscrn.refresh()
    if(newscrn.getkey().upper()=="Y"):
        settings["GROUPS"][key] = highlighted
        JSONSave(settings,SETTINGS_FILENAME)
def LoadGroup(scrn,settings,highlighted):
    newscrn = curses.newwin(*DEFAULT_NEWWIN)
    curses.echo()
    newscrn.clear()
    newscrn.box()
    newscrn.addstr(1,1,"This window is for loading previous groups of selections. Continue? (Y/any)",curses.color_pair(2))
    if(newscrn.getkey()!="Y"):return
    newscrn.addstr(1,1,"Saved groups: ",curses.color_pair(3))
    for i,groupKey in enumerate(settings["GROUPS"]):
        newscrn.addstr(i+2,2,groupKey,curses.color_pair(4))
    newscrn.addstr(len(settings["GROUPS"])+2,2,"Type in group save slot:",curses.color_pair(3))
    newscrn.refresh()
    group_key = newscrn.getstr().decode("utf-8")
    
    try: settings["GROUPS"][group_key]
    except KeyError:
        newscrn.addstr(len(settings["GROUPS"])+2,2,"Error, wrong slot.             ",curses.color_pair(1))
        newscrn.box()
        newscrn.refresh()
        curses.napms(1500)
        return
    finally:
        scrn.touchwin()
        scrn.refresh()
    ClearHighlight(scrn,highlighted,settings)
    for key in settings["GROUPS"][group_key]:
        scrn.chgat(list(settings["COMBINATIONS"].keys()).index(key)+1,1,1,curses.A_STANDOUT)
        highlighted.append(key)
    scrn.refresh()
def Help(settings):
    newscrn = curses.newwin(*DEFAULT_NEWWIN)
    newscrn.clear()
    newscrn.box()
    newscrn.addstr(1,1,"All hotkeys for commands. Press Q to go back.",curses.color_pair(5))
    for key,value in settings["COMMANDS"].items():
        commandKey = list(COMMANDS.keys())[value]
        newscrn.addstr(value+2,2,f"'{key}' -> {commandKey.__name__}. '{COMMANDS[commandKey][0]}'.",curses.color_pair(0))
    while True: 
        if(newscrn.getkey()=="Q"):return
def WindowSettings(settings):
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
            preset = settings["COLORS"][i].copy()
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
            settings["COLORS"][int(input)] = [result[0],result[1]]
            JSONSave(settings,SETTINGS_FILENAME)
        else:
            curses.init_pair(int(input),settings["COLORS"][int(input)-1][0],settings["COLORS"][int(input)-1][1])
            newscrn.clear()
def main(stdscr):
    global Y,X,DEFAULT_NEWWIN,COMMANDS,RESTRICTED_KEYS
    Y,X = stdscr.getmaxyx()
    curses.start_color()
    curses.cbreak()
    curses.curs_set(0)
    Highlighted = []
    SETTINGS = JSONLoad(SETTINGS_FILENAME)
    if not SETTINGS:
        stdscr.addstr("!SETTINGS FILE NOT FOUND! Create new file? (Y/N)",curses.color_pair(1))
        if(stdscr.getkey().upper() == "Y"):
            stdscr.move(0,0)
            stdscr.clrtoeol()
            SETTINGS = ManualSetup(stdscr)
        else:
            quit()
    RESTRICTED_KEYS = set(SETTINGS["COMMANDS"].keys())
    RESTRICTED_KEYS.update(SETTINGS["COMBINATIONS"].keys())
    DEFAULT_NEWWIN = [round(Y*0.9),round(X*0.5),round(Y*0.1),round(X*0.1)]
    COMMANDS = {
        Quit:["Quit program",[]],
        AddHotkey:[
            "Add new hotkeys to set",
            [stdscr,SETTINGS]
        ],
        Run:[
            "Run all highlighted programs",
            [Highlighted,SETTINGS]
        ],
        ClearHighlight:[
            "Clear selection",
            [stdscr,Highlighted,SETTINGS]
        ],
        DelHighlight:[
            "Delete highlighted programs from set (NOT files)",
            [stdscr,Highlighted,SETTINGS]
        ],
        SaveGroup:[
            "Save selected programs to a group",
            [Highlighted,SETTINGS]
        ],
        LoadGroup:[
            "Load saved group to selection",
            [stdscr,SETTINGS,Highlighted]
        ],
        CommandSetup:[
            "Re-assign command hotkeys",
            [SETTINGS]
        ],
        WindowSettings:[
            "Settings for size, position, and colors of windows.",
            [SETTINGS]
        ],
        Help:[
            "Display this menu",
            [SETTINGS]
        ]
        }
    for i,color in enumerate(SETTINGS["COLORS"],start=1):
        curses.init_pair(i,*color)
    stdscr.clear()
    stdscr.addstr(f" Choose which programs to run. Hotkey help @ {list(SETTINGS['COMMANDS'].keys())[-1]}. CTRL+C to kill program (may throw errors).",curses.color_pair(4))
    for key,value in SETTINGS["COMBINATIONS"].items(): 
        stdscr.addstr(f"\n({key}) {value[1]}",curses.A_NORMAL)
    while True:
        stdscr.refresh()
        stdscr.move(0,0)
        try: 
            key = stdscr.getkey()
            y,x = list(SETTINGS["COMBINATIONS"].keys()).index(key)+1, 1
            if bool(AttrCheck(stdscr,[y,x],curses.A_NORMAL)):
                stdscr.chgat(y,x,1,curses.A_STANDOUT)
                Highlighted.append(key)
            else:
                stdscr.chgat(y,x,1,curses.A_NORMAL)
                Highlighted.remove(key)
            stdscr.move(0,0)
        except ValueError:
            try:
                i = int(SETTINGS["COMMANDS"][key])
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
    try:curses.wrapper(main)
    except KeyboardInterrupt:pass
