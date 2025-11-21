# -*- coding: utf-8 -*-
"""
AI助手主服务
同时启动向量数据库服务和对话问答服务
"""
import logging
import json
import threading
import time
from flask import Flask

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)


def run_vector_db_server():
    """运行向量数据库服务"""
    try:
        from vector_db_server import app as vector_app
        server_config = config.get('milvus_api_server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8005)
        
        logger.info(f"向量数据库服务启动，监听地址: {host}:{port}")
        vector_app.run(host=host, port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"向量数据库服务启动失败: {e}")
        import traceback
        logger.exception(traceback.format_exc())


def run_chat_server():
    """运行对话问答服务"""
    try:
        from chat_server import app as chat_app
        server_config = config.get('chat_api_server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8006)
        
        logger.info(f"对话问答服务启动，监听地址: {host}:{port}")
        chat_app.run(host=host, port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"对话问答服务启动失败: {e}")
        import traceback
        logger.exception(traceback.format_exc())


def main():
    """主函数：启动两个服务"""
    logger.info("=" * 60)
    logger.info("AI助手主服务启动")
    logger.info("=" * 60)
    
    # 初始化向量库（如果需要）
    try:
        logger.info("初始化向量库...")
        from milvus.miluvs_helper import create_collection
        is_succ, msg = create_collection()
        if is_succ:
            logger.info(f"向量库初始化成功: {msg}")
        else:
            logger.warning(f"向量库初始化失败: {msg}")
    except Exception as e:
        logger.warning(f"向量库初始化异常（可能已存在）: {e}")
    
    # 初始化MySQL表（如果需要）
    try:
        logger.info("初始化MySQL表...")
        from mysql_utils.mysql_helper import MySQLHelper
        mysql_helper = MySQLHelper()
        is_succ, msg = mysql_helper.create_tables()
        if is_succ:
            logger.info(f"MySQL表初始化成功: {msg}")
        else:
            logger.warning(f"MySQL表初始化失败: {msg}")
        mysql_helper.close()
    except Exception as e:
        logger.warning(f"MySQL表初始化异常: {e}")
    
    # 创建并启动向量数据库服务线程
    vector_thread = threading.Thread(target=run_vector_db_server, daemon=True)
    vector_thread.start()
    logger.info("向量数据库服务线程已启动")
    
    # 等待一下确保第一个服务启动
    time.sleep(2)
    
    # 创建并启动对话问答服务线程
    chat_thread = threading.Thread(target=run_chat_server, daemon=True)
    chat_thread.start()
    logger.info("对话问答服务线程已启动")
    
    logger.info("=" * 60)
    logger.info("所有服务已启动")
    logger.info("向量数据库服务: http://0.0.0.0:8005")
    logger.info("对话问答服务: http://0.0.0.0:8006")
    logger.info("=" * 60)
    
    # 主线程保持运行
    try:
        while True:
            time.sleep(1)
            # 检查线程是否还在运行
            if not vector_thread.is_alive():
                logger.error("向量数据库服务线程已停止")
                break
            if not chat_thread.is_alive():
                logger.error("对话问答服务线程已停止")
                break
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"主服务运行异常: {e}")
        import traceback
        logger.exception(traceback.format_exc())


if __name__ == '__main__':
    main()

