<template>
  <div class="container">
    <div class="header">
      <h1>AI助手管理平台</h1>
    </div>
    
    <div class="tabs">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="向量库管理" name="vector">
          <VectorManagement />
        </el-tab-pane>

        <el-tab-pane label="对话问答" name="chat">
          <ChatInterface />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import VectorManagement from './components/VectorManagement.vue'
import ChatInterface from './components/ChatInterface.vue'

export default {
  name: 'App',
  components: {
    VectorManagement,
    ChatInterface
  },
  data() {
    return {
      activeTab: 'vector'
    }
  },
  methods: {
    handleTabChange(name) {
      if (name === 'chat' && this.$refs.chatInterface) {
        this.$refs.chatInterface.initSession()
      }
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.header h1 {
  margin: 0;
  font-size: 24px;
}

.tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
</style>

