import json
import logging

# logging.basicConfig(filename='logs/app_chat_server.log', encoding='utf-8', level=logging.INFO,
#                    format='%(asctime)s - %(filename)s - %(funcName)s - %(levelname)s - %(message)s',
#                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_cors import CORS
from utils.auth_check import *
from chat.chat_uitls import *
from llm.llm_service import *

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

##加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)


@app.route('/')
def index():
    return 'hello ai world!'


'''
@app.route('/generate_session_id', methods=['POST'])
def generate_session_id():
    data = request.get_json()
    api_key = data.get('api_key', None)
    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})
    session_id = chat_session_manager.generate_session_id()
    return jsonify({'status': 'success', 'code': 200, 'msg': '生成session_id成功', 'data': session_id})
'''


@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    #send(f'====>客户端已经链接。session_id={session_id},room={session_id}')
    logger.info(f'客户端已连接, session_id={session_id}, room={session_id}')
    chat_session_manager.add_session(session_id)
    emit('session_id', {'session_id': session_id, "room": session_id})



@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    logger.info(f'移除session: {session_id}')
    chat_session_manager.remove_session(session_id)
    #send(f'====>客户端链接已断开.session_id={session_id}')
    logger.info(f'客户端连接已断开, session_id={session_id}')


@socketio.on('join')
def handle_join(data):
    session_id = request.sid
    room = data.get('room', None)
    user_id = data.get('user_id', None)
    logger.info(f'加入房间: session_id={session_id}, room={room}, user_id={user_id}')

    if not room:
        logger.error('room must required!')
        raise ValueError('room must required!')
    join_room(room)
    #send(f'{user_id} has entered the room = {room}.', to=room)
    logger.info(f'{user_id} 已进入房间 {room}')



@socketio.on('leave')
def handle_leave(data):
    session_id = request.sid
    room = data.get('room', None)
    user_id = data.get('user_id', None)
    if not room:
        logger.error('room must required!')
        raise ValueError('room must required!')
    leave_room(room)
    #send(f'===>>leave room: session_id={session_id},room={room}, user_id={user_id}', to=room)
    logger.info(f'离开房间: session_id={session_id}, room={room}, user_id={user_id}')


@socketio.on('chat')
def handle_chat(data):
    logger.info(f'开始聊天: {data}')
    data["session_id"]=request.sid
    socketio.start_background_task(target=send_message(data))


def send_message(data):
    if type(data) == str:
        data = json.loads(data)
    prompt = data.get("prompt", None)
    history = data.get("history", [])
    session_id = data.get("session_id")
    room = data.get("room")
    user_id = data.get("user_id", None)
    tenant_code = data.get("tenant_code", None)
    collection_name = data.get("collection_name", None)
    chat_effect_params = config['chat_effect_param']
    stream = True

    assert prompt is not None
    assert session_id is not None
    assert user_id is not None
    assert tenant_code is not None
    assert collection_name is not None
    assert chat_effect_params is not None

    params_dic = {
        'prompt': prompt,
        'history': history,
        'session_id': session_id,
        'tenant_code': tenant_code,
        'collection_name': collection_name,
        'stream': stream,
        'chat_effect_params': chat_effect_params
    }

    response_dict = chat_obj.chat(params_dic)

    response_dict['status'] = 'transferring'
    response_dict['session_id'] = session_id
    response = response_dict['response']

    if type(response) == str:
        socketio.send(response_dict, to=room)
        finally_res = response
    else:
        finally_res = ""
        for res in response:
            response_dict['response'] = res
            finally_res = res
            socketio.send(response_dict, to=room)

    response_dict['status'] = 'finished'
    socketio.send(response_dict, to=room)

    # 一定要记住，在下面实现，当流式输出最后一个的时候，记录到历史对话中！！！
    chat_session_manager.update_last_reply_to_chat_state(session_id, finally_res)

    # session入库
    chat_session_manager.save_session_to_db(session_id=session_id, tenant_code=tenant_code, user_id=user_id)
    return


@app.route('/get_recommend_questions', methods=['POST'])
def get_recommend_questions():
    data = request.get_json()
    session_id = data.get('session_id', None)
    api_key = data.get('api_key', None)
    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not session_id:
        return jsonify({'status': 'fail', 'msg': '缺少session_id', 'code': 400, 'data': ''})

    recommend_questions = []
    chat_session = chat_session_manager.get_session(session_id=session_id)
    if chat_session and chat_session.chat_state_history:
        last_round_chat_state = chat_session.chat_state_history[-1]
        recommend_questions = last_round_chat_state.recommend_questions

    return jsonify({'status': 'success', 'code': 200, 'msg': '获取推荐问题成功', 'data': recommend_questions})


if __name__ == '__main__':
    chat_session_manager = ChatSessionManager()
    llm_serv = LlmService()
    chat_obj = ChatUitls(llm_srv=llm_serv, chat_session_manager=chat_session_manager)

    # app.run(host='0.0.0.0', port=8802)
    socketio.run(app, host='0.0.0.0', port=8802, allow_unsafe_werkzeug=True)
