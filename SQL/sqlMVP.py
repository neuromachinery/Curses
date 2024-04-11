import sqlite3
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
        self.methods = [getattr(self,func) for func in dir(self) if callable(getattr(self, func)) and not func.startswith("__")]
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_name ON Players (nickname)")
    def DB_add(self):
        #"Adds new entries to database."
        properties = list(input("Enter (name,money,location_id) to add:\n"))
        self.cur.execute("INSERT INTO Players (nickname,money,location_id) VALUES (?,?,?)",(properties[0],properties[1],properties[2]))
    def DB_remove(self):
        #"Removes certain entries from database."
        id = int(input("Enter id to remove:\n"))
        self.cur.execute(f"DELETE FROM Players WHERE id={id}") 
    def DB_list(self):
        #"Returns list of all entries in database"
        return self.cur.execute("SELECT COUNT(*) FROM Players")
    def DB_get_byName(self):
        #"Returns entries in database by name"
        name = input("Enter name to get:\n")
        return self.cur.execute(f"SELECT FROM Players WHERE nickname={name}")
    def DB_get_byID(self):
        #"Returns entries in database by ID"
        id = int(input("Enter name to get:\n"))
        return self.cur.execute(f"SELECT FROM Players WHERE id={id}")
    def DB_edit(self):
        #"Edits entries in database"
        properties = list(input("Enter (id,field,value) to edit:\n"))
        self.cur.execute(f"UPDATE Players SET {properties[1]}={properties[2]} WHERE id={properties[0]}")
    def DB_quit(self):
        self.db.commit()
        self.db.close()
class Presenter:
    def __init__(self,Model,View) -> None:
        self.model = Model
        self.view = View
        self.methods = [getattr(self,func) for func in dir(self) if callable(getattr(self, func)) and not func.startswith("__")]
        self.hotkeys = zip(("a","r","l","n","i","e","q"),self.methods)
    def execute(self,command:str) -> str:
        if(command in self.hotkeys):return self.hotkeys[command]()
    def quit(self):
        self.model.DB_quit()
        quit()
class View:
    def __init__(self) -> None:
        self.presenter = Presenter(Model("PlayersDB.db"),self)
        self.main()
    def main(self):
        try:
            print(self.presenter.execute(input()))
        except KeyboardInterrupt:
            self.presenter.quit()
if __name__ == "__main__":
    View()