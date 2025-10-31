import sqlite3
db = sqlite3.connect("demo.db"); c = db.cursor()
# counselors
c.execute("""INSERT INTO counselors(name,specialty,languages,bio,cal_link,visible)
             VALUES (?,?,?,?,?,1)""",
          ("Dr. Meera Gupta","Academic stress, Sleep","English,Hindi","Short bio","https://cal.com/your-org/meera"))
c.execute("""INSERT INTO counselors(name,specialty,languages,bio,cal_link,visible)
             VALUES (?,?,?,?,?,1)""",
          ("Mr. Arjun Iyer","Exam anxiety, Procrastination","English,Tamil","Short bio","https://cal.com/your-org/arjun"))
# one live community post
c.execute("""INSERT INTO posts(category,body,anon,alias,status)
             VALUES (?,?,?,?, 'live')""",
          ("Exam stress","Exams are close and I’m feeling anxious",1,"Student A"))
db.commit(); db.close()
print("Seeded counselors + one live post ✔")
