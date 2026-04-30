<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e6f7ff; color: #1890ff">
          <el-icon :size="32"><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_members }}</div>
          <div class="stat-label">家庭成员</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #fff7e6; color: #faad14">
          <el-icon :size="32"><List /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.today_logs }}</div>
          <div class="stat-label">今日识别</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #fff1f0; color: #ff4d4f">
          <el-icon :size="32"><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.stranger_alerts }}</div>
          <div class="stat-label">陌生人告警</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon" style="background: #f6ffed; color: #52c41a">
          <el-icon :size="32"><SuccessFilled /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.recognition_rate }}%</div>
          <div class="stat-label">识别成功率</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-container">
      <div class="chart-box">
        <h3>识别趋势</h3>
        <div ref="trendChartRef" class="chart"></div>
      </div>
    </div>

    <!-- 最近识别记录 -->
    <div class="page-container recent-logs">
      <div class="page-header">
        <h2>最近识别记录</h2>
        <el-button type="primary" link @click="$router.push('/logs')">
          查看更多 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>

      <el-table :data="recentLogs" stripe>
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="member_name" label="成员" width="120">
          <template #default="{ row }">
            {{ row.member_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-tag :type="getConfidenceType(row.confidence)">
              {{ row.confidence ? (row.confidence * 100).toFixed(1) + '%' : '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recognition_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.recognition_type)">
              {{ getTypeText(row.recognition_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备" />
        <el-table-column label="图片" width="80">
          <template #default="{ row }">
            <el-image
              v-if="row.image_path"
              :src="`/uploads/${row.image_path}`"
              :preview-src-list="[`/uploads/${row.image_path}`]"
              fit="cover"
              style="width: 40px; height: 40px; border-radius: 4px"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getStatsOverview, getRecognitionTrend } from '@/api/stats'
import * as echarts from 'echarts'
import dayjs from 'dayjs'

const stats = ref({
  total_members: 0,
  total_logs: 0,
  today_logs: 0,
  stranger_alerts: 0,
  recognition_rate: 0
})

const recentLogs = ref([])
const trendChartRef = ref(null)
let trendChart = null

const fetchStats = async () => {
  try {
    const res = await getStatsOverview()
    stats.value = res
    recentLogs.value = res.recent_logs || []
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const fetchTrendData = async () => {
  try {
    const trendData = await getRecognitionTrend()
    updateChart(trendData)
  } catch (error) {
    console.error('获取趋势数据失败:', error)
  }
}

const updateChart = (trendData) => {
  if (!trendChartRef.value) return

  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const dates = trendData.map(item => item.date)
  const knownData = trendData.map(item => item.known)
  const unknownData = trendData.map(item => item.unknown)

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function(params) {
        let result = params[0].name + '<br/>'
        params.forEach(item => {
          result += item.marker + item.seriesName + ': ' + item.value + '<br/>'
        })
        return result
      }
    },
    legend: {
      data: ['家庭成员', '陌生人'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { color: '#666' }
    },
    yAxis: {
      type: 'value',
      name: '识别次数',
      axisLabel: { color: '#666' }
    },
    series: [
      {
        name: '家庭成员',
        type: 'bar',
        stack: 'total',
        data: knownData,
        itemStyle: { color: '#67c23a' },
        barWidth: '40%'
      },
      {
        name: '陌生人',
        type: 'bar',
        stack: 'total',
        data: unknownData,
        itemStyle: { color: '#f56c6c' }
      }
    ]
  })
}

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getConfidenceType = (confidence) => {
  if (!confidence) return 'info'
  return confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'warning' : 'danger'
}

const getTypeTag = (type) => {
  const map = { known: 'success', unknown: 'danger', pending_review: 'warning' }
  return map[type] || 'info'
}

const getTypeText = (type) => {
  const map = { known: '家庭成员', unknown: '陌生人', pending_review: '待审核' }
  return map[type] || '未知'
}

let refreshTimer = null

onMounted(() => {
  fetchStats()
  fetchTrendData()
  refreshTimer = setInterval(() => {
    fetchStats()
    fetchTrendData()
  }, 30000)
  window.addEventListener('resize', () => trendChart?.resize())
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  trendChart?.dispose()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .chart-container {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
    margin-bottom: 20px;

    .chart-box {
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

      .chart {
        height: 300px;
      }
    }
  }

  .recent-logs {
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h2 {
        margin: 0;
      }
    }
  }
}
</style>
