import sqlite3
db = sqlite3.connect("demo.db"); c = db.cursor()
c.execute("UPDATE posts SET status='live' WHERE status='pending'")
print(f"Approved {c.rowcount} posts")
db.commit(); db.close()
