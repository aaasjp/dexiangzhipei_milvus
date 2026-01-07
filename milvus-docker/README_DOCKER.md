# 使用 Docker 命令启动 Milvus 服务

本目录提供了两种方式启动 Milvus 服务：
1. 使用启动脚本（推荐）
2. 手动执行 Docker 命令

## 方式一：使用启动脚本（推荐）

### 启动服务
```bash
cd milvus-docker
./start.sh
```

### 停止服务
```bash
./stop.sh
```

## 方式二：手动执行 Docker 命令

### 1. 创建网络
```bash
docker network create milvus
```

### 2. 启动 etcd 服务
```bash
docker run -d \
  --name milvus-etcd \
  --network milvus \
  -e ETCD_AUTO_COMPACTION_MODE=revision \
  -e ETCD_AUTO_COMPACTION_RETENTION=1000 \
  -e ETCD_QUOTA_BACKEND_BYTES=4294967296 \
  -e ETCD_SNAPSHOT_COUNT=50000 \
  -v $(pwd)/volumes/etcd:/etcd \
  --health-cmd="etcdctl endpoint health" \
  --health-interval=30s \
  --health-timeout=20s \
  --health-retries=3 \
  quay.io/coreos/etcd:v3.5.18 \
  etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
```

### 3. 启动 minio 服务
```bash
docker run -d \
  --name milvus-minio \
  --network milvus \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \
  -p 9001:9001 \
  -p 9000:9000 \
  -v $(pwd)/volumes/minio:/minio_data \
  --health-cmd="curl -f http://localhost:9000/minio/health/live" \
  --health-interval=30s \
  --health-timeout=20s \
  --health-retries=3 \
  minio/minio:RELEASE.2024-12-18T13-15-44Z \
  server /minio_data --console-address ":9001"
```

### 4. 启动 milvus standalone 服务
```bash
docker run -d \
  --name milvus-standalone \
  --network milvus \
  --security-opt seccomp=unconfined \
  -e ETCD_ENDPOINTS=etcd:2379 \
  -e MINIO_ADDRESS=minio:9000 \
  -e MQ_TYPE=woodpecker \
  -p 19530:19530 \
  -p 9091:9091 \
  -v $(pwd)/volumes/milvus:/var/lib/milvus \
  --health-cmd="curl -f http://localhost:9091/healthz" \
  --health-interval=30s \
  --health-start-period=90s \
  --health-timeout=20s \
  --health-retries=3 \
  milvusdb/milvus:v2.6.6 \
  milvus run standalone
```

### 停止服务
```bash
docker stop milvus-standalone milvus-minio milvus-etcd
docker rm milvus-standalone milvus-minio milvus-etcd
```

## 环境变量

如果需要自定义卷目录位置，可以设置环境变量：
```bash
export DOCKER_VOLUME_DIRECTORY=/path/to/volumes
./start.sh
```

## 服务端口

- **etcd**: 内部使用，不对外暴露端口
- **minio**: 
  - 9000: API 端口
  - 9001: 控制台端口
- **milvus**: 
  - 19530: Milvus 服务端口
  - 9091: 健康检查端口

## 访问地址

- MinIO 控制台: http://localhost:9001
- MinIO API: http://localhost:9000
- Milvus: localhost:19530

