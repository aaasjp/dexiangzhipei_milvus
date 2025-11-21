# -*- coding: utf-8 -*-
"""
对话问答服务
"""
import logging
import json
import os
import uuid
from typing import Optional, List, Dict, Any, Generator
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

from llm.llm_service import LlmService
from milvus.miluvs_helper import search_from_collection
from utils.file_loader import extract_content_from_file
from chat.chat_service import ChatService
from minio_utils.minio_client import upload_file

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 初始化服务
llm_service = LlmService()
chat_service = ChatService()
ocr_config = config.get('ocr_service', {})


def generate_suggested_questions(user_question: str, answer: str, llm_service: LlmService) -> List[str]:
    """基于用户问题和回答生成延申问题推荐"""
    try:
        prompt = f"""基于以下用户问题和AI回答，生成3-5个相关的延申问题推荐。要求：
1. 问题应该与用户问题相关，但角度不同或更深入
2. 问题应该简洁明了，每个问题不超过20个字
3. 只返回问题列表，每行一个问题，不要编号，不要其他说明

用户问题：{user_question}

AI回答：{answer[:500]}  # 限制回答长度避免token过多

请生成延申问题："""
        
        response = llm_service.inference(
            prompt=prompt,
            stream=False,
            generate_params={'temperature': 0.7, 'max_tokens': 200}
        )
        
        if isinstance(response, str):
            # 解析返回的问题列表
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            # 过滤掉空问题和过长的问题
            questions = [q for q in questions if len(q) <= 50 and len(q) > 0]
            return questions[:5]  # 最多返回5个
        else:
            return []
    except Exception as e:
        logger.error(f"生成延申问题失败: {e}")
        return []


def format_sources(entities: List[Dict]) -> Dict[str, Any]:
    """格式化文档来源信息"""
    if not entities:
        return {
            'count': 0,
            'documents': []
        }
    
    # 提取唯一的文档来源
    source_map = {}
    for entity in entities:
        source_url = entity.get('source', '')
        file_name = entity.get('file_name') or entity.get('question', '未知文档')
        
        if source_url:
            if source_url not in source_map:
                source_map[source_url] = {
                    'name': file_name,
                    'url': source_url
                }
    
    documents = list(source_map.values())
    return {
        'count': len(documents),
        'documents': documents
    }


@app.route('/chat_service/chat', methods=['POST'])
def chat():
    """问答接口
    
    请求参数：
    - user_id: 用户ID（必填）
    - session_id: 会话ID（可选，不传则创建新会话）
    - question: 用户问题（必填）
    - tenant_code: 租户代码（可选）
    - org_code: 组织代码（可选）
    - use_vector_db: 是否使用向量库（默认true）
    - use_uploaded_doc: 是否使用上传的文档（默认false）
    - uploaded_doc_url: 上传的文档URL（当use_uploaded_doc为true时必填）
    - stream: 是否流式输出（默认true）
    - limit: 检索结果数量（默认5）
    """
    data = request.get_json()
    logger.info(f'问答请求, data={data}')
    
    user_id = data.get('user_id', '')
    session_id = data.get('session_id', '')
    question = data.get('question', '')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    use_vector_db = data.get('use_vector_db', True)
    use_uploaded_doc = data.get('use_uploaded_doc', False)
    uploaded_doc_url = data.get('uploaded_doc_url', '')
    stream = data.get('stream', True)
    limit = data.get('limit', 5)
    
    # 参数验证
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})
    
    # 如果没有session_id，创建新会话
    if not session_id:
        session_id = str(uuid.uuid4())
        is_succ, msg = chat_service.create_session(user_id, session_id, title=question[:50], 
                                                   tenant_code=tenant_code, org_code=org_code)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': f'创建会话失败: {msg}', 'code': 400, 'data': ''})
    
    # 检查会话是否存在
    session = chat_service.get_session(session_id)
    if not session:
        return jsonify({'status': 'fail', 'msg': '会话不存在', 'code': 400, 'data': ''})
    
    # 保存用户问题
    chat_service.save_message(session_id, user_id, 'user', question)
    
    # 获取对话历史
    history = chat_service.get_conversation_history(session_id)
    
    # 构建系统提示词和上下文
    context_parts = []
    sources_info = {'count': 0, 'documents': []}
    
    # 优先使用上传的文档
    if use_uploaded_doc and uploaded_doc_url:
        try:
            is_succ, doc_content = extract_content_from_file(uploaded_doc_url, ocr_config=ocr_config)
            if is_succ and doc_content:
                context_parts.append(f"参考文档内容：\n{doc_content[:3000]}")  # 限制长度
                sources_info = {
                    'count': 1,
                    'documents': [{'name': '用户上传文档', 'url': uploaded_doc_url}]
                }
        except Exception as e:
            logger.error(f"解析上传文档失败: {e}")
    
    # 如果使用向量库检索（且没有使用上传文档）
    elif use_vector_db and not (use_uploaded_doc and uploaded_doc_url):
        try:
            # 构建过滤表达式
            filter_expr = ""
            if tenant_code and org_code:
                filter_expr = f"tenant_code == '{tenant_code}' && org_code == '{org_code}'"
            elif tenant_code:
                filter_expr = f"tenant_code == '{tenant_code}'"
            elif org_code:
                filter_expr = f"org_code == '{org_code}'"
            
            # 先搜索QA集合（不传tenant_code和org_code则使用全部向量知识库）
            qa_results = search_from_collection(
                tenant_code=tenant_code if tenant_code else '',
                org_code=org_code if org_code else '',
                collection_type='QA',
                query_list=[question],
                filter_expr=filter_expr if filter_expr else '',
                limit=limit,
                use_hybrid=True  # 使用BM25+向量检索
            )
            
            # 再搜索DOC集合（不传tenant_code和org_code则使用全部向量知识库）
            doc_results = search_from_collection(
                tenant_code=tenant_code if tenant_code else '',
                org_code=org_code if org_code else '',
                collection_type='DOC',
                query_list=[question],
                filter_expr=filter_expr if filter_expr else '',
                limit=limit,
                use_hybrid=True
            )
            
            # 合并结果
            all_entities = []
            if isinstance(qa_results, dict) and qa_results.get('entities'):
                all_entities.extend(qa_results['entities'][0] if qa_results['entities'] else [])
            if isinstance(doc_results, dict) and doc_results.get('entities'):
                all_entities.extend(doc_results['entities'][0] if doc_results['entities'] else [])
            
            # 格式化来源信息
            sources_info = format_sources(all_entities)
            
            # 构建上下文
            if all_entities:
                context_texts = []
                for entity in all_entities[:limit]:
                    if 'answer' in entity:
                        # QA类型
                        context_texts.append(f"问题：{entity.get('question', '')}\n答案：{entity.get('answer', '')}")
                    elif 'content' in entity:
                        # DOC类型
                        context_texts.append(f"文档内容：{entity.get('content', '')}")
                
                if context_texts:
                    context_parts.append("参考知识库内容：\n" + "\n\n".join(context_texts))
        
        except Exception as e:
            logger.error(f"向量库检索失败: {e}")
            import traceback
            logger.exception(traceback.format_exc())
    
    # 构建系统提示词
    system_prompt = """你是一个专业的AI助手，能够基于提供的知识库内容回答用户问题。
如果知识库中有相关内容，请基于知识库内容回答；如果没有相关内容，可以使用你的通用知识回答。
回答要准确、简洁、有条理。"""
    
    if context_parts:
        system_prompt += "\n\n" + "\n\n".join(context_parts)
    
    # 调用LLM生成回答
    try:
        if stream:
            # 流式输出
            def generate():
                full_answer = ""
                try:
                    response_generator = llm_service.inference(
                        prompt=question,
                        system=system_prompt,
                        history=history,
                        stream=True
                    )
                    
                    for chunk in response_generator:
                        full_answer = chunk
                        yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    
                    # 生成延申问题
                    suggested_questions = generate_suggested_questions(question, full_answer, llm_service)
                    
                    # 保存完整回答（包含延申问题）
                    chat_service.save_message(session_id, user_id, 'assistant', full_answer,
                                             sources=sources_info.get('documents', []),
                                             suggested_questions=suggested_questions)
                    
                    # 返回最终结果
                    final_data = {
                        'content': full_answer,
                        'done': True,
                        'sources': sources_info,
                        'suggested_questions': suggested_questions
                    }
                    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
                except Exception as e:
                    logger.error(f"流式生成回答失败: {e}")
                    import traceback
                    error_msg = traceback.format_exc()
                    yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
            
            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
        else:
            # 非流式输出
            response = llm_service.inference(
                prompt=question,
                system=system_prompt,
                history=history,
                stream=False
            )
            
            answer = response if isinstance(response, str) else ""
            
            # 生成延申问题
            suggested_questions = generate_suggested_questions(question, answer, llm_service)
            
            # 保存回答
            chat_service.save_message(session_id, user_id, 'assistant', answer,
                                     sources=sources_info.get('documents', []),
                                     suggested_questions=suggested_questions)
            
            return jsonify({
                'status': 'success',
                'code': 200,
                'msg': '问答成功',
                'data': {
                    'session_id': session_id,
                    'answer': answer,
                    'sources': sources_info,
                    'suggested_questions': suggested_questions
                }
            })
    
    except Exception as e:
        logger.error(f"生成回答失败: {e}")
        import traceback
        return jsonify({
            'status': 'fail',
            'msg': f'生成回答失败: {traceback.format_exc()}',
            'code': 500,
            'data': ''
        })


@app.route('/chat_service/sessions', methods=['GET'])
def list_sessions():
    """获取会话列表"""
    user_id = request.args.get('user_id', '')
    tenant_code = request.args.get('tenant_code', '')
    org_code = request.args.get('org_code', '')
    limit = int(request.args.get('limit', 50))
    
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    sessions = chat_service.list_sessions(user_id, tenant_code, org_code, limit)
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取会话列表成功',
        'data': sessions
    })


@app.route('/chat_service/session', methods=['POST'])
def create_session():
    """创建新会话"""
    data = request.get_json()
    user_id = data.get('user_id', '')
    session_id = data.get('session_id', '')
    title = data.get('title', '')
    tenant_code = data.get('tenant_code', '')
    org_code = data.get('org_code', '')
    
    if not user_id:
        return jsonify({'status': 'fail', 'msg': '缺少用户ID', 'code': 400, 'data': ''})
    
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    
    is_succ, msg = chat_service.create_session(user_id, session_id, title, tenant_code, org_code)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '创建会话成功',
        'data': {'session_id': session_id}
    })


@app.route('/chat_service/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话信息"""
    session = chat_service.get_session(session_id)
    if not session:
        return jsonify({'status': 'fail', 'msg': '会话不存在', 'code': 404, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取会话成功',
        'data': session
    })


@app.route('/chat_service/session/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """获取会话消息历史"""
    limit = int(request.args.get('limit', 100))
    
    from mysql_utils.mysql_helper import MySQLHelper
    mysql_helper = MySQLHelper()
    messages = mysql_helper.get_messages(session_id, limit)
    mysql_helper.close()
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '获取消息历史成功',
        'data': messages
    })


@app.route('/chat_service/session/<session_id>/title', methods=['PUT'])
def update_session_title(session_id):
    """更新会话标题"""
    data = request.get_json()
    title = data.get('title', '')
    
    if not title:
        return jsonify({'status': 'fail', 'msg': '缺少标题参数', 'code': 400, 'data': ''})
    
    is_succ, msg = chat_service.update_session_title(session_id, title)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '更新标题成功',
        'data': ''
    })


@app.route('/chat_service/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    is_succ, msg = chat_service.delete_session(session_id)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '删除会话成功',
        'data': ''
    })


@app.route('/chat_service/session/<session_id>/restore', methods=['POST'])
def restore_session(session_id):
    """恢复会话"""
    is_succ, msg = chat_service.restore_session(session_id)
    if not is_succ:
        return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    
    return jsonify({
        'status': 'success',
        'code': 200,
        'msg': '恢复会话成功',
        'data': ''
    })


@app.route('/chat_service/upload', methods=['POST'])
def upload_document():
    """上传文档到MinIO"""
    if 'file' not in request.files:
        return jsonify({'status': 'fail', 'msg': '缺少文件', 'code': 400, 'data': ''})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'fail', 'msg': '文件名为空', 'code': 400, 'data': ''})
    
    try:
        # 读取文件数据
        file_data = file.read()
        file_name = file.filename
        
        # 获取文件MIME类型
        content_type = file.content_type or 'application/octet-stream'
        
        # 上传到MinIO
        file_url = upload_file(file_data, file_name, content_type)
        
        return jsonify({
            'status': 'success',
            'code': 200,
            'msg': '上传成功',
            'data': {
                'file_url': file_url,
                'file_name': file_name
            }
        })
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        import traceback
        return jsonify({
            'status': 'fail',
            'msg': f'上传失败: {traceback.format_exc()}',
            'code': 500,
            'data': ''
        })


if __name__ == '__main__':
    server_config = config.get('chat_api_server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8006)
    logger.info(f"对话问答服务启动，监听地址: {host}:{port}")
    app.run(host=host, port=port)

