import sqlite3

conn = sqlite3.connect('c:\\Users\\admin\\Desktop\\jkxt\\backend\\src\\jkxt.db')
cursor = conn.cursor()

# 查询所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== Database Tables ===")
for t in tables:
    print(t[0])

# 查询设备
print("\n=== Devices ===")
cursor.execute("SELECT * FROM devices")
for row in cursor.fetchall():
    print(row)

conn.close()
