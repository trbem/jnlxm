import os
import sys
import subprocess

# 设置环境变量
os.environ['IDF_PATH'] = r'D:\app\Espressif\frameworks\esp-idf-v5.4.3'
os.environ['IDF_PYTHON_ENV_PATH'] = r'D:\app\Espressif\python_env\idf5.4_py3.14_env'
os.environ['PATH'] = (
    r'D:\app\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin;' +
    r'D:\app\Espressif\tools\cmake\3.30.2\bin;' +
    r'D:\app\Espressif\tools\ninja\1.12.1;' +
    r'D:\app\Espressif\python_env\idf5.4_py3.14_env\Scripts;' +
    os.environ.get('PATH', '')
)
os.environ['CC'] = r'D:\app\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin\xtensa-esp32s3-elf-gcc.exe'
os.environ['CXX'] = r'D:\app\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin\xtensa-esp32s3-elf-g++.exe'
os.environ['IDF_MAINTAINER'] = '1'  # 允许使用不同版本的工具链

# 切换到固件目录
os.chdir(r'c:\Users\admin\Desktop\jkxt\firmware')

# 命令行参数
action = sys.argv[1] if len(sys.argv) > 1 else 'build'
port = sys.argv[2] if len(sys.argv) > 2 else 'COM6'

# 调用idf.py
idf_py = os.path.join(os.environ['IDF_PATH'], 'tools', 'idf.py')

if action == 'flash':
    result = subprocess.run([sys.executable, idf_py, '-p', port, 'flash'], env=os.environ)
else:
    result = subprocess.run([sys.executable, idf_py, 'build'], env=os.environ)

sys.exit(result.returncode)
