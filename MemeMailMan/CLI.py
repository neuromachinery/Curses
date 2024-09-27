import curses
from numpy import array
from time import sleep
TIMEOUT = 1
class Page():
    def __init__(self,scr,dims,pos,utf=True,top_row="",content="",bottom_row=""):
        self.scr = scr
        self.dims = dims
        self.pos = pos
        self.utf = utf
        self.content = content
        self.display_content = self.preprocess(content)
        self.content_positions = array((0,0))
        self.top_row = top_row[:self.dims[1]].replace("\n"," ")
        self.bottom_row = bottom_row[:self.dims[1]].replace("\n"," ")
    def preprocess(self,text):
        res = []
        lines = text.splitlines()
        while lines:
            line = lines.pop(0)
            words = line.split()
            current_line = ""
            while words:
                word = words.pop(0)
                if len(current_line + word) <= self.dims[1]:
                    current_line += word + " "
                else:
                    res.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                res.append(current_line.strip())
        res = [line.ljust(self.dims[1]) for line in res]
        return "".join(res)
    def __repr__(self):
        return self.top_row
    def __eq__(self, __value: object) -> bool:
        return self.top_row==__value
    def __hash__(self) -> int:
        return hash(self.top_row) 
    def filler(self,text) -> str:
        try:return (text if type(text)==str else text.decode("UTF-8"))+(" "*(self.dims[1]+1-len(text)))
        except UnicodeDecodeError:
            print(text,type(text))
            return ""
    def draw(self):
        self.scr.addstr(self.pos[0],self.pos[1],self.filler(self.top_row))
        lines = [self.display_content[self.dims[1]*i:self.dims[1]*(i+1)] for i in range(len(self.display_content)//self.dims[1])]
        self.content_positions[1] = 0
        try:
            for i,y in enumerate(range(self.pos[0]+1,self.dims[0])):
                self.content_positions[1]+=len(lines[i])
                self.scr.addstr(y,self.pos[1],lines[i])
        except IndexError:pass
        self.scr.addstr(self.dims[0],self.pos[1],self.filler(self.bottom_row))
    def clear(self):
        #self.content_positions = np.array((0,0))
        #self.content=""
        #self.display_content=self.filler("")
        for y in range(self.pos[0],self.dims[0]+1):
            self.scr.addstr(y,self.pos[1]," "*self.dims[1])
    def change_top(self,text:str,draw:bool=True):
        self.top_row = text
        text = text[:self.dims[1]]
        if draw: 
            self.scr.addstr(self.pos[0],self.pos[1],self.filler(text))
    def change_bottom(self,text:str,draw:bool=True):
        self.bottom_row = text
        text = text[:self.dims[1]]
        if draw: 
            self.scr.addstr(self.dims[0],self.pos[1],self.filler(text))
    def change_content(self,content:str,draw:bool=True):
        self.content = content
        self.display_content = self.preprocess(content)
        if draw: 
            self.draw()
    def scroll_content(self,up:bool):
        win = self.scr
        change = self.dims[1]
        char_lim = self.dims[1]*2 if self.utf else self.dims[1]
        if up:
            if(self.content_positions[1]>=len(self.display_content)):
                #return True
                return
            for row in range(self.pos[0]+1,self.dims[0]-1):
                win.move(row,self.pos[1])
                line = win.instr(row+1,self.pos[1],char_lim)
                win.addstr(row,self.pos[1],self.filler(line))
            Slice = slice(self.content_positions[1],self.content_positions[1]+self.dims[1])
            win.move(self.dims[0]-1,self.pos[1])
        else:
            if(self.content_positions[0]<=0):
                return 
            for row in range(self.dims[0]-1,self.pos[0]+1,-1):
                win.move(row,self.pos[1])
                line = win.instr(row-1,self.pos[1],char_lim)
                win.addstr(row,self.pos[1],self.filler(line))
            win.move(self.pos[0]+1,self.pos[1])
            change = change*-1
            Slice = slice(self.content_positions[0]-self.dims[1],self.content_positions[0])
        content = self.display_content[Slice]
        win.addstr(self.filler(content))
        self.content_positions = self.content_positions + change
        #if np.any(self.content_positions<0):self.content_positions = np.array((0,self.dims[1]+self.dims[0]+3))

        win.move(*self.pos)
class CLIBot():
    def __init__(self,db_req_f,db_get_f,db_exit_f):
        self.name = "CLI"
        self.db_req_f,self.db_get_f = db_req_f,db_get_f
        self.db_exit_f = db_exit_f
        self.statusbar_func = lambda iter:"| [{}] " * (len(iter)) + " |"
        self.content_numbers = {}
        self.currentPage = 0
        self.status_pos = (2,2)
        self.BGch = "#"
    def run(self,pages_args):
        for i,args in enumerate(pages_args):
            count = int(args[2].split("/")[0])
            self.content_numbers[i]=count
        try:curses.wrapper(self.main,pages_args)
        except KeyboardInterrupt:quit()
    def main(self,scr,pages_args):
        self.scr = scr
        self.dims = array((curses.LINES,curses.COLS))
        self.pages = [Page(scr,self.dims-(2,4),(3,2),True,*args) for args in pages_args]
        self.page_lim = len(pages_args)
        scr.addstr(0,0,self.statusbar_func(self.pages).format(*self.pages))
        for x in (0,self.dims[1]-1):
            for y in range(1,self.dims[0]-1):
                scr.addstr(y,x,self.BGch)
        for y in (1,self.dims[0]-1):
            for x in range(self.dims[1]-1):
                scr.addstr(y,x,self.BGch)

        self.pages[self.currentPage].draw()
        self.scr.chgat(0,3,len(str(self.pages[self.currentPage])),curses.A_STANDOUT)
        while(True):
            try:
                self.status("awaiting key")
                key = scr.getch()
            except KeyboardInterrupt:quit()
            self.FunMap = { 
                456:lambda:self.pages[self.currentPage].scroll_content(up=True),
                258:lambda:self.pages[self.currentPage].scroll_content(up=True),
                450:lambda:self.pages[self.currentPage].scroll_content(up=False),
                259:lambda:self.pages[self.currentPage].scroll_content(up=False),
                452:lambda:self.changePage(right=False),
                260:lambda:self.changePage(right=False),
                454:lambda:self.changePage(right=True),
                261:lambda:self.changePage(right=True),
                113:self.db_exit_f,
                114:self.update,
                109:self.mute,

                1081:self.db_exit_f,
                1082:self.update,
                1100:self.mute
            }
            if(key in self.FunMap.keys()): 
                try:
                    res = self.FunMap[key]()
                except NotImplementedError:
                    self.status("not implemented. Yet.")
                    sleep(TIMEOUT)
                    continue
                if(res == None):
                    scr.refresh()
                    continue
                tableData=pages_args[self.currentPage]
                tableName = tableData[0]
                currentCount = self.content_numbers[self.currentPage]
                max_count = int(tableData[2].split("/")[1])
                if currentCount>=max_count:continue
                batch_size = int(tableData[2].split("/")[2])
                offset = max_count-(currentCount+batch_size)
                if (currentCount+offset>max_count or offset<currentCount):
                    offset = max_count-currentCount
                self.db_req_f(self.name,tableName,max_count,offset)
                self.status("waiting database")
                db_content = None
                while True:
                    db_content = self.db_get_f()
                    if db_content == []:
                        db_content = None
                        break
                    if db_content == None:
                        continue
                    format_string = "{} @ {}" if len(db_content[0])==2 else "{}:{} ({}) @{} in {}"
                    db_content = [format_string.format(*message) for message in db_content]
                    change = len(db_content)
                    db_content = "\n".join(db_content)
                    break
                if db_content == None:
                    continue
                
                page = self.pages[self.currentPage]
                pg_content = page.content
                if res:
                    content = "\n".join((db_content, pg_content))
                else:
                    content = "\n".join((pg_content, db_content))
                self.status("changing content")
                page.change_content(content)
                page_bottom_row = page.bottom_row.split("/")
                page.change_bottom("/".join((str(int(page_bottom_row[0]) + change),*page_bottom_row[1:])))
                self.content_numbers[self.currentPage] = currentCount + change
            else:
                self.status(" -> ".join(("wrong key",str(key))))
                sleep(TIMEOUT)
            scr.refresh()
            #sleep(TIMEOUT)
    def status(self,status:str):
        self.scr.addstr(*self.status_pos,status.ljust(self.dims[1]-2))
        self.scr.refresh()
    def changePage(self,right):
        change = 1 if right else -1
        previousPage = self.currentPage
        self.currentPage = self.currentPage + change
        currentPage = self.currentPage
        if currentPage<0:
            self.currentPage=0
            return
        if currentPage>=self.page_lim:
            self.currentPage=self.page_lim-1
            return
        self.pages[currentPage-change].clear()
        self.pages[currentPage].draw()
        #map(lambda page,mode:self.scr.chgat(0,3+(5*page)+sum([len(str(pagename)) for pagename in self.pages[:page]]),len(str(self.pages[page])),mode),((previousPage,curses.A_NORMAL),(currentPage,curses.A_STANDOUT)))
        self.scr.chgat(0,3+(5*previousPage)+sum([len(str(pagename)) for pagename in self.pages[:previousPage]]),len(str(self.pages[previousPage])),curses.A_NORMAL)
        self.scr.chgat(0,3+(5*currentPage)+sum([len(str(pagename)) for pagename in self.pages[:currentPage]]),len(str(self.pages[currentPage])),curses.A_STANDOUT)
    def update(self):
        update_screen = False
        self.status("getting updates.")
        while True:
            db_content = self.db_get_f()
            if db_content:
                table = db_content[0]
                try: page_index = self.pages.index(table)
                except ValueError:continue
                page = self.pages[page_index]
                if not update_screen and page_index==self.currentPage:
                    update_screen = True
                format_string = " | ".join([str(entry) if entry else "<nothing>" for entry in db_content[1]])
                page.change_content(f"{format_string}\n{page.content}",draw=False)
            else:
                break
        if update_screen:
            self.status("updating screen")
            page = self.pages[self.currentPage]
            page.clear()
            page.draw()
        self.status("update finished")
        sleep(TIMEOUT)
    def mute(self):
        raise NotImplementedError
if __name__ == "__main__":
    #pages = [(f"TOP {i}","",f"BOTTOM {i}") for i in range(3)]
    #for i,filename in enumerate(("lorem.txt","rus.txt","en.txt")):
    #    with open(filename,"r",encoding="UTF-8") as file:pages[i] = pages[i][0],file.read(),pages[i][2]
    #    #print(pages[i][0])
    ##print(pages[0][0])
    #CLIBot(pages,None)
    print("no")