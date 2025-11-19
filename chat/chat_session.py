import sys

sys.path.append('./')
import json
import uuid
import time
from mysql_utils.mysql_helper import *
import logging

logger = logging.getLogger(__name__)


class ChatState:
    def __init__(self):
        self.round = 0
        self.user_question = ''
        self.context_question = ''
        self.reply = ''
        self.reply_type = ''
        self.recommend_questions = []
        self.reply_reference = []

    def serialize(self):
        attr_dic = vars(self)
        res_str = json.dumps(attr_dic, ensure_ascii=False, indent=2)
        return res_str

    def deserialize(self, state_str):
        dic = json.loads(state_str)
        for k, v in dic.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)


class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.chat_state_history: list[ChatState] = []

    def serialize(self):

        def default_serializer(obj):
            if isinstance(obj, ChatState):
                return obj.__dict__
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        attr_dic = vars(self)
        res_str = json.dumps(attr_dic, ensure_ascii=False, indent=2, default=default_serializer)
        return res_str

    def deserialize(self, state_str):
        dic = json.loads(state_str)
        for k, v in dic.items():
            if k == 'chat_state_history':
                for jb in v:
                    cs = ChatState()
                    cs.deserialize(json.dumps(jb))
                    self.chat_state_history.append(cs)
            else:
                setattr(self, k, v)


class ChatSessionManager:
    def __init__(self):
        self.session_dic = {}

    def generate_session_id(self):
        timestamp = str(int(time.time() * 1000))  # 毫秒时间戳
        unique_id = str(uuid.uuid4())  # 生成UUID
        session_id = f"{timestamp}-{unique_id}"
        return session_id

    ##主要在session_dic中增加一个槽位方session，如果已经有槽位了，直接返回。如果没有，就看数据库有没有，有的话放到槽位；数据库也没有就初始化一个
    def add_session(self, session_id):
        if session_id in self.session_dic:
            print(f"session already exists: {session_id}",flush=True)
        else:
            conversation, chat_session_str = SQLDatabase().get_conversation(session_id=session_id)
            if conversation:
                chat_session = ChatSession(session_id)
                chat_session.deserialize(chat_session_str)
                self.session_dic[session_id] = chat_session
                print(f"add session from mysql: {session_id}",flush=True)
            else:
                self.session_dic[session_id] = ChatSession(session_id)
                print(f"add new session: {session_id}",flush=True)

    def get_session(self, session_id) -> ChatSession:
        return self.session_dic.get(session_id, None)

    def session_exist(self, session_id):
        if session_id in self.session_dic:
            return True
        else:
            return False

    def get_last_round(self, session_id):
        last_round = 0
        cur_session = self.get_session(session_id)
        if cur_session and cur_session.chat_state_history:
            last_round = cur_session.chat_state_history[-1].round
        return last_round

    def get_history(self, session_id):
        history = []
        cur_session = self.get_session(session_id)
        if cur_session and cur_session.chat_state_history:
            for chatstat in cur_session.chat_state_history:
                #print(f'=====>chatstat={chatstat},{type(chatstat)}')
                history.append((chatstat.user_question, chatstat.reply))
        print(f'=====>get history={history}',flush=True)
        return history

    def update_last_reply_to_chat_state(self, session_id, final_answer):
        if self.get_session(session_id).chat_state_history:
            self.get_session(session_id).chat_state_history[-1].reply = final_answer

    def save_session_to_db(self, session_id: str, tenant_code: str, user_id: str):
        chat_session = self.session_dic.get(session_id, None)
        if chat_session:
            chat_session_str = chat_session.serialize()
            SQLDatabase().save_conversation(session_id=session_id, tenant_code=tenant_code, user_id=user_id,
                                            chat_session=chat_session_str)
            print(f'save chat session to mysql completed。{session_id}',flush=True)

    def remove_session(self, session_id):
        if session_id in self.session_dic:
            self.session_dic.pop(session_id, None)

