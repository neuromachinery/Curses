import numpy as np
import curses
from time import sleep
from datetime import datetime
from random import choice

class Piece():
    def __init__(self,pos,level,team) -> None:
        self.pos=pos
        self.map=level
        self.team=team
        self.team_char = "B" if team == "black" else "W"
        self.highlighted = False
        self.queen = False
        self.debug_output = level.debug
 
    def Move(self,pos):
        check = self.Check_move(pos)
        if(not check):return False
        check = self.map.matrix.shape[0]-1 if (self.team=="black") else 1
        if(pos[0] == check):
            self.queen = True
        self.map.Change(self.pos,pos)
        self.pos = pos
        self.map.Highlight(self)
        self.map.Render()
        return True
    def Check_move(self,target):
        target,me = np.array(target),np.array(self.pos)
        diff = me-target
        dist = np.sum(abs(diff))
        if(target[0]==0):
            return False # top line is reserved
        if(np.any(target>=self.map.matrix.shape) or np.any(target<0)):
            return False # no out-of-bounds
        if((abs(diff)).ptp()!=0):
            return False # diagonals only
        if(self.map.Get_by_coord(tuple(target))): 
            return False # not to step on pieces
        if(dist==2):
            return True
        if(dist==4):
            enemy = self.map.Get_by_coord(tuple(me-(me-target)//2))
            #self.debug_output(f"{me}->{target};{enemy.team if enemy else 'None'}/{self.team}@{enemy.pos if enemy else tuple(me-(me-target)//2)}")
            if(not enemy or enemy.team == self.team): return False
            enemy.Die()
            return True
        if(self.queen):
            direction = diff//abs(diff)
            for i in range(1,diff[0]):
                enemy = self.map.Get_by_coord(tuple(me+(direction+i)))
                if(enemy and enemy.team!=self.team):enemy.Die()
            return True
        return False
    def Die(self):
        self.map.Sub(self.pos)
        self.map.pieces[self.team].remove(self)
class CursorHandler():
    def __init__(self,screen,Map,team) -> None:
        self.screen = screen
        self.keybinds = {
            "KEY_A2":np.array((-1,0)),
            "KEY_C2":np.array((1,0)),
            "KEY_B1":np.array((0,-1)),
            "KEY_B3":np.array((0,1)),
            "KEY_UP":np.array((-1,0)),
            "KEY_DOWN":np.array((1,0)),
            "KEY_LEFT":np.array((0,-1)),
            "KEY_RIGHT":np.array((0,1)),
 
            " ":"select",
            "\n":"move"
        }
        self.map = Map
        self.team = team
        self.selected = None
    def Input(self):
        key = str(self.screen.getkey())
        if(key=="q"):
            quit()
        try:bind = self.keybinds[key]
        except KeyError:return None
        if(len(bind)==2):
            self.Move(bind)
            return None
        if(bind == "select"):
            self.Select(self.screen.getyx())
        if(bind == "move" and self.selected):
            pos = self.screen.getyx()
            if(self.selected.Move(pos)):
                self.screen.move(*pos)
                return pos
            return None
    def Select(self,pos):
        self.selected = self.map.Get_by_coord(pos,self.team)
        self.map.Highlight(self.selected)
    def Move(self,coord):
        pos = np.array(self.screen.getyx())+coord
        if(np.any(pos<0)or np.any(pos>=self.map.matrix.shape)):return
        self.screen.move(*pos)
        self.screen.refresh()
class Level():
    def debug(self,*args):
        pos = self.screen.getyx()
        self.screen.addstr(self.matrix.shape[0]+1,0,str(args)+" "*10)
        self.screen.move(*pos)
    def __init__(self,screen,mat,bgchar) -> None:
        self.screen = screen
        self.matrix = mat
        self.bgchar = bgchar
        self.pieces = {
            "black":[],
            "white":[]
        }
        for sign in [1,-1]:
            team = "black" if sign==1 else "white"
            for i in [0,1]:
                for j in range(0,self.matrix.shape[1]-1,2):
                    piece = Piece((i+1,j+i),self,team) if sign==1 else Piece((self.matrix.shape[0]-(i+1),j+i),self,team)
                    self.matrix[sign*(i+1)][j+i] = piece.team_char
                    self.pieces[team].append(piece)
 
    def Render(self):
        #self.screen.clear()
        for i,row in enumerate(self.matrix[1:],1):
            self.screen.addstr(i,0,"".join(row))
        for piece in self.pieces["black"]+self.pieces["white"]:
            self.screen.addstr(*piece.pos,piece.team_char)
        self.screen.refresh()
    def Highlight(self,Piece:Piece):
        if not Piece: return
        for piece in self.pieces["black"]+self.pieces["white"]:
            if piece.highlighted and piece != Piece:
                self.screen.chgat(*piece.pos,1,curses.A_NORMAL)
                piece.highlighted = False
        Piece.highlighted = not Piece.highlighted
        self.screen.chgat(*Piece.pos,1,curses.A_STANDOUT if Piece.highlighted else curses.A_NORMAL)
        self.screen.refresh()
    def GameOver(self,result):
        self.screen.clear()
        self.screen.addstr(0,0,result)
        self.screen.refresh()
        sleep(3)
        quit()
    def Change(self,coordFrom, coordTo):
        self.matrix[coordFrom],self.matrix[coordTo] = self.matrix[coordTo],self.matrix[coordFrom]
    def Add(self,coord,char):
        self.matrix[coord] = char
    def Sub(self,coord):
        self.matrix[coord] = self.bgchar
    def Get_by_coord(self,coord:tuple,team=None):
        pieces = self.pieces[team] if team else self.pieces["black"]+self.pieces["white"]
        for piece in pieces:
            if piece.pos == coord: return piece
        return None
class AI():
    def __init__(self,team,level) -> None:
        self.team = team
        self.level = level
        self.turn_counter = 0
        valid_vectors = np.array([[1,1],[1,-1]] if self.team=="black" else [[-1,1],[-1,-1]])
        self.valid_vectors = np.append(valid_vectors,np.array([[1,1],[1,-1],[-1,1],[-1,-1]])*2,0)
        self.min = min(self.level.matrix.shape) 
    def Think(self):
        #if(not len(self.level.pieces["black"])):self.level.GameOver(f"White won!" )
        #if(not len(self.level.pieces["white"])):self.level.GameOver(f"Black won!")
        #self.level.debug(self.valid_vectors)
        if(not len(self.level.pieces["black"])):return ["white",self.turn_counter,len(self.level.pieces["white"])]
        if(not len(self.level.pieces["white"])):return ["black",self.turn_counter,len(self.level.pieces["black"])]
        while True:
            piece = choice(self.level.pieces[self.team])
            if(piece.queen):
                queen_vec = np.copy(self.valid_vectors)
                for i in range(2,self.min-1):
                    queen_vec = np.append(queen_vec,np.array([[1,1],[1,-1],[-1,1],[-1,-1]])*i,0)
                valid_vectors = queen_vec
            else:
                valid_vectors = self.valid_vectors
            move = np.array(piece.pos)+choice(valid_vectors)
            if(piece.Move(tuple(move))):
                self.turn_counter +=1
                return 
        
def main(scr,size,team=None,game_number=1):
    time1 = datetime.now()
    scr.clear()
    Map = np.full(size," ")
    topRow = "#### move. Game #{}; turns:"
    #Map[0] = list(topRow.format(game_number)+" "*(size[1]-len(topRow)+1))[:size[1]+1]
    scr.addstr(0,0,topRow.format(game_number))
    Map = Level(scr,Map," ")
    Map.Render()    
    #cursor = CursorHandler(scr,Map,team)
    team = "black" if team == "white" else "white"
    #ai = AI(team,Map)
    aiW = AI("white",Map)
    aiB = AI("black",Map)
    pos = scr.getyx()
    pos = Map.matrix.shape[0]-1,Map.matrix.shape[1]//2
    while True:
        sleep(0.1)
        #scr.addstr(0,0,"Your")
        scr.addstr(0,0,"AI.W")
        scr.refresh()
        scr.move(*pos)
        if(result := aiW.Think()):return result+[str(datetime.now()-time1)]
        #while True:
        #    if pos := cursor.Input():break
        scr.addstr(0,0,"AI.B")
        scr.refresh()
        if(result := aiB.Think()):return result+[str(datetime.now()-time1)]
        scr.addstr(0,len(topRow)+len(str(game_number))+1-len(str(aiW.turn_counter)),str(aiW.turn_counter))
        scr.move(*pos)

if __name__ == "__main__":
    try:
        strings = ["Winner: ","Moves: ","Survivors: ","Time: "]
        List = [curses.wrapper(main,(10,10),i) for i in range(10)]
        for i,game in enumerate(List,1):
            print(f"Game #{i}:")
            for i,res in enumerate(game):
                print(strings[i],res)
            print("\n")
    except KeyboardInterrupt:quit()