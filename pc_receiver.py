#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC端语音识别服务器
功能：
1. 接收ESP32发送的音频数据 (HTTP POST to /voice)
2. 语音转文字 (使用百度语音识别或本地Whisper)
3. 提供Web界面显示识别结果和发送回复
4. 回复通过ESP32的HTTP服务器发送
"""

import http.server
import socketserver
import json
import threading
import urllib.request
import urllib.error
import io
from datetime import datetime

# 配置
VOICE_PORT = 8087
ESP32_HTTP_URL = "http://10.1.41.140:8087/api/reply"  # ESP32的HTTP服务器地址 (端口8087)
WEB_PORT = 8087

# 音频缓冲区
audio_buffer = bytearray()
buffer_lock = threading.Lock()
is_recording = False

# 识别结果
last_text = ""
text_lock = threading.Lock()

# HTML网页
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 语音识别</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            text-align: center;
            max-width: 600px;
            width: 100%;
        }
        .title {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ccc;
            margin-right: 8px;
            transition: background 0.3s;
        }
        .status.active {
            background: #4caf50;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .recognition {
            margin: 30px 0;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 10px;
            min-height: 80px;
        }
        .recognition-label {
            font-size: 14px;
            color: #999;
            margin-bottom: 10px;
        }
        .recognition-text {
            font-size: 18px;
            color: #333;
            word-wrap: break-word;
        }
        .reply-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .reply-input {
            width: 100%;
            padding: 12px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        .reply-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .reply-btn:hover {
            background: #5a6fd6;
        }
        .controls {
            margin: 20px 0;
        }
        .record-btn {
            background: #ff5252;
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 16px;
            border-radius: 30px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .record-btn.recording {
            background: #4caf50;
            animation: pulse 1.5s infinite;
        }
        .log {
            margin-top: 20px;
            padding: 15px;
            background: #1e1e1e;
            color: #d4d4d4;
            border-radius: 10px;
            text-align: left;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
            max-height: 200px;
        }
        .log-entry {
            margin: 5px 0;
        }
        .log-time {
            color: #858585;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="title"><span class="status" id="status"></span>ESP32 语音识别</div>
        
        <div class="controls">
            <button class="record-btn" id="record-btn" onclick="toggleRecording()">
                开始录音
            </button>
        </div>
        
        <div class="recognition">
            <div class="recognition-label">识别结果:</div>
            <div class="recognition-text" id="recognition-text">等待语音输入...</div>
        </div>
        
        <div class="reply-section">
            <div class="recognition-label">回复到ESP32:</div>
            <input type="text" class="reply-input" id="reply-input" placeholder="输入回复文字...">
            <button class="reply-btn" onclick="sendReply()">发送回复</button>
        </div>
        
        <div class="log" id="log">
            <div class="log-entry">
                <span class="log-time">[系统]</span> 服务器已启动
            </div>
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let audioContext = null;
        let mediaRecorder = null;
        let audioChunks = [];
        
        function addLog(message) {
            const log = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }
        
        function updateStatus(active) {
            const status = document.getElementById('status');
            if (active) {
                status.classList.add('active');
            } else {
                status.classList.remove('active');
            }
        }
        
        async function toggleRecording() {
            const btn = document.getElementById('record-btn');
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioContext = new AudioContext();
                    const source = audioContext.createMediaStreamSource(stream);
                    const analyser = audioContext.createAnalyser();
                    analyser.fftSize = 2048;
                    source.connect(analyser);
                    
                    // 使用Web Audio API进行实时语音识别
                    addLog('麦克风已启动，开始监听...');
                    updateStatus(true);
                    btn.textContent = '停止录音';
                    btn.classList.add('recording');
                    isRecording = true;
                    
                    // 简单的音频检测，检测到声音后发送
                    const data = new Uint8Array(analyser.frequencyBinCount);
                    let soundDetected = false;
                    let soundBuffer = [];
                    
                    function detectSound() {
                        if (!isRecording) return;
                        
                        analyser.getByteFrequencyData(data);
                        const average = Array.from(data).reduce((a, b) => a + b, 0) / data.length;
                        
                        if (average > 30) {
                            soundDetected = true;
                        }
                        
                        if (soundDetected) {
                            soundBuffer.push(...Array.from(data));
                        }
                        
                        requestAnimationFrame(detectSound);
                    }
                    detectSound();
                    
                } catch (err) {
                    addLog('麦克风访问失败: ' + err.message);
                }
            } else {
                addLog('录音已停止');
                updateStatus(false);
                btn.textContent = '开始录音';
                btn.classList.remove('recording');
                isRecording = false;
            }
        }
        
        async function sendReply() {
            const input = document.getElementById('reply-input');
            const text = input.value.trim();
            if (!text) return;
            
            try {
                const req = new XMLHttpRequest();
                req.open('POST', '/api/reply');
                req.setRequestHeader('Content-Type', 'text/plain');
                req.onload = function() {
                    if (req.status === 200) {
                        addLog('回复已发送: ' + text);
                        input.value = '';
                    }
                };
                req.send(text);
            } catch (err) {
                addLog('发送失败: ' + err.message);
            }
        }
        
        // 定期更新识别结果
        setInterval(async () => {
            try {
                const resp = await fetch('/api/recognition');
                const data = await resp.text();
                if (data && data !== lastDisplayedText) {
                    document.getElementById('recognition-text').textContent = data;
                    lastDisplayedText = data;
                }
            } catch (e) {}
        }, 1000);
        
        let lastDisplayedText = '';
    </script>
</body>
</html>
"""


class VoiceRecognitionHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/api/recognition':
            # 返回最新识别结果
            with text_lock:
                text = last_text
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(text.encode('utf-8'))
        else:
            super().do_GET()
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/voice':
            # 接收音频数据
            content_length = int(self.headers['Content-Length'])
            audio_data = self.rfile.read(content_length)
            
            with buffer_lock:
                audio_buffer.extend(audio_data)
            
            # 进行语音识别
            self.process_audio(audio_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        
        elif self.path == '/api/reply':
            # 接收文字回复
            content_length = int(self.headers['Content-Length'])
            reply_text = self.rfile.read(content_length).decode('utf-8')
            
            # 发送回复到ESP32
            self.send_reply_to_esp32(reply_text)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'OK: {reply_text}'.encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def process_audio(self, audio_data):
        """处理音频数据 - 语音识别"""
        # 这里可以实现实际的语音识别逻辑
        # 目前只是模拟，实际使用时需要接入语音识别API
        
        # 方案1: 使用百度语音识别
        # self.baidu_speech_recognition(audio_data)
        
        # 方案2: 使用Whisper本地识别
        # self.whisper_speech_recognition(audio_data)
        
        # 方案3: 使用Azure Speech SDK
        # self.azure_speech_recognition(audio_data)
        
        # 模拟识别结果
        pass
    
    def send_reply_to_esp32(self, reply_text):
        """发送回复到ESP32"""
        try:
            req = urllib.request.Request(
                ESP32_HTTP_URL,
                data=reply_text.encode('utf-8'),
                headers={'Content-Type': 'text/plain'},
                method='POST'
            )
            response = urllib.request.urlopen(req, timeout=5)
            response.read()
            print(f"[{datetime.now()}] 回复已发送到ESP32: {reply_text}")
        except Exception as e:
            print(f"[{datetime.now()}] 发送到ESP32失败: {e}")


def run_server():
    """运行HTTP服务器"""
    with socketserver.TCPServer(("", VOICE_PORT), VoiceRecognitionHandler) as httpd:
        print(f"=" * 50)
        print(f"ESP32 语音识别服务器已启动")
        print(f"监听端口: {VOICE_PORT}")
        print(f"ESP32 HTTP地址: {ESP32_HTTP_URL}")
        print(f"访问地址: http://localhost:{VOICE_PORT}/")
        print(f"=" * 50)
        httpd.serve_forever()


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n服务器已停止")