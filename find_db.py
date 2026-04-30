import os

# 检查可能的数据库位置
paths = [
    'c:\\Users\\admin\\Desktop\\jkxt\\jkxt.db',
    'c:\\Users\\admin\\Desktop\\jkxt\\backend\\jkxt.db',
]

for p in paths:
    if os.path.exists(p):
        print(f"Found: {p}")
        print(f"Size: {os.path.getsize(p)} bytes")
    else:
        print(f"Not found: {p}")
