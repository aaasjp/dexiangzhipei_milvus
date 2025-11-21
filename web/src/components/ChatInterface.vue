<template>
  <div class="chat-container">
    <div class="chat-messages" ref="messagesContainer">
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div>
          <div class="message-content" v-html="formatMessage(msg.content)"></div>
          <div class="message-time">{{ formatTime(msg.created_at) }}</div>
          <div v-if="msg.sources && msg.sources.length > 0" class="sources">
            <strong>参考来源：</strong>
            <span v-for="(source, idx) in msg.sources" :key="idx">
              <a :href="source.url" target="_blank">{{ source.name }}</a>
              <span v-if="idx < msg.sources.length - 1">, </span>
            </span>
          </div>
          <div v-if="msg.suggested_questions && msg.suggested_questions.length > 0" class="suggested-questions">
            <span 
              v-for="(q, idx) in msg.suggested_questions" 
              :key="idx"
              class="suggested-question"
              @click="askQuestion(q)">
              {{ q }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="streaming" class="message assistant">
        <div>
          <div class="message-content">{{ currentAnswer }}</div>
          <div class="message-time">正在输入...</div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <el-form :model="chatForm" label-width="100px">
        <el-form-item label="用户ID">
          <el-input v-model="chatForm.user_id" placeholder="请输入用户ID" style="width: 200px;"></el-input>
        </el-form-item>
        <el-form-item label="租户代码">
          <el-input v-model="chatForm.tenant_code" placeholder="可选" style="width: 200px;"></el-input>
        </el-form-item>
        <el-form-item label="组织代码">
          <el-input v-model="chatForm.org_code" placeholder="可选" style="width: 200px;"></el-input>
        </el-form-item>
        <el-form-item label="问题">
          <el-input 
            v-model="chatForm.question" 
            type="textarea" 
            :rows="3"
            placeholder="请输入您的问题..."
            @keyup.ctrl.enter="sendMessage"></el-input>
        </el-form-item>
        <el-form-item label="选项">
          <el-checkbox v-model="chatForm.use_vector_db">使用向量库</el-checkbox>
          <el-checkbox v-model="chatForm.stream">流式输出</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="sendMessage" :loading="chatting">发送 (Ctrl+Enter)</el-button>
          <el-button @click="clearChat">清空对话</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'ChatInterface',
  data() {
    return {
      chatForm: {
        user_id: 'user001',
        tenant_code: '',
        org_code: '',
        question: '',
        use_vector_db: true,
        stream: true,
        session_id: ''
      },
      chatting: false,
      streaming: false,
      currentAnswer: '',
      messages: []
    }
  },
  mounted() {
    this.initSession()
  },
  methods: {
    initSession() {
      this.chatForm.session_id = this.generateSessionId()
    },
    generateSessionId() {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    },
    async sendMessage() {
      if (!this.chatForm.user_id) {
        ElMessage.warning('请输入用户ID')
        return
      }
      if (!this.chatForm.question) {
        ElMessage.warning('请输入问题')
        return
      }

      const question = this.chatForm.question
      this.chatForm.question = ''
      
      this.messages.push({
        role: 'user',
        content: question,
        created_at: new Date().toISOString()
      })

      this.chatting = true
      this.streaming = this.chatForm.stream
      this.currentAnswer = ''

      try {
        if (this.chatForm.stream) {
          await this.sendStreamMessage(question)
        } else {
          await this.sendNormalMessage(question)
        }
      } catch (error) {
        ElMessage.error('发送失败：' + error.message)
        this.messages.push({
          role: 'assistant',
          content: '抱歉，发生了错误：' + error.message,
          created_at: new Date().toISOString()
        })
      } finally {
        this.chatting = false
        this.streaming = false
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },
    async sendStreamMessage(question) {
      const response = await fetch('/chat_service/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: this.chatForm.user_id,
          session_id: this.chatForm.session_id,
          question: question,
          tenant_code: this.chatForm.tenant_code || '',
          org_code: this.chatForm.org_code || '',
          use_vector_db: this.chatForm.use_vector_db,
          stream: true,
          limit: 5
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6))
            if (data.error) {
              throw new Error(data.error)
            }
            if (data.done) {
              this.messages.push({
                role: 'assistant',
                content: data.content,
                sources: data.sources?.documents || [],
                suggested_questions: data.suggested_questions || [],
                created_at: new Date().toISOString()
              })
              this.currentAnswer = ''
            } else {
              this.currentAnswer = data.content
            }
          }
        }
      }
    },
    async sendNormalMessage(question) {
      const res = await axios.post('/chat_service/chat', {
        user_id: this.chatForm.user_id,
        session_id: this.chatForm.session_id,
        question: question,
        tenant_code: this.chatForm.tenant_code || '',
        org_code: this.chatForm.org_code || '',
        use_vector_db: this.chatForm.use_vector_db,
        stream: false,
        limit: 5
      })

      if (res.data.status === 'success') {
        this.messages.push({
          role: 'assistant',
          content: res.data.data.answer,
          sources: res.data.data.sources?.documents || [],
          suggested_questions: res.data.data.suggested_questions || [],
          created_at: new Date().toISOString()
        })
      } else {
        throw new Error(res.data.msg)
      }
    },
    askQuestion(question) {
      this.chatForm.question = question
      this.sendMessage()
    },
    clearChat() {
      this.messages = []
      this.chatForm.session_id = this.generateSessionId()
    },
    formatMessage(content) {
      if (!content) return ''
      return content.replace(/\n/g, '<br>')
    },
    formatTime(timeStr) {
      if (!timeStr) return ''
      const date = new Date(timeStr)
      return date.toLocaleString('zh-CN')
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fafafa;
}

.message {
  margin-bottom: 20px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #409eff;
  color: white;
}

.message.assistant .message-content {
  background: white;
  border: 1px solid #e4e7ed;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.sources {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.suggested-questions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggested-question {
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  color: #409eff;
}

.suggested-question:hover {
  background: #e1f3ff;
}

.input-area {
  padding: 20px;
  background: white;
  border-top: 1px solid #e4e7ed;
}
</style>

