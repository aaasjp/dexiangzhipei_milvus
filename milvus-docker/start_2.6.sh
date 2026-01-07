#!/bin/bash

# 设置卷目录，如果环境变量未设置，则使用当前目录
VOLUME_DIR=${DOCKER_VOLUME_DIRECTORY:-$(pwd)}

# 创建 Docker 网络（如果不存在）
docker network create milvus 2>/dev/null || true

# 启动 etcd 服务
echo "启动 etcd 服务..."
docker run -d \
  --name milvus-etcd \
  --network milvus \
  -e ETCD_AUTO_COMPACTION_MODE=revision \
  -e ETCD_AUTO_COMPACTION_RETENTION=1000 \
  -e ETCD_QUOTA_BACKEND_BYTES=4294967296 \
  -e ETCD_SNAPSHOT_COUNT=50000 \
  -v ${VOLUME_DIR}/volumes/etcd:/etcd \
  --health-cmd="etcdctl endpoint health" \
  --health-interval=30s \
  --health-timeout=20s \
  --health-retries=3 \
  quay.io/coreos/etcd:v3.5.18 \
  etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

# 等待 etcd 启动
echo "等待 etcd 启动..."
sleep 5

# 启动 minio 服务
echo "启动 minio 服务..."
docker run -d \
  --name milvus-minio \
  --network milvus \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \
  -p 9001:9001 \
  -p 9000:9000 \
  -v ${VOLUME_DIR}/volumes/minio:/minio_data \
  --health-cmd="curl -f http://localhost:9000/minio/health/live" \
  --health-interval=30s \
  --health-timeout=20s \
  --health-retries=3 \
  minio/minio:RELEASE.2024-12-18T13-15-44Z \
  server /minio_data --console-address ":9001"

# 等待 minio 启动
echo "等待 minio 启动..."
sleep 5

# 启动 milvus standalone 服务
echo "启动 milvus standalone 服务..."
docker run -d \
  --name milvus-standalone \
  --network milvus \
  --security-opt seccomp=unconfined \
  -e ETCD_ENDPOINTS=etcd:2379 \
  -e MINIO_ADDRESS=minio:9000 \
  -e MQ_TYPE=woodpecker \
  -p 19530:19530 \
  -p 9091:9091 \
  -v ${VOLUME_DIR}/volumes/milvus:/var/lib/milvus \
  --health-cmd="curl -f http://localhost:9091/healthz" \
  --health-interval=30s \
  --health-start-period=90s \
  --health-timeout=20s \
  --health-retries=3 \
  milvusdb/milvus:v2.6.6 \
  milvus run standalone

echo "所有服务启动完成！"
echo "etcd: 运行中"
echo "minio: http://localhost:9001 (控制台), http://localhost:9000 (API)"
echo "milvus: localhost:19530"

