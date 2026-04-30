<template>
  <div class="members-page">
    <div class="page-container">
      <div class="page-header">
        <h2>人员管理</h2>
        <el-button type="primary" @click="showAddAndEnrollDialog">
          <el-icon><Plus /></el-icon>
          添加成员
        </el-button>
      </div>

      <div class="table-operations">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索成员姓名"
          style="width: 200px"
          clearable
          @clear="fetchMembers"
          @keyup.enter="searchMembers"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>

      <el-table :data="filteredMembers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="relationship" label="关系" width="120">
          <template #default="{ row }">
            {{ row.relationship || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="头像" width="100">
          <template #default="{ row }">
            <el-image
              v-if="row.avatar_image_path"
              :src="`/uploads/${row.avatar_image_path}`"
              fit="cover"
              style="width: 50px; height: 50px; border-radius: 50%"
            />
            <div v-else class="avatar-placeholder">
              <el-icon><User /></el-icon>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="添加时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注">
          <template #default="{ row }">
            {{ row.notes || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button type="warning" link size="small" @click="showFaceDialog(row)">
              更新人脸
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入成员姓名" />
        </el-form-item>
        <el-form-item label="关系" prop="relationship">
          <el-select v-model="form.relationship" placeholder="请选择关系" style="width: 100%">
            <el-option label="父亲" value="父亲" />
            <el-option label="母亲" value="母亲" />
            <el-option label="儿子" value="儿子" />
            <el-option label="女儿" value="女儿" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 录入人脸对话框 -->
    <el-dialog
      v-model="faceDialogVisible"
      :title="editingFaceId ? '更新人脸' : '录入人脸'"
      width="500px"
      @close="faceDialogVisible = false"
    >
      <el-form ref="faceFormRef" :model="faceForm" :rules="faceRules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="faceForm.name" :disabled="!!editingFaceId" placeholder="请输入成员姓名" />
        </el-form-item>
        <el-form-item label="照片" prop="image">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            accept="image/*"
            list-type="picture-card"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">请上传清晰的人脸照片，建议正面免冠照片</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="faceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEnroll" :loading="submitting">
          {{ editingFaceId ? '更新人脸' : '开始录入' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMemberList, addMember, updateMember, deleteMember, enrollMember, updateMemberFace } from '@/api/member'
import dayjs from 'dayjs'

const loading = ref(false)
const submitting = ref(false)
const members = ref([])
const searchKeyword = ref('')

const dialogVisible = ref(false)
const dialogTitle = ref('添加成员')
const editingId = ref(null)

const faceDialogVisible = ref(false)
const editingFaceId = ref(null)

const formRef = ref()
const uploadRef = ref()
const faceFormRef = ref()
const faceFile = ref(null)

const form = reactive({
  name: '',
  relationship: '',
  notes: ''
})

const faceForm = reactive({
  name: ''
})

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }]
}

const faceRules = {
  image: [{ required: true, message: '请上传照片', trigger: 'change' }]
}

const filteredMembers = computed(() => {
  if (!searchKeyword.value) return members.value
  return members.value.filter(m =>
    m.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

const fetchMembers = async () => {
  loading.value = true
  try {
    members.value = await getMemberList()
  } catch (error) {
    ElMessage.error('获取成员列表失败')
  } finally {
    loading.value = false
  }
}

const searchMembers = () => {
  fetchMembers()
}

const showAddDialog = () => {
  dialogTitle.value = '添加成员'
  editingId.value = null
  // 添加成功后，弹出录入人脸对话框
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  dialogTitle.value = '编辑成员'
  editingId.value = row.id
  form.name = row.name
  form.relationship = row.relationship || ''
  form.notes = row.notes || ''
  dialogVisible.value = true
}

const showFaceDialog = (row) => {
  editingFaceId.value = row.id  // 有值表示更新
  faceForm.name = row.name
  faceFile.value = null
  faceDialogVisible.value = true
}

// 添加新成员并录入人脸
const showAddAndEnrollDialog = () => {
  editingFaceId.value = null  // 无值表示新增
  faceForm.name = ''
  faceFile.value = null
  faceDialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.relationship = ''
  form.notes = ''
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      await updateMember(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await addMember(form)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除成员 "${row.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteMember(row.id)
    ElMessage.success('删除成功')
    fetchMembers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleFileChange = (file) => {
  faceFile.value = file.raw
}

const handleEnroll = async () => {
  if (!faceFile.value) {
    ElMessage.warning('请上传照片')
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('image', faceFile.value)

    if (editingFaceId.value) {
      // 更新已有成员的人脸
      formData.append('name', faceForm.name)
      await updateMemberFace(editingFaceId.value, formData)
      ElMessage.success('人脸更新成功')
    } else {
      // 新成员录入
      formData.append('name', faceForm.name)
      await enrollMember(formData)
      ElMessage.success('人脸录入成功')
    }
    faceDialogVisible.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error(error.message || '人脸录入失败')
  } finally {
    submitting.value = false
  }
}

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

onMounted(() => {
  fetchMembers()
})
</script>

<style lang="scss" scoped>
.members-page {
  .avatar-placeholder {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: #f0f2f5;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
  }

  .upload-tip {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
  }
}
</style>
