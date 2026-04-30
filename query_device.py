import sqlite3

conn = sqlite3.connect('c:\\Users\\admin\\Desktop\\jkxt\\jkxt.db')
cursor = conn.cursor()

# 查询设备表
cursor.execute("SELECT * FROM devices")
rows = cursor.fetchall()

print("=== 设备列表 ===")
for row in rows:
    print(row)

conn.close()
