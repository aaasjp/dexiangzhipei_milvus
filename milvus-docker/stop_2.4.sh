#!/bin/bash

echo "停止所有服务..."

# 停止并删除容器
docker stop milvus-standalone 2>/dev/null || true
docker rm milvus-standalone 2>/dev/null || true

docker stop milvus-minio 2>/dev/null || true
docker rm milvus-minio 2>/dev/null || true

docker stop milvus-etcd 2>/dev/null || true
docker rm milvus-etcd 2>/dev/null || true

# 可选：删除网络（如果不再需要）
# docker network rm milvus 2>/dev/null || true

echo "所有服务已停止！"

