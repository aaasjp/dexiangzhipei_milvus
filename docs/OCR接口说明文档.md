# 文档解析API接口说明文档

## 概述

文档解析API服务是一个基于FastAPI构建的RESTful API，提供多种文档格式的解析服务。支持PDF、Word、PowerPoint、图片和文本文件的解析，并提供三种不同的解析模式以满足不同场景的需求。

## 服务信息

- **服务名称**: 文档解析API服务
- **版本**: 1.0.0
- **基础URL**: `http://localhost:8000`
- **API文档**: `http://localhost:8000/docs`
- **ReDoc文档**: `http://localhost:8000/redoc`

## 支持的文档格式

| 文档类型 | 支持格式 | 扩展名 |
|---------|---------|--------|
| PDF文档 | PDF | `.pdf` |
| Word文档 | Word | `.doc`, `.docx` |
| PowerPoint文档 | PowerPoint | `.ppt`, `.pptx` |
| 图片文件 | 图片 | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` |
| 文本文件 | 文本 | `.txt`, `.md` |

## 解析模式

### 1. 极速模式 (speed)
- **特点**: 解析速度快，适合大批量文档处理
- **适用场景**: 对速度要求高，对准确性要求相对较低的场景

### 2. 精确模式 (accuracy)
- **特点**: 解析效果准确，适合高质量文档处理
- **适用场景**: 对准确性要求高，对速度要求相对较低的场景

### 3. 均衡模式 (balanced) - 默认
- **特点**: 兼顾准确性和解析速度，适合日常使用
- **适用场景**: 平衡速度和准确性的通用场景

## API接口详情

### 1. 根路径

**GET** `/`

获取API基本信息。

**响应示例**:
```json
{
  "message": "文档解析API服务",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

### 2. 健康检查

**GET** `/health`

检查服务运行状态。

**响应示例**:
```json
{
  "status": "healthy",
  "message": "服务运行正常"
}
```

### 3. 获取解析模式（调试的时候，使用精确模式，有利于测试服务器压力）

**GET** `/modes`

获取所有可用的解析模式及其描述。

**响应示例**:
```json
{
  "available_modes": {
    "speed": {
      "name": "极速模式",
      "description": "解析速度快，适合大批量文档处理"
    },
    "accuracy": {
      "name": "精确模式", 
      "description": "解析效果准确，适合高质量文档处理"
    },
    "balanced": {
      "name": "均衡模式",
      "description": "兼顾准确性和解析速度，适合日常使用"
    }
  }
}
```

### 4. 文档解析

**POST** `/parse`

解析文档内容，支持三种输入方式：
1. 本地文件路径
2. URL链接
3. base64编码内容

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| document | string | 是 | 文档内容，可以是本地文件路径、URL或base64编码 |
| parse_mode | string | 否 | 解析模式，默认为"balanced" |
| document_type | string | 否 | 文档类型，如果不指定则自动检测 |
| include_raw_result | boolean | 否 | 是否返回详细的原始解析结果，默认为false |

**请求示例**:

```json
{
  "document": "/path/to/document.pdf",
  "parse_mode": "balanced",
  "document_type": "pdf",
  "include_raw_result": false
}
```

**响应示例**:

成功响应:
```json
{
  "success": true,
  "document_type": "pdf",
  "parse_mode": "balanced",
  "parse_method": "auto",
  "text_content": "解析后的文档内容...",
  "metadata": {
    "file_size": 1024000,
    "page_count": 10
  },
  "raw_result": null,
  "error": null,
  "processing_time": 2.5
}
```

失败响应:
```json
{
  "success": false,
  "document_type": "pdf",
  "parse_mode": "balanced", 
  "parse_method": "none",
  "text_content": "",
  "metadata": {},
  "raw_result": null,
  "error": "文件不存在: /path/to/document.pdf",
  "processing_time": 0.1
}
```

### 5. 文件上传解析

**POST** `/parse/upload`

直接上传文件进行解析。

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file | file | 是 | 上传的文件 |
| parse_mode | string | 否 | 解析模式，默认为"balanced" |
| include_raw_result | boolean | 否 | 是否返回详细的原始解析结果，默认为false |

**请求示例** (multipart/form-data):

```
Content-Type: multipart/form-data

file: [文件内容]
parse_mode: balanced
include_raw_result: false
```

**响应格式**: 与 `/parse` 接口相同

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": "错误描述信息",
  "error_code": "错误代码"
}
```

### 常见错误代码

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| HTTP_400 | 400 | 请求参数错误 |
| HTTP_404 | 404 | 文件不存在 |
| HTTP_413 | 413 | 文件过大（超过20MB） |
| HTTP_500 | 500 | 内部服务器错误 |
| INTERNAL_ERROR | 500 | 未处理的异常 |

## 使用示例

### Python客户端示例

```python
import requests
import base64

# 创建API客户端
api_url = "http://localhost:8000"

# 1. 健康检查
response = requests.get(f"{api_url}/health")
print(response.json())

# 2. 获取解析模式
response = requests.get(f"{api_url}/modes")
print(response.json())

# 3. 解析本地文件
data = {
    "document": "/path/to/document.pdf",
    "parse_mode": "balanced"
}
response = requests.post(f"{api_url}/parse", json=data)
print(response.json())

# 4. 解析URL文档
data = {
    "document": "https://example.com/document.pdf",
    "parse_mode": "accuracy"
}
response = requests.post(f"{api_url}/parse", json=data)
print(response.json())

# 5. 解析base64内容
with open("document.pdf", "rb") as f:
    base64_content = base64.b64encode(f.read()).decode('utf-8')

data = {
    "document": base64_content,
    "parse_mode": "speed"
}
response = requests.post(f"{api_url}/parse", json=data)
print(response.json())

# 6. 上传文件解析
with open("document.pdf", "rb") as f:
    files = {'file': f}
    data = {'parse_mode': 'balanced'}
    response = requests.post(f"{api_url}/parse/upload", files=files, data=data)
    print(response.json())
```

### cURL示例

```bash
# 健康检查
curl -X GET "http://localhost:8000/health"

# 获取解析模式
curl -X GET "http://localhost:8000/modes"

# 解析本地文件
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "document": "/path/to/document.pdf",
    "parse_mode": "balanced"
  }'

# 解析URL文档
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "document": "https://example.com/document.pdf",
    "parse_mode": "accuracy"
  }'

# 上传文件解析
curl -X POST "http://localhost:8000/parse/upload" \
  -F "file=@document.pdf" \
  -F "parse_mode=balanced"
```

## 配置说明

### 服务配置

服务启动时可以通过命令行参数进行配置：

```bash
python api_server.py --host 0.0.0.0 --port 8000 --reload
```

**参数说明**:
- `--host`: 服务主机地址，默认为 `0.0.0.0`
- `--port`: 服务端口，默认为 `8000`
- `--reload`: 开发模式，自动重载，默认为 `False`

### 配置文件 (config.json)

```json
{
  "structure_ocr_server_url": "http://10.249.238.110:8080/layout-parsing",
  "general_ocr_server_url": "http://10.249.238.110:8081/ocr",
  "temp_directory": "./temp",
  "save_results": {
    "enabled": true,
    "save_raw_results": true,
    "save_processed_results": true,
    "save_images": true,
    "results_directory": "results"
  }
}
```

**配置项说明**:
- `structure_ocr_server_url`: 结构化OCR服务地址
- `general_ocr_server_url`: 通用OCR服务地址
- `temp_directory`: 临时文件存储目录
- `save_results`: 结果保存配置

## 性能说明

### 文件大小限制

- 最大文件大小: 20MB
- 建议文件大小: 小于10MB以获得最佳性能

### 处理时间参考

| 文档类型 | 文件大小 | 极速模式 | 均衡模式 | 精确模式 |
|---------|---------|---------|---------|---------|
| PDF | 1MB | 0.5-1s | 1-2s | 2-5s |
| Word | 1MB | 0.2-0.5s | 0.3-0.8s | 0.5-1s |
| PowerPoint | 1MB | 0.3-0.8s | 0.5-1.2s | 0.8-2s |
| 图片 | 1MB | 1-3s | 2-5s | 3-8s |
| 文本 | 1MB | 0.1-0.3s | 0.1-0.3s | 0.1-0.3s |

*注: 实际处理时间可能因文档复杂度、服务器性能等因素而有所差异*

## 注意事项

1. **服务依赖**: 确保OCR服务正常运行
2. **临时文件**: 服务会自动清理临时文件
3. **并发限制**: 建议控制并发请求数量以避免服务器过载
4. **错误重试**: 建议实现适当的错误重试机制
5. **文件格式**: 确保上传的文件格式正确且未损坏

## 技术支持

如有问题或建议，请联系开发团队。

---

*文档版本: 1.0.0*  
*最后更新: 2024年*
