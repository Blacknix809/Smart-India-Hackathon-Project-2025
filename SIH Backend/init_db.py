import sqlite3

db = sqlite3.connect("demo.db")
db.executescript(open("init_db.sql","r",encoding="utf-8").read())
db.commit()
db.close()
print("demo.db created ✔")
