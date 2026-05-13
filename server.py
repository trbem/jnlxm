"""
ESP32-CAM 视觉识别系统 - PC 端后端服务
==========================================
功能：
1. 接收 ESP32-CAM 发送的图像，调用远程 API 进行图像识别
2. 文字对话服务（知心伙伴人设）
3. 识图聊天服务（图片 + 对话上下文）
4. 人设配置管理
技术栈：FastAPI, Uvicorn, Pillow, requests
"""

import base64
import io
import json
import time
import os
import re
import sys
import traceback
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
import requests

# 设置未捕获异常处理器
def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n\n未捕获的异常:")
    logging.error("".join(traceback.format_tb(exc_traceback)))
    logging.error(f"{exc_type.__name__}: {exc_value}")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# 默认配置
DEFAULT_CONFIG = {
    "name": "知心伙伴",
    "system_prompt": """你是一个温暖、贴心的知心伙伴。你的任务是倾听用户的心声，陪伴他们度过每一天。你会：
1. 认真倾听用户的分享，给予积极的回应
2. 当用户难过时，温柔地安慰他们
3. 当用户需要鼓励时，真诚地鼓励他们
4. 适当开一些善意的玩笑，让气氛轻松愉快
5. 使用温暖、亲切的语气，经常使用emoji表达情感
6. 记住用户之前分享的事情，让对话有连续性

你的性格特点：温柔、体贴、幽默、善解人意、积极向上。""",
    "model": "qwen3.6-35b-a3b-awq",
    "max_context_rounds": 10,
    "server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "remote_api": {
        "url": "http://10.1.88.112:8000/v1",
        "image_path": "/chat/completions",
        "text_path": "/chat/completions"
    }
}

# 全局配置和对话历史
config = DEFAULT_CONFIG.copy()
conversation_history = {}  # {session_id: [messages]}

# 最大会话历史长度（每个会话最多保留多少条用户/助手消息）
MAX_HISTORY_LENGTH = 10


def load_config():
    """加载配置文件"""
    global config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            config.update(loaded_config)
            print(f"[配置] 已从 config.json 加载配置")
    except FileNotFoundError:
        print(f"[配置] 未找到 config.json，使用默认配置")
        save_config()
    except json.JSONDecodeError as e:
        print(f"[配置] config.json 格式错误: {e}，使用默认配置")
        save_config()


def save_config():
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[配置] 配置已保存到 config.json")


def get_system_message():
    """获取系统消息"""
    return {
        "role": "system",
        "content": config["system_prompt"]
    }


def get_session_history(session_id: str, max_rounds: int = None):
    """获取会话历史"""
    if max_rounds is None:
        max_rounds = config.get("max_context_rounds", 10)
    
    history = conversation_history.get(session_id, [])
    return history[-(max_rounds * 2):] if history else []


def add_to_history(session_id: str, role: str, content: str):
    """添加到会话历史"""
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    conversation_history[session_id].append({
        "role": role,
        "content": content
    })
    
    # 限制历史长度：保留 system message + 最近 MAX_HISTORY_LENGTH 轮对话
    # 每轮对话包含 user + assistant 两条消息，所以最多保留 MAX_HISTORY_LENGTH * 2 条
    max_messages = MAX_HISTORY_LENGTH * 2
    if len(conversation_history[session_id]) > max_messages:
        conversation_history[session_id] = conversation_history[session_id][-max_messages:]


def filter_response(text: str) -> str:
    """
    过滤 AI 回复，去除思考过程，只保留实际回复内容
    
    Args:
        text: API 返回的原始文本
        
    Returns:
        清理后的文本
    """
    # 查找 </think> 或 </thinking> 或 <endthink> 等标签
    tags_to_find = [
        (r'</think>', '结束标签 </think>'),
        (r'</thinking>', '结束标签 </thinking>'),
        (r'</?endthink>', '结束标签 endthink'),
        (r'</?end_of_thinking>', '结束标签 end_of_thinking'),
    ]
    
    found_end = None
    for pattern, desc in tags_to_find:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found_end = match.end()
            break
    
    # 如果找到了结束标签，取之后的内容
    if found_end:
        text = text[found_end:]
    else:
        # 没找到结束标签，尝试找到开始标记并移除之前的内容
        thinking_start_markers = [
            r"Here['\']s a thinking process:",
            r"Here['\']s the thinking process:",
            r'Analyze User Input:',
            r'Identify Constraints',
            r'Identify Key Requirements',
            r'Role/Persona Requirements:',
            r'Formulate Response',
            r'Check (?:against|Against)',
            r'Mental Refinement',
            r'Self-Correction',
            r'Mental Draft',
        ]
        
        for marker in thinking_start_markers:
            match = re.search(marker, text, re.IGNORECASE)
            if match:
                text = text[match.end():]
                break
    
    # 移除编号列表格式（如 "1.  **", "2.  **" 等）
    text = re.sub(r'^\d+\.\s+\*\*\s*', '', text, flags=re.MULTILINE)
    
    # 移除 "All criteria met" 或 "All constraints met" 等确认信息
    text = re.sub(r'(?i)(all\s+(criteria|constraints)\s+met\.?\s*(ready\s+to\s+output\.?)?\s*)', '', text)
    
    # 移除 emoji 确认标记
    text = re.sub(r'[✅📝✔️]\s*', '', text)
    
    # 移除 <thinking> 标签及其内容
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    text = re.sub(r'<thinking>', '', text, flags=re.DOTALL)
    text = re.sub(r'</thinking>', '', text)
    
    # 移除 <think> 标签及其内容
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>', '', text, flags=re.DOTALL)
    text = re.sub(r'</think>', '', text)
    
    # 清理多余的空行（3个或更多连续换行替换为2个）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 去除首尾空白
    text = text.strip()
    
    return text


def call_api(messages: list) -> str:
    """
    调用远程 OpenAI 兼容 API
    
    Args:
        messages: 消息列表
        
    Returns:
        API 返回的文本（已过滤思考过程）
    """
    api_url = config["remote_api"]["url"]
    api_key = "11111"
    model = config["model"]
    text_path = config["remote_api"].get("text_path", "/chat/completions")
    
    endpoint = f"{api_url}{text_path}"
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        # 添加 connect timeout (5秒) 和 read timeout (90秒)
        # 注意：远程 API 响应较慢，需要较长的 read timeout
        logger.info(f"正在调用 API: {endpoint}")
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=(5, 90)  # (connect_timeout, read_timeout)
        )
        
        logger.info(f"API 响应状态码: {response.status_code}")
        
        # 检查 HTTP 状态
        response.raise_for_status()
        
        # 解析 JSON 响应
        try:
            result = response.json()
        except Exception as json_err:
            logger.error(f"JSON 解析错误: {json_err}")
            logger.error(f"原始响应: {response.text[:500]}")
            raise HTTPException(status_code=502, detail=f"API 返回格式错误: {str(json_err)}")
        
        # 检查响应结构
        if "choices" not in result:
            logger.error(f"响应缺少 choices 字段: {result}")
            raise HTTPException(status_code=502, detail=f"API 响应格式错误: 缺少 choices 字段")
        
        if len(result["choices"]) == 0:
            logger.error("choices 为空")
            raise HTTPException(status_code=502, detail="API 返回空响应")
        
        choice = result["choices"][0]
        
        # 检查 error 字段
        if "error" in choice:
            error_msg = choice["error"].get("message", "未知错误")
            logger.error(f"API 错误: {error_msg}")
            raise HTTPException(status_code=502, detail=f"API 错误: {error_msg}")
        
        # 提取回复内容
        message = choice.get("message", {})
        raw_text = message.get("content", "") if isinstance(message, dict) else ""
        
        if not raw_text:
            logger.error("回复内容为空")
            raise HTTPException(status_code=502, detail="API 返回空回复")
        
        logger.info(f"原始回复长度: {len(raw_text)}")
        
        # 过滤思考过程
        filtered = filter_response(raw_text)
        logger.info(f"过滤后回复长度: {len(filtered)}")
        
        return filtered
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: 无法连接到 {api_url}")
        logger.error(f"错误详情: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接到远程 API ({api_url})，请检查网络连接或 API 服务是否运行"
        )
    
    except requests.exceptions.Timeout as e:
        logger.error(f"超时错误: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"API 调用超时，请稍后重试"
        )
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP 错误: {str(e)}")
        resp_text = response.text[:500] if 'response' in locals() else 'N/A'
        logger.error(f"响应内容: {resp_text}")
        raise HTTPException(
            status_code=502,
            detail=f"API HTTP 错误: {str(e)}"
        )
    
    except HTTPException:
        # 重新抛出已处理的 HTTPException
        raise
    
    except Exception as e:
        print(f"[API] 未知错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"API 调用失败: {type(e).__name__}: {str(e)}"
        )


def process_image_to_base64(image_bytes: bytes) -> str:
    """将 JPEG 图像转换为 Base64 编码"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        raise ValueError(f"图像处理失败: {str(e)}")


def call_image_api(image_base64: str, user_prompt: str, session_id: str) -> str:
    """调用图像识别 API（带上下文）"""
    # 获取会话历史（只返回 user/assistant 消息）
    messages = get_session_history(session_id)
    
    # 确保 system message 在最前面（OpenAI API 要求）
    messages = [get_system_message()] + messages
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ]
    })
    
    result = call_api(messages)
    add_to_history(session_id, "user", user_prompt)
    add_to_history(session_id, "assistant", result)
    return result


app = FastAPI(title="知心伙伴 - 智能对话系统")

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，防止服务器崩溃"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {type(exc).__name__}: {str(exc)}"}
    )

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载配置
load_config()


# ==================== 网页静态文件 ====================

# 创建 web 目录用于存放静态文件
import os
web_dir = os.path.join(os.path.dirname(__file__), "web")
if not os.path.exists(web_dir):
    os.makedirs(web_dir)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=web_dir), name="static")


# ==================== API 接口 ====================

@app.get("/")
async def serve_index():
    """提供主页"""
    return FileResponse(os.path.join(web_dir, "index.html"))


@app.get("/api/config", response_model=dict)
async def get_config():
    """获取配置"""
    return {
        "name": config["name"],
        "system_prompt": config["system_prompt"],
        "model": config["model"],
        "max_context_rounds": config.get("max_context_rounds", 10),
        "remote_api_url": config["remote_api"]["url"]
    }


@app.post("/api/config")
async def update_config(request: Request):
    """更新配置"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")
    
    # 更新配置
    if "name" in data:
        config["name"] = data["name"]
    if "system_prompt" in data:
        config["system_prompt"] = data["system_prompt"]
    if "model" in data:
        config["model"] = data["model"]
    if "max_context_rounds" in data:
        config["max_context_rounds"] = int(data["max_context_rounds"])
    
    # 保存到文件
    save_config()
    
    return {"status": "success", "message": "配置已更新"}


@app.post("/api/chat")
async def chat(request: Request):
    """
    文字对话接口
    
    请求体:
    {
        "message": "用户消息",
        "session_id": "会话ID（可选，不传则生成新会话）"
    }
    
    返回:
    {
        "response": "助手回复",
        "session_id": "会话ID",
        "time": 耗时
    }
    """
    start_time = time.time()
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")
    
    user_message = data.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    session_id = data.get("session_id", f"session_{int(time.time())}")
    
    # 获取会话历史（只返回 user/assistant 消息）
    messages = get_session_history(session_id)
    
    # 确保 system message 在最前面（OpenAI API 要求）
    messages = [get_system_message()] + messages
    messages.append({"role": "user", "content": user_message})
    
    # 调用 API
    response_text = call_api(messages)
    
    # 更新历史
    add_to_history(session_id, "user", user_message)
    add_to_history(session_id, "assistant", response_text)
    
    elapsed = time.time() - start_time
    
    return {
        "response": response_text,
        "session_id": session_id,
        "time": round(elapsed, 2)
    }


@app.post("/api/image_chat")
async def image_chat(request: Request):
    """
    识图聊天接口
    
    请求体:
    {
        "image": "Base64 编码的 JPEG 图像",
        "message": "用户问题（可选，默认使用提示词）",
        "session_id": "会话ID（可选）"
    }
    
    返回:
    {
        "response": "助手回复",
        "session_id": "会话ID",
        "time": 耗时
    }
    """
    start_time = time.time()
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")
    
    image_base64 = data.get("image", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="图像不能为空")
    
    user_message = data.get("message", "请描述这张图片里的内容，用中文回答，语气要温暖亲切。")
    session_id = data.get("session_id", f"session_{int(time.time())}")
    
    # 调用图像 API
    response_text = call_image_api(image_base64, user_message, session_id)
    
    elapsed = time.time() - start_time
    
    return {
        "response": response_text,
        "session_id": session_id,
        "time": round(elapsed, 2)
    }


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    接收 ESP32-CAM 上传的图像并进行识别（保留旧接口）
    """
    start_time = time.time()
    
    if file.content_type not in ["image/jpeg", "image/jpg"]:
        return {"success": False, "error": "仅支持 JPEG 格式的图像"}
    
    image_bytes = await file.read()
    
    if len(image_bytes) == 0:
        return {"success": False, "error": "图像数据为空"}
    
    try:
        image_base64 = process_image_to_base64(image_bytes)
        result_text = call_image_api(image_base64, "请简短描述这张图片里的内容。", "esp32")
        
        elapsed = time.time() - start_time
        
        return {
            "success": True,
            "result": result_text,
            "time": round(elapsed, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time": round(time.time() - start_time, 2)
        }


@app.post("/upload_raw")
async def upload_raw_image(request: Request):
    """
    接收 ESP32-CAM 直接发送的原始 JPEG 二进制数据（保留旧接口）
    """
    data = await request.body()
    start_time = time.time()
    
    if len(data) == 0:
        return {"success": False, "error": "图像数据为空"}
    
    try:
        image_base64 = process_image_to_base64(data)
        result_text = call_image_api(image_base64, "请简短描述这张图片里的内容。", "esp32")
        
        elapsed = time.time() - start_time
        
        return {
            "success": True,
            "result": result_text,
            "time": round(elapsed, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time": round(time.time() - start_time, 2)
        }


# ==================== 语音对话接口 ====================

async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    调用远程 Whisper API 进行语音识别
    
    Args:
        audio_bytes: 音频字节数据 (WAV 格式)
        
    Returns:
        识别出的文字
    """
    api_url = config["remote_api"]["url"]
    api_key = config["remote_api"].get("whisper_key", "11111")
    whisper_path = config["remote_api"].get("whisper_path", "/whisper")
    
    endpoint = f"{api_url}{whisper_path}"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        logger.info(f"正在调用语音识别 API: {endpoint}")
        
        # 发送 WAV 音频文件
        response = requests.post(
            endpoint,
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "whisper"},
            headers=headers,
            timeout=(5, 60)
        )
        
        logger.info(f"语音识别 API 响应状态码: {response.status_code}")
        response.raise_for_status()
        
        result = response.json()
        
        # 解析响应
        text = result.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=502, detail="语音识别返回空结果")
        
        logger.info(f"语音识别结果: {text}")
        return text
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: 无法连接到 {api_url}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接到语音识别 API ({api_url})"
        )
    except requests.exceptions.Timeout as e:
        logger.error(f"超时错误: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"语音识别超时，请稍后重试"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别错误: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"语音识别失败: {type(e).__name__}: {str(e)}"
        )


async def synthesize_text(text: str) -> bytes:
    """
    调用远程 TTS API 进行语音合成
    
    Args:
        text: 要合成的文字
        
    Returns:
        MP3 音频字节数据
    """
    api_url = config["remote_api"]["url"]
    api_key = config["remote_api"].get("tts_key", "11111")
    tts_path = config["remote_api"].get("tts_path", "/tts")
    
    endpoint = f"{api_url}{tts_path}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "language": "zh",
        "voice": "zh-CN-XiaoxiaoNeural"  # 中文女声
    }
    
    try:
        logger.info(f"正在调用 TTS API: {endpoint}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=(5, 30)
        )
        
        logger.info(f"TTS API 响应状态码: {response.status_code}")
        response.raise_for_status()
        
        # 返回 MP3 音频数据
        audio_bytes = response.content
        logger.info(f"TTS 音频长度: {len(audio_bytes)} 字节")
        return audio_bytes
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: 无法连接到 {api_url}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接到 TTS API ({api_url})"
        )
    except requests.exceptions.Timeout as e:
        logger.error(f"超时错误: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail=f"TTS 合成超时，请稍后重试"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 错误: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS 合成失败: {type(e).__name__}: {str(e)}"
        )


@app.post("/api/voice")
async def voice_chat(request: Request):
    """
    语音对话接口
    
    请求体:
    {
        "audio_base64": "Base64 编码的 WAV 音频",
        "session_id": "会话ID（可选）"
    }
    
    返回:
    {
        "response": "AI 回复文字",
        "audio_base64": "Base64 编码的 MP3 音频",
        "session_id": "会话ID",
        "time": 耗时
    }
    """
    start_time = time.time()
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 格式")
    
    audio_base64 = data.get("audio_base64", "")
    if not audio_base64:
        raise HTTPException(status_code=400, detail="音频不能为空")
    
    session_id = data.get("session_id", f"session_{int(time.time())}")
    
    # 解码 Base64 音频
    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"音频 Base64 解码失败: {str(e)}")
    
    # 步骤 1: 语音识别
    logger.info("开始语音识别...")
    user_text = await transcribe_audio(audio_bytes)
    
    if not user_text:
        raise HTTPException(status_code=400, detail="语音识别结果为空")
    
    logger.info(f"用户语音内容: {user_text}")
    
    # 步骤 2: 获取会话历史并调用 AI
    messages = get_session_history(session_id)
    messages = [get_system_message()] + messages
    messages.append({"role": "user", "content": user_text})
    
    response_text = call_api(messages)
    
    # 更新历史
    add_to_history(session_id, "user", user_text)
    add_to_history(session_id, "assistant", response_text)
    
    # 步骤 3: 语音合成
    logger.info("开始语音合成...")
    try:
        audio_bytes = await synthesize_text(response_text)
        response_audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        logger.warning(f"TTS 合成失败: {str(e)}，只返回文字")
        response_audio_base64 = ""
    
    elapsed = time.time() - start_time
    
    return {
        "response": response_text,
        "audio_base64": response_audio_base64,
        "session_id": session_id,
        "time": round(elapsed, 2)
    }


@app.post("/api/clear_history")
async def clear_history(request: Request):
    """清除会话历史"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if session_id and session_id in conversation_history:
            del conversation_history[session_id]
            return {"status": "success", "message": "历史已清除"}
        elif not session_id:
            conversation_history.clear()
            return {"status": "success", "message": "所有历史已清除"}
        else:
            raise HTTPException(status_code=400, detail="无效的会话ID")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除历史失败: {str(e)}")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "running",
        "service": "知心伙伴 - 智能对话系统",
        "model": config.get("model", ""),
        "config_file": CONFIG_FILE
    }


def run_server():
    """启动 FastAPI 服务器"""
    import uvicorn
    
    print("=" * 50)
    print("  知心伙伴 - 智能对话系统")
    print("=" * 50)
    print(f"  网页地址: http://localhost:{config['server']['port']}")
    print(f"  API 文档: http://localhost:{config['server']['port']}/docs")
    print(f"  模型: {config['model']}")
    print(f"  人设: {config['name']}")
    print("=" * 50)
    print()
    
    uvicorn.run(app, host=config["server"]["host"], port=config["server"]["port"], log_level="info")


if __name__ == "__main__":
    run_server()