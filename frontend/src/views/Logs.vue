<template>
  <div class="logs-page">
    <div class="page-container">
      <div class="page-header">
        <h2>识别日志</h2>
      </div>

      <!-- 筛选条件 -->
      <div class="filter-bar">
        <el-select
          v-model="filters.recognition_type"
          placeholder="识别类型"
          style="width: 120px"
          clearable
          @change="fetchLogs"
        >
          <el-option label="家庭成员" value="known" />
          <el-option label="陌生人" value="unknown" />
          <el-option label="待审核" value="pending_review" />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="margin-left: 10px"
          @change="handleDateChange"
        />

        <el-button style="margin-left: 10px" @click="resetFilters">
          重置
        </el-button>
      </div>

      <!-- 日志表格 -->
      <el-table :data="logs" v-loading="loading" stripe>
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
            <el-progress
              v-if="row.confidence"
              :percentage="(row.confidence * 100).toFixed(1)"
              :color="getConfidenceColor(row.confidence)"
              :stroke-width="12"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="recognition_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.recognition_type)">
              {{ getTypeText(row.recognition_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备" width="150" />
        <el-table-column prop="note" label="备注" />
        <el-table-column label="抓拍图片" width="100">
          <template #default="{ row }">
            <el-image
              v-if="row.image_path"
              :src="`/uploads/${row.image_path}`"
              :preview-src-list="[`/uploads/${row.image_path}`]"
              fit="cover"
              style="width: 50px; height: 50px; border-radius: 4px; cursor: pointer"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getLogList } from '@/api/log'
import dayjs from 'dayjs'

const loading = ref(false)
const logs = ref([])

const dateRange = ref(null)

const filters = reactive({
  recognition_type: '',
  start_date: '',
  end_date: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const res = await getLogList({
      page: pagination.page,
      page_size: pagination.page_size,
      ...filters
    })
    logs.value = res.items
    pagination.total = res.total
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const handleDateChange = (val) => {
  if (val) {
    filters.start_date = val[0]
    filters.end_date = val[1]
  } else {
    filters.start_date = ''
    filters.end_date = ''
  }
  fetchLogs()
}

const resetFilters = () => {
  filters.recognition_type = ''
  filters.start_date = ''
  filters.end_date = ''
  dateRange.value = null
  pagination.page = 1
  fetchLogs()
}

const handlePageChange = () => {
  fetchLogs()
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchLogs()
}

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

const getTypeTag = (type) => {
  const map = { known: 'success', unknown: 'danger', pending_review: 'warning' }
  return map[type] || 'info'
}

const getTypeText = (type) => {
  const map = { known: '家庭成员', unknown: '陌生人', pending_review: '待审核' }
  return map[type] || '未知'
}

onMounted(() => {
  fetchLogs()
})
</script>

<style lang="scss" scoped>
.logs-page {
  .filter-bar {
    margin-bottom: 20px;
    display: flex;
    align-items: center;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
