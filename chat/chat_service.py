# -*- coding: utf-8 -*-
"""
对话管理服务
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from mysql_utils.mysql_helper import MySQLHelper

logger = logging.getLogger(__name__)


class ChatService:
    """对话管理服务类"""
    
    def __init__(self):
        """初始化对话服务"""
        self.mysql_helper = MySQLHelper()
        # 确保表已创建
        self.mysql_helper.create_tables()
    
    def create_session(self, user_id: str, session_id: str, title: Optional[str] = None,
                     tenant_code: Optional[str] = None, org_code: Optional[str] = None) -> tuple:
        """创建新对话会话"""
        return self.mysql_helper.create_session(user_id, session_id, title, tenant_code, org_code)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self.mysql_helper.get_session(session_id)
    
    def list_sessions(self, user_id: str, tenant_code: Optional[str] = None,
                     org_code: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户的会话列表"""
        return self.mysql_helper.list_sessions(user_id, tenant_code, org_code, limit)
    
    def update_session_title(self, session_id: str, title: str) -> tuple:
        """更新会话标题"""
        return self.mysql_helper.update_session_title(session_id, title)
    
    def delete_session(self, session_id: str) -> tuple:
        """删除会话（软删除）"""
        return self.mysql_helper.delete_session(session_id)
    
    def restore_session(self, session_id: str) -> tuple:
        """恢复会话"""
        return self.mysql_helper.restore_session(session_id)
    
    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[Tuple[str, str]]:
        """获取对话历史，返回格式为[(question, answer), ...]"""
        return self.mysql_helper.get_conversation_history(session_id, limit)
    
    def save_message(self, session_id: str, user_id: str, role: str, content: str,
                    sources: Optional[List[Dict]] = None,
                    suggested_questions: Optional[List[str]] = None) -> tuple:
        """保存消息"""
        return self.mysql_helper.add_message(session_id, user_id, role, content, sources, suggested_questions)
    
    def close(self):
        """关闭数据库连接"""
        self.mysql_helper.close()

