# ESP32-CAM 智能家庭助手系统

一个基于 ESP32-S3-Eye 硬件和大语言模型的智能家庭助手系统，支持语音交互、图像识别和多模态对话。

## 🌟 功能特性

### 💬 智能对话
- 温暖贴心的"知心伙伴"人设
- 支持上下文连续对话
- 可自定义人设和系统提示词
- 支持多种大语言模型（Qwen3.6-35B 等）

### 📷 图像识别
- ESP32-CAM 拍摄照片并上传
- 基于 AI 的图像内容理解和描述
- 支持看图聊天功能

### 🎤 语音对话
- PDM 麦克风语音录制
- Whisper 语音识别
- TTS 语音合成回复
- 完整的语音交互闭环

### 📺 LCD 显示
- ST7789 LCD 实时状态显示
- 多状态界面切换（待机、录音、思考、结果）
- 中文文字显示支持

## 🛠️ 技术栈

### 后端服务
| 技术 | 说明 |
|------|------|
| FastAPI | 高性能 Web 框架 |
| Uvicorn | ASGI 服务器 |
| Pillow | 图像处理 |
| requests | HTTP 客户端 |

### 硬件平台
| 组件 | 规格 |
|------|------|
| 芯片 | ESP32-S3 |
| 开发框架 | ESP-IDF v5.4+ |
| 摄像头 | OV2640 |
| LCD | ST7789 (160x80) |
| 麦克风 | PDM (I2S接口) |

### AI 服务
| 服务 | 说明 |
|------|------|
| 语言模型 | Qwen3.6-35B-A3B-AWQ |
| 语音识别 | Whisper |
| 语音合成 | Edge TTS (zh-CN-XiaoxiaoNeural) |

## 📁 项目结构

```
jnjxm/
├── server.py                 # PC 端后端服务（FastAPI）
├── config.json               # 配置文件
├── README.md                 # 项目说明文档
├── .gitignore                # Git 忽略文件配置
├── docs/
│   └── firmware_requirements.md  # ESP32 固件需求文档
├── web/
│   └── index.html            # 前端网页界面
└── house_price_model/        # 房价预测模型（可选）
    ├── clean_dataset.py
    ├── predict_test.py
    └── train_model.py
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn pillow requests
```

### 2. 配置文件

编辑 `config.json`：

```json
{
  "name": "知心伙伴",
  "system_prompt": "你的系统提示词...",
  "model": "Qwen3.6-35B-A3B-AWQ",
  "server": {
    "host": "0.0.0.0",
    "port": 8082
  },
  "remote_api": {
    "url": "http://your-api-server:8000/v1",
    "image_path": "/chat/completions",
    "text_path": "/chat/completions"
  }
}
```

### 3. 启动服务

```bash
python server.py
```

服务启动后访问：
- **网页界面**: http://localhost:8082
- **API 文档**: http://localhost:8082/docs

## 📡 API 接口说明

### 文字对话

```
POST /api/chat
Content-Type: application/json

{
  "message": "你好，今天天气怎么样？",
  "session_id": "device_001"
}
```

响应：
```json
{
  "response": "今天是晴天，气温25度，很适合出门呢！😊",
  "session_id": "device_001",
  "time": 3.5
}
```

### 识图聊天

```
POST /api/image_chat
Content-Type: application/json

{
  "image": "base64编码的JPEG图像",
  "message": "请描述这张图片",
  "session_id": "device_001"
}
```

### 语音对话

```
POST /api/voice
Content-Type: application/json

{
  "audio_base64": "base64编码的WAV音频",
  "session_id": "device_001"
}
```

响应：
```json
{
  "response": "文字回复内容",
  "audio_base64": "base64编码的MP3音频",
  "session_id": "device_001",
  "time": 5.2
}
```

### 配置管理

```
GET /api/config          # 获取配置
POST /api/config         # 更新配置
POST /api/clear_history  # 清除对话历史
GET /api/health          # 健康检查
```

### ESP32 上传接口

```
POST /upload             # 接收上传的图像文件
POST /upload_raw         # 接收原始JPEG数据
```

## 🔧 ESP32 固件开发

### 引脚配置

| 组件 | 引脚 |
|------|------|
| PDM 麦克风 | GPIO47 (WS), GPIO45 (BCLK) |
| LCD (ST7789) | GPIO07 (MOSI), GPIO06 (SCLK), GPIO05 (CS), GPIO05 (DC), GPIO48 (RST), GPIO38 (BL) |
| 摄像头 (OV2640) | GPIO01-41 (详见固件文档) |
| 按键 | GPIO0 (BOOT - 长按录音) |
| LED | GPIO1 (状态指示) |

### 按键操作

| 操作 | 功能 |
|------|------|
| 长按 (>1秒) | 开始录音，释放停止并发送 |
| 双击 | 触发拍照 |

### 状态界面

- **待机**: 显示 Wi-Fi 状态和 IP 地址
- **录音中**: 音频波形动画
- **思考中**: 旋转加载动画
- **显示结果**: AI 回复文字

详细固件需求请参考 [`docs/firmware_requirements.md`](docs/firmware_requirements.md)。

## 📝 配置说明

### 人设配置

在 `config.json` 中修改：

- `name`: 助手名称
- `system_prompt`: 系统提示词（定义 AI 性格和行为）
- `model`: 使用的模型名称
- `max_context_rounds`: 对话上下文轮数

### 服务器配置

- `server.host`: 监听地址（默认 0.0.0.0）
- `server.port`: 监听端口（默认 8082）

### API 服务配置

- `remote_api.url`: 远程 AI 服务地址
- `remote_api.image_path`: 图像识别 API 路径
- `remote_api.text_path`: 文字对话 API 路径

## ⚠️ 注意事项

1. **敏感信息**: `config.json` 包含服务器地址等敏感信息，请勿公开分享
2. **网络要求**: 需要能够访问远程 AI API 服务
3. **硬件要求**: ESP32-S3-Eye 开发板需要正确的 ESP-IDF 环境编译固件

## 📄 许可证

本项目仅供学习和研究使用。