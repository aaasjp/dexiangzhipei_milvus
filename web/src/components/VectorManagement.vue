<template>
  <div>
    <div class="upload-section">
      <h3>上传文档到向量库</h3>
      <el-form :model="docForm" label-width="120px" style="margin-top: 20px;">
        <el-form-item label="租户代码">
          <el-input v-model="docForm.tenant_code" placeholder="请输入租户代码"></el-input>
        </el-form-item>
        <el-form-item label="知识库名称">
          <el-input v-model="docForm.org_code" placeholder="请输入知识库名称"></el-input>
        </el-form-item>
        <el-form-item label="文档文件">
          <el-upload
            ref="docUpload"
            :auto-upload="false"
            :on-change="handleDocChange"
            :limit="1"
            accept=".pdf,.doc,.docx,.txt">
            <el-button type="primary">选择文档</el-button>
            <template #tip>
              <div class="el-upload__tip">支持PDF、Word、TXT格式</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="uploadDocument" :loading="docUploading">上传文档</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-divider></el-divider>

    <div class="upload-section">
      <h3>上传问答对到向量库</h3>
      <el-form :model="qaForm" label-width="120px" style="margin-top: 20px;">
        <el-form-item label="租户代码">
          <el-input v-model="qaForm.tenant_code" placeholder="请输入租户代码"></el-input>
        </el-form-item>
        <el-form-item label="知识库名称">
          <el-input v-model="qaForm.org_code" placeholder="请输入知识库名称"></el-input>
        </el-form-item>
        <el-form-item label="问答对文件">
          <el-upload
            ref="qaUpload"
            :auto-upload="false"
            :on-change="handleQaChange"
            :limit="1"
            accept=".xlsx">
            <el-button type="primary">选择Excel文件</el-button>
            <template #tip>
              <div class="el-upload__tip">请使用问答库模板.xlsx格式</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="uploadQA" :loading="qaUploading">上传问答对</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-divider></el-divider>

    <div class="search-section">
      <h3>向量库检索</h3>
      <el-form :model="searchForm" label-width="120px" style="margin-top: 20px;">
        <el-form-item label="租户代码">
          <el-input v-model="searchForm.tenant_code" placeholder="请输入租户代码"></el-input>
        </el-form-item>
        <el-form-item label="知识库名称">
          <el-input v-model="searchForm.org_code" placeholder="请输入知识库名称"></el-input>
        </el-form-item>
        <el-form-item label="检索类型">
          <el-radio-group v-model="searchForm.collection_type">
            <el-radio label="QA">问答对</el-radio>
            <el-radio label="DOC">文档</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="查询内容">
          <el-input v-model="searchForm.query" type="textarea" :rows="3" placeholder="请输入查询内容"></el-input>
        </el-form-item>
        <el-form-item label="结果数量">
          <el-input-number v-model="searchForm.limit" :min="1" :max="20" :step="1"></el-input-number>
        </el-form-item>
        <el-form-item label="混合检索">
          <el-switch v-model="searchForm.use_hybrid"></el-switch>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchVectorDB" :loading="searching">检索</el-button>
        </el-form-item>
      </el-form>

      <div v-if="searchResults.length > 0" style="margin-top: 20px;">
        <h4>检索结果（共{{ searchResults.length }}条）</h4>
        <div v-for="(item, index) in searchResults" :key="index" class="result-item">
          <div v-if="item.question">
            <strong>问题：</strong>{{ item.question }}<br>
            <strong>答案：</strong>{{ item.answer }}<br>
          </div>
          <div v-else>
            <strong>文档名：</strong>{{ item.file_name }}<br>
            <strong>内容：</strong>{{ item.content }}<br>
          </div>
          <div style="margin-top: 5px; font-size: 12px; color: #909399;">
            <span>来源：{{ item.source || '未知' }}</span>
            <span style="margin-left: 20px;">相似度：{{ (item.score || item.distance || 0).toFixed(4) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'VectorManagement',
  data() {
    return {
      docForm: {
        tenant_code: '',
        org_code: '',
        file: null
      },
      docUploading: false,
      qaForm: {
        tenant_code: '',
        org_code: '',
        file: null
      },
      qaUploading: false,
      searchForm: {
        tenant_code: '',
        org_code: '',
        collection_type: 'QA',
        query: '',
        limit: 5,
        use_hybrid: true
      },
      searching: false,
      searchResults: []
    }
  },
  methods: {
    handleDocChange(file) {
      this.docForm.file = file.raw
    },
    handleQaChange(file) {
      this.qaForm.file = file.raw
    },
    async uploadDocument() {
      if (!this.docForm.tenant_code || !this.docForm.org_code) {
        ElMessage.warning('请填写租户代码和知识库名称')
        return
      }
      if (!this.docForm.file) {
        ElMessage.warning('请选择文档文件')
        return
      }

      this.docUploading = true
      try {
        const formData = new FormData()
        formData.append('file', this.docForm.file)
        
        const uploadRes = await axios.post('/chat_service/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        if (uploadRes.data.status === 'success') {
          const fileUrl = uploadRes.data.data.file_url
          const fileName = uploadRes.data.data.file_name

          const addRes = await axios.post('/vector_db_service/add_document', {
            tenant_code: this.docForm.tenant_code,
            org_code: this.docForm.org_code,
            doc_url: fileUrl,
            doc_name: fileName
          })

          if (addRes.data.status === 'success') {
            ElMessage.success('文档上传成功')
            this.docForm.file = null
            this.$refs.docUpload.clearFiles()
          } else {
            ElMessage.error('添加文档失败：' + addRes.data.msg)
          }
        } else {
          ElMessage.error('文件上传失败：' + uploadRes.data.msg)
        }
      } catch (error) {
        ElMessage.error('上传失败：' + error.message)
      } finally {
        this.docUploading = false
      }
    },
    async uploadQA() {
      if (!this.qaForm.tenant_code || !this.qaForm.org_code) {
        ElMessage.warning('请填写租户代码和知识库名称')
        return
      }
      if (!this.qaForm.file) {
        ElMessage.warning('请选择Excel文件')
        return
      }

      this.qaUploading = true
      try {
        const formData = new FormData()
        formData.append('file', this.qaForm.file)
        
        const uploadRes = await axios.post('/chat_service/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        if (uploadRes.data.status === 'success') {
          const fileUrl = uploadRes.data.data.file_url
          
          const addRes = await axios.post('/vector_db_service/add_qa_from_url', {
            tenant_code: this.qaForm.tenant_code,
            org_code: this.qaForm.org_code,
            template_file_url: fileUrl
          })

          if (addRes.data.status === 'success') {
            ElMessage.success('问答对上传成功：' + addRes.data.msg)
            this.qaForm.file = null
            this.$refs.qaUpload.clearFiles()
          } else {
            ElMessage.error('添加问答对失败：' + addRes.data.msg)
          }
        } else {
          ElMessage.error('文件上传失败：' + uploadRes.data.msg)
        }
      } catch (error) {
        ElMessage.error('上传失败：' + error.message)
      } finally {
        this.qaUploading = false
      }
    },
    async searchVectorDB() {
      if (!this.searchForm.tenant_code || !this.searchForm.org_code) {
        ElMessage.warning('请填写租户代码和知识库名称')
        return
      }
      if (!this.searchForm.query) {
        ElMessage.warning('请输入查询内容')
        return
      }

      this.searching = true
      this.searchResults = []
      try {
        const res = await axios.post('/vector_db_service/search_from_vector_db', {
          tenant_code: this.searchForm.tenant_code,
          org_code: this.searchForm.org_code,
          query: this.searchForm.query,
          collection_type: this.searchForm.collection_type,
          limit: this.searchForm.limit,
          use_hybrid: this.searchForm.use_hybrid
        })

        if (res.data.status === 'success' && res.data.data && res.data.data.entities) {
          this.searchResults = res.data.data.entities[0] || []
          ElMessage.success(`检索成功，找到${this.searchResults.length}条结果`)
        } else {
          ElMessage.error('检索失败：' + (res.data.msg || '未知错误'))
        }
      } catch (error) {
        ElMessage.error('检索失败：' + error.message)
      } finally {
        this.searching = false
      }
    }
  }
}
</script>

<style scoped>
.upload-section {
  margin-bottom: 30px;
}

.search-section {
  margin-top: 30px;
}

.result-item {
  background: #f9f9f9;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}
</style>

