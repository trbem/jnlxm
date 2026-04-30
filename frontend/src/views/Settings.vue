<template>
  <div class="settings-page">
    <div class="page-container">
      <div class="page-header">
        <h2>系统设置</h2>
        <el-button type="primary" @click="saveSettings" :loading="saving">
          保存设置
        </el-button>
      </div>

      <el-form :model="settings" label-width="140px" class="settings-form">
        <!-- 人脸识别设置 -->
        <div class="settings-section">
          <h3>人脸识别设置</h3>

          <el-form-item label="识别阈值">
            <div class="slider-with-value">
              <el-slider
                v-model="settings.face_threshold"
                :min="0.4"
                :max="0.9"
                :step="0.01"
                :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
              />
              <span class="value-display">{{ (settings.face_threshold * 100).toFixed(0) }}%</span>
            </div>
            <div class="form-tip">
              数值越高要求越严格，建议设置在 55%-65% 之间
            </div>
          </el-form-item>

          <el-form-item label="检测间隔">
            <el-input-number
              v-model="settings.detection_interval"
              :min="5"
              :max="60"
              :step="1"
            />
            <span class="unit">秒</span>
          </el-form-item>
        </div>

        <!-- 通知设置 -->
        <div class="settings-section">
          <h3>通知设置</h3>

          <el-form-item label="启用通知">
            <el-switch v-model="settings.notification_enabled" />
          </el-form-item>

          <el-form-item label="陌生人告警">
            <el-switch v-model="settings.stranger_alert" />
          </el-form-item>

          <el-form-item label="通知方式">
            <el-checkbox-group v-model="settings.notification_ways">
              <el-checkbox label="wecom">企业微信</el-checkbox>
              <el-checkbox label="dingtalk">钉钉</el-checkbox>
              <el-checkbox label="email">邮件</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="测试通知">
            <div class="test-notification">
              <el-select v-model="testNotificationWay" placeholder="选择通知方式" style="width: 120px; margin-right: 10px">
                <el-option label="企业微信" value="wecom" />
                <el-option label="钉钉" value="dingtalk" />
                <el-option label="邮件" value="email" />
              </el-select>
              <el-button @click="handleTestNotification" :loading="testing">
                发送测试
              </el-button>
              <span class="connection-status" v-if="connectionStatus">
                <el-tag :type="connectionStatus.wecom_configured || connectionStatus.dingtalk_configured || connectionStatus.email_configured ? 'success' : 'info'" size="small">
                  {{ connectionStatus.wecom_configured || connectionStatus.dingtalk_configured || connectionStatus.email_configured ? '已配置' : '未配置' }}
                </el-tag>
              </span>
            </div>
          </el-form-item>
        </div>

        <!-- Webhook 配置 -->
        <div class="settings-section">
          <h3>Webhook 配置</h3>

          <el-form-item label="企业微信 Webhook">
            <el-input
              v-model="webhooks.wecom"
              placeholder="请输入企业微信机器人 Webhook 地址"
            />
          </el-form-item>

          <el-form-item label="钉钉 Webhook">
            <el-input
              v-model="webhooks.dingtalk"
              placeholder="请输入钉钉群机器人 Webhook 地址"
            />
          </el-form-item>
        </div>

        <!-- 邮件配置 -->
        <div class="settings-section">
          <h3>邮件配置</h3>

          <el-form-item label="SMTP 服务器">
            <el-input v-model="emailConfig.host" placeholder="smtp.example.com" />
          </el-form-item>

          <el-form-item label="端口">
            <el-input-number v-model="emailConfig.port" :min="1" :max="65535" />
          </el-form-item>

          <el-form-item label="用户名">
            <el-input v-model="emailConfig.user" placeholder="发件人邮箱" />
          </el-form-item>

          <el-form-item label="密码">
            <el-input v-model="emailConfig.password" type="password" show-password placeholder="授权码或密码" />
          </el-form-item>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, getAllConfigs, updateConfig } from '@/api/config'

const saving = ref(false)
const testing = ref(false)
const testNotificationWay = ref('wecom')
const connectionStatus = ref(null)

const settings = reactive({
  face_threshold: 0.6,
  detection_interval: 10,
  notification_enabled: true,
  stranger_alert: true,
  notification_ways: ['wecom']
})

const webhooks = reactive({
  wecom: '',
  dingtalk: ''
})

const emailConfig = reactive({
  host: '',
  port: 587,
  user: '',
  password: ''
})

const fetchSettings = async () => {
  try {
    const config = await getConfig()
    settings.face_threshold = config.face_threshold
    settings.detection_interval = config.detection_interval
    settings.notification_enabled = config.notification_enabled
    settings.stranger_alert = config.stranger_alert

    const allConfigs = await getAllConfigs()
    if (allConfigs.notification_ways) {
      try {
        settings.notification_ways = JSON.parse(allConfigs.notification_ways)
      } catch (e) {
        settings.notification_ways = [allConfigs.notification_ways]
      }
    }

    if (allConfigs.wecom_webhook) webhooks.wecom = allConfigs.wecom_webhook
    if (allConfigs.dingtalk_webhook) webhooks.dingtalk = allConfigs.dingtalk_webhook
    if (allConfigs.email_host) emailConfig.host = allConfigs.email_host
    if (allConfigs.email_port) emailConfig.port = parseInt(allConfigs.email_port)
    if (allConfigs.email_user) emailConfig.user = allConfigs.email_user
  } catch (error) {
    console.error('获取配置失败:', error)
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await updateConfig('face_threshold', settings.face_threshold.toString())
    await updateConfig('detection_interval', settings.detection_interval.toString())
    await updateConfig('notification_enabled', settings.notification_enabled.toString())
    await updateConfig('stranger_alert', settings.stranger_alert.toString())
    await updateConfig('notification_ways', JSON.stringify(settings.notification_ways))

    await updateConfig('wecom_webhook', webhooks.wecom)
    await updateConfig('dingtalk_webhook', webhooks.dingtalk)
    await updateConfig('email_host', emailConfig.host)
    await updateConfig('email_port', emailConfig.port.toString())
    await updateConfig('email_user', emailConfig.user)
    await updateConfig('email_password', emailConfig.password)

    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleTestNotification = async () => {
  testing.value = true
  try {
    const response = await fetch('/api/notification/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: `【家庭监控系统测试】这是一条测试消息，发送时间: ${new Date().toLocaleString()}`,
        way: testNotificationWay.value
      })
    })
    const result = await response.json()
    if (result.success) {
      ElMessage.success('测试通知发送成功')
    } else {
      ElMessage.warning(result.message || '测试通知发送失败')
    }
  } catch (error) {
    ElMessage.error('发送测试通知失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style lang="scss" scoped>
.settings-page {
  .settings-form {
    max-width: 800px;
  }

  .settings-section {
    margin-bottom: 40px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 20px;
      padding-bottom: 10px;
      border-bottom: 1px solid #ebeef5;
    }
  }

  .slider-with-value {
    display: flex;
    align-items: center;
    width: 300px;

    .el-slider {
      flex: 1;
    }

    .value-display {
      margin-left: 16px;
      width: 50px;
      font-weight: 600;
      color: #409eff;
    }
  }

  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }

  .unit {
    margin-left: 8px;
    color: #606266;
  }

  .test-notification {
    display: flex;
    align-items: center;

    .connection-status {
      margin-left: 12px;
    }
  }
}
</style>
