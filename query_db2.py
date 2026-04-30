import sqlite3

conn = sqlite3.connect('c:\\Users\\admin\\Desktop\\jkxt\\jkxt.db')
cursor = conn.cursor()

# 查询所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== 数据库表 ===")
for t in tables:
    print(t[0])

# 查询设备
print("\n=== 设备列表 ===")
cursor.execute("SELECT * FROM device")
for row in cursor.fetchall():
    print(row)

conn.close()
