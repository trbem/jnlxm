-- 家庭监控智能助手 - 数据库初始化脚本

-- 设备表
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name VARCHAR(100) NOT NULL,
    device_token VARCHAR(64) UNIQUE NOT NULL,
    device_type VARCHAR(50) DEFAULT 'ESP32-S3-EYE',
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);

-- 家庭成员表
CREATE TABLE IF NOT EXISTS family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    avatar_image_path VARCHAR(255),
    face_encoding TEXT NOT NULL,  -- JSON 存储人脸特征向量
    relationship VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- 识别日志表
CREATE TABLE IF NOT EXISTS recognition_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    member_name VARCHAR(100),
    confidence REAL,
    matched BOOLEAN,
    image_path VARCHAR(255),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(50),
    recognition_type VARCHAR(20) DEFAULT 'unknown',  -- known, unknown, pending_review
    note TEXT,
    FOREIGN KEY (member_id) REFERENCES family_members(id)
);

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description VARCHAR(255),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 通知日志表
CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER,
    notification_type VARCHAR(50),  -- wecom, dingtalk, email
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed
    sent_at DATETIME,
    error_message TEXT,
    FOREIGN KEY (log_id) REFERENCES recognition_logs(id)
);

-- 管理员用户表
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_super_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- 初始化默认配置
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
    ('face_threshold', '0.6', '人脸识别相似度阈值'),
    ('detection_interval', '10', '检测间隔(秒)'),
    ('notification_enabled', 'true', '是否启用通知'),
    ('notification_ways', '["wecom"]', '通知方式(wecom/dingtalk/email)'),
    ('stranger_alert', 'true', '陌生人是否报警');

-- 初始化默认管理员 (密码: admin123)
INSERT OR IGNORE INTO admin_users (username, hashed_password, is_super_admin) VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWz1E3OQT.K2', TRUE);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_recognition_logs_timestamp ON recognition_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_recognition_logs_member ON recognition_logs(member_id);
CREATE INDEX IF NOT EXISTS idx_recognition_logs_device ON recognition_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_family_members_active ON family_members(is_active);
