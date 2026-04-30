<template>
  <div class="monitor-page">
    <div class="page-container">
      <div class="page-header">
        <h2>实时监控</h2>
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <div class="monitor-grid">
        <!-- 实时画面 -->
        <div class="monitor-card">
          <div class="card-header">
            <span class="device-name">{{ currentDevice?.device_name || '未连接设备' }}</span>
            <el-tag :type="currentDevice?.is_online ? 'success' : 'info'" size="small">
              {{ currentDevice?.is_online ? '在线' : '离线' }}
            </el-tag>
          </div>
          <div class="card-body">
            <div class="image-container">
              <img v-if="latestImage" :src="latestImage" alt="监控画面" @error="onImageError" />
              <div v-else class="no-image">
                <el-icon :size="48"><VideoCamera /></el-icon>
                <span>暂无画面</span>
              </div>
              <div class="image-overlay">
                <span class="time">{{ currentTime }}</span>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <span class="info">最后更新: {{ lastUpdate }}</span>
          </div>
        </div>

        <!-- 设备状态 -->
        <div class="monitor-card">
          <div class="card-header">
            <span class="device-name">设备状态</span>
          </div>
          <div class="card-body status-info">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="设备名称">
                {{ currentDevice?.device_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="在线状态">
                <el-tag :type="currentDevice?.is_online ? 'success' : 'danger'">
                  {{ currentDevice?.is_online ? '在线' : '离线' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="最后心跳">
                {{ currentDevice?.last_seen ? formatTime(currentDevice.last_seen) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="今日识别">
                {{ currentDevice?.today_recognitions || 0 }} 次
              </el-descriptions-item>
              <el-descriptions-item label="陌生人告警">
                {{ currentDevice?.today_strangers || 0 }} 次
              </el-descriptions-item>
            </el-descriptions>

            <div class="quick-stats">
              <div class="stat-item">
                <span class="label">家庭成员</span>
                <span class="value success">{{ knownCount }}</span>
              </div>
              <div class="stat-item">
                <span class="label">陌生人</span>
                <span class="value danger">{{ unknownCount }}</span>
              </div>
              <div class="stat-item">
                <span class="label">总计</span>
                <span class="value">{{ knownCount + unknownCount }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 设备列表 -->
      <div class="device-list" v-if="devices.length > 0">
        <h3>设备列表</h3>
        <el-table :data="devices" stripe v-loading="loading">
          <el-table-column prop="device_name" label="设备名称" width="180" />
          <el-table-column prop="device_type" label="设备型号" width="150" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_online ? 'success' : 'info'">
                {{ row.is_online ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_seen" label="最后心跳" width="180">
            <template #default="{ row }">
              {{ row.last_seen ? formatTime(row.last_seen) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="today_recognitions" label="今日识别" width="100" />
          <el-table-column prop="today_strangers" label="今日告警" width="100">
            <template #default="{ row }">
              <el-tag type="danger" v-if="row.today_strangers > 0">{{ row.today_strangers }}</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 最近告警 -->
      <div class="recent-alerts">
        <h3>最近告警</h3>
        <el-table :data="alerts" stripe v-loading="loading">
          <el-table-column prop="timestamp" label="时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column prop="recognition_type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.recognition_type === 'unknown' ? 'danger' : 'warning'">
                {{ row.recognition_type === 'unknown' ? '陌生人' : '异常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="member_name" label="人员" width="120">
            <template #default="{ row }">
              {{ row.member_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="device_id" label="设备" width="150" />
          <el-table-column prop="note" label="备注" />
          <el-table-column label="抓拍图片" width="80">
            <template #default="{ row }">
              <el-image
                v-if="row.image_path"
                :src="`/uploads/${row.image_path}`"
                :preview-src-list="[`/uploads/${row.image_path}`]"
                fit="cover"
                style="width: 40px; height: 40px; border-radius: 4px; cursor: pointer"
              />
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="alerts.length === 0" class="no-data">
          <el-empty description="暂无告警记录" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getDeviceList } from '@/api/device'
import { getRecentLogs } from '@/api/log'
import dayjs from 'dayjs'

const loading = ref(false)
const devices = ref([])
const alerts = ref([])
const latestImage = ref('')
const currentTime = ref('')
const lastUpdate = ref('-')

const currentDevice = computed(() => devices.value[0] || null)
const knownCount = computed(() => alerts.value.filter(a => a.recognition_type === 'known').length)
const unknownCount = computed(() => alerts.value.filter(a => a.recognition_type === 'unknown').length)

const fetchData = async () => {
  loading.value = true
  try {
    const [deviceList, recentAlerts] = await Promise.all([
      getDeviceList(),
      getRecentLogs(20)
    ])
    devices.value = deviceList
    alerts.value = recentAlerts.filter(log => log.recognition_type === 'unknown')

    if (alerts.value.length > 0 && alerts.value[0].image_path) {
      latestImage.value = `/uploads/${alerts.value[0].image_path}`
    }
    lastUpdate.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
  } catch (error) {
    console.error('获取数据失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchData()
}

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const onImageError = () => {
  latestImage.value = ''
}

const updateTime = () => {
  currentTime.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
}

let timer = null

onMounted(() => {
  fetchData()
  updateTime()
  timer = setInterval(() => {
    updateTime()
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.monitor-page {
  .monitor-grid {
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 20px;
    margin-bottom: 20px;
  }

  .monitor-card {
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

    .card-header {
      padding: 12px 16px;
      background: #fafafa;
      border-bottom: 1px solid #ebeef5;
      display: flex;
      justify-content: space-between;
      align-items: center;

      .device-name {
        font-weight: 600;
        color: #303133;
      }
    }

    .card-body {
      .image-container {
        position: relative;
        width: 100%;
        aspect-ratio: 4/3;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .no-image {
          width: 100%;
          height: 100%;
          min-height: 240px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: #f0f2f5;
          color: #909399;

          span {
            margin-top: 12px;
          }
        }

        .image-overlay {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          padding: 8px 12px;
          background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
          color: #fff;
          font-size: 12px;
        }
      }

      &.status-info {
        padding: 16px;
      }
    }

    .card-footer {
      padding: 8px 16px;
      background: #fafafa;
      border-top: 1px solid #ebeef5;
      font-size: 12px;
      color: #909399;
    }
  }

  .quick-stats {
    display: flex;
    gap: 16px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #ebeef5;

    .stat-item {
      flex: 1;
      text-align: center;

      .label {
        display: block;
        font-size: 12px;
        color: #909399;
        margin-bottom: 4px;
      }

      .value {
        font-size: 24px;
        font-weight: 600;
        color: #303133;

        &.success { color: #67c23a; }
        &.danger { color: #f56c6c; }
      }
    }
  }

  .device-list {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #303133;
    }
  }

  .recent-alerts {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #303133;
    }

    .no-data {
      padding: 40px 0;
    }
  }
}
</style>
