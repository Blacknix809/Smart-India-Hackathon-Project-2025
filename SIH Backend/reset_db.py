# reset_db.py
import os, sqlite3

DB = "demo.db"
SCHEMA = "init_db.sql"

# 1) delete old DB (if exists)
if os.path.exists(DB):
    os.remove(DB)

# 2) recreate schema
sql = open(SCHEMA, "r", encoding="utf-8").read()
db = sqlite3.connect(DB)
db.executescript(sql)

# 3) seed demo data
c = db.cursor()
c.execute("""INSERT INTO counselors(name,specialty,languages,bio,cal_link,visible)
             VALUES (?,?,?,?,?,1)""",
          ("Dr. Meera Gupta","Academic stress, Sleep","English,Hindi","Short bio","https://cal.com/your-org/meera"))
c.execute("""INSERT INTO counselors(name,specialty,languages,bio,cal_link,visible)
             VALUES (?,?,?,?,?,1)""",
          ("Mr. Arjun Iyer","Exam anxiety, Procrastination","English,Tamil","Short bio","https://cal.com/your-org/arjun"))
c.execute("""INSERT INTO posts(category,body,anon,alias,status)
             VALUES (?,?,?,?, 'live')""",
          ("Exam stress","Exams are close and I’m feeling anxious",1,"Student A"))
db.commit(); db.close()
print("Database reset & demo data seeded.")
