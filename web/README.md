# AI助手管理平台前端

这是一个基于Vue 3和Element Plus的单页面应用，用于管理向量库和进行AI对话。

## 技术栈

- Vue 3
- Element Plus
- Vite
- Axios

## 安装依赖

```bash
npm install
```

## 开发模式

```bash
npm run dev
```

启动后访问 `http://localhost:8080`

## 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录

## 预览生产版本

```bash
npm run preview
```

## 功能特性

### 1. 向量库管理
- **上传文档**：支持上传PDF、Word、TXT等格式的文档到向量库
- **上传问答对**：支持上传Excel格式的问答对文件（需使用问答库模板.xlsx格式）
- **向量库检索**：支持对向量库进行检索，可以检索问答对或文档内容
  - 支持混合检索（BM25+向量检索）
  - 可设置检索结果数量
  - 显示检索结果的相似度分数

### 2. 对话问答
- **AI对话**：基于大模型的智能问答
- **流式输出**：支持实时流式输出回答内容
- **多轮对话**：支持基于对话历史的上下文理解
- **文档来源**：显示回答参考的文档来源
- **延申问题推荐**：自动生成相关延申问题

## 配置说明

### API代理配置

在 `vite.config.js` 中配置了API代理：
- `/vector_db_service` -> `http://localhost:8005`
- `/chat_service` -> `http://localhost:8006`

如果后端服务地址不同，请修改 `vite.config.js` 中的 `proxy` 配置。

## 注意事项

1. **后端服务**：确保后端服务已启动
   - 向量数据库服务：`http://localhost:8005`
   - 对话问答服务：`http://localhost:8006`

2. **CORS配置**：确保后端服务已配置CORS，允许前端域名访问。

3. **文件格式**：
   - 文档支持：PDF、Word、TXT
   - 问答对文件：Excel格式，需使用问答库模板.xlsx格式

4. **会话管理**：对话页面会自动生成session_id，支持多轮对话。
