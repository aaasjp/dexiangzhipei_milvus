import logging
#logging.basicConfig(filename='logs/vector_db_server.log', encoding='utf-8', level=logging.INFO,
#                   format='%(asctime)s - %(filename)s - %(funcName)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

import os
import json
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from milvus.miluvs_helper import *
from utils.auth_check import *
from utils.file_loader import *
from mysql_utils.mysql_helper import *



app = Flask(__name__)

##加载配置文件
with open('./config/config.json', 'r') as f:
    config = json.load(f)


@app.route('/')
def index():
    return 'Hello, World!'


@app.route('/vector_db_service/new_collection', methods=['POST'])
def new_collection():
    data = request.get_json()
    print(f'====>new_collection(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = create_collection(tenant_code, collection_name)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception as e:
        import traceback
        logger.exception(f"创建向量库[{collection_name}]异常:：%s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功创建向量库', 'data': ''})


@app.route('/vector_db_service/del_collection', methods=['POST'])
def del_collection():
    data = request.get_json()
    print(f'====>del_collection(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = delete_collection(tenant_code, collection_name)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"删除向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功删除向量库', 'data': ''})


@app.route('/vector_db_service/add_qa', methods=['POST'])
def add_qa():
    data = request.get_json()
    print(f'====>add_qa(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', '')
    answer = data.get('answer', '')
    source = data.get('source', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    if not answer:
        return jsonify({'status': 'fail', 'msg': '缺少答案参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = insert_qa_to_collection(tenant_code, collection_name, question_list=[question.strip()],
                                               answer_list=[answer], source_list=[source], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入问答对到向量库', 'data': ''})


@app.route('/vector_db_service/add_qa_from_template', methods=['POST'])
def add_qa_from_template():
    data = request.get_json()
    print(f'====>add_qa_from_template(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    template_file_path = data.get('template_path', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not template_file_path:
        return jsonify({'status': 'fail', 'msg': '缺少模版文件路径参数', 'code': 400, 'data': ''})

    if not os.path.exists(template_file_path):
        logger.error(f"{template_file_path}模版文件不存在")
        return jsonify({'status': 'fail', 'msg': f"{template_file_path}模版文件不存在", 'code': 400, 'data': ''})

    question_list, answers_list, source_list = load_qa_template(template_file_path)
    metadata_list = [{} for q in question_list]
    try:
        is_succ, msg = insert_qa_to_collection(tenant_code, collection_name, question_list=question_list,
                                               answer_list=answers_list, source_list=source_list,
                                               metadata_list=metadata_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入问答对到向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入问答对到向量库', 'data': ''})


@app.route('/vector_db_service/add_document', methods=['POST'])
def add_document():
    data = request.get_json()
    print(f'====>add_document(),data={data}',flush=True)
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    doc_url = data.get('doc_url', '')
    doc_name = data.get('doc_name', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not doc_url:
        return jsonify({'status': 'fail', 'msg': '缺少文档URL参数', 'code': 400, 'data': ''})

    if not doc_name:
        return jsonify({'status': 'fail', 'msg': '缺少文档名称参数', 'code': 400, 'data': ''})

    # 验证URL格式
    try:
        parsed_url = urlparse(doc_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return jsonify({'status': 'fail', 'msg': '文档URL格式不正确', 'code': 400, 'data': ''})
    except Exception as e:
        return jsonify({'status': 'fail', 'msg': f'文档URL格式验证失败: {repr(e)}', 'code': 400, 'data': ''})

    # 从配置读取OCR配置
    ocr_config = config.get('ocr_service', {})
    is_succ, content = extract_content_from_file(doc_url, ocr_config=ocr_config)
    if not is_succ:
        logger.error(f"解析文档失败:{content}")
        return jsonify({'status': 'fail', 'msg': f"解析文档失败:{content}", 'code': 400, 'data': ''})

    try:
        is_succ, msg = insert_docs_to_collection(tenant_code, collection_name, doc_name_list=[doc_name.strip()],
                                                 doc_content_list=[content], source_list=[doc_url], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"插入文档到向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功插入文档到向量库', 'data': ''})


@app.route('/vector_db_service/add_multi_document', methods=['POST'])
def add_multi_document():
    data = request.get_json()
    print(f'====>add_multi_document(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    multi_doc_urls = data.get('multi_doc_urls', [])
    doc_names = data.get('doc_names', [])

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not multi_doc_urls or not isinstance(multi_doc_urls, list):
        return jsonify({'status': 'fail', 'msg': '缺少文档URL列表参数或格式不正确', 'code': 400, 'data': ''})

    if len(multi_doc_urls) == 0:
        return jsonify({'status': 'fail', 'msg': '文档URL列表为空', 'code': 400, 'data': ''})

    if not doc_names or not isinstance(doc_names, list):
        return jsonify({'status': 'fail', 'msg': '缺少文档名称列表参数或格式不正确', 'code': 400, 'data': ''})

    if len(doc_names) != len(multi_doc_urls):
        return jsonify({'status': 'fail', 'msg': f'文档名称列表长度({len(doc_names)})与文档URL列表长度({len(multi_doc_urls)})不一致', 'code': 400, 'data': ''})

    # 从配置读取OCR配置
    ocr_config = config.get('ocr_service', {})
    
    success_count = 0
    failed_count = 0
    for idx, doc_url in enumerate(multi_doc_urls):
        try:
            # 验证URL格式
            try:
                parsed_url = urlparse(doc_url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    logger.error(f"文档URL格式不正确: {doc_url}")
                    failed_count += 1
                    continue
            except Exception as e:
                logger.error(f"文档URL格式验证失败: {doc_url}, 错误: {repr(e)}")
                failed_count += 1
                continue
            
            is_succ, content = extract_content_from_file(doc_url, ocr_config=ocr_config)
            if not is_succ:
                logger.error(f"解析文档[{doc_url}]失败:{content}")
                failed_count += 1
                continue
            
            # 从请求参数中获取文档名称
            doc_name = doc_names[idx].strip() if idx < len(doc_names) else ''
            if not doc_name:
                logger.error(f"文档名称为空，索引: {idx}")
                failed_count += 1
                continue
            
            is_succ, msg = insert_docs_to_collection(tenant_code, collection_name, doc_name_list=[doc_name],
                                                     doc_content_list=[content], source_list=[doc_url],
                                                     metadata_list=[{}])
            if not is_succ:
                logger.error(f"插入文档[{doc_url}]到向量库[{collection_name}]失败:{msg}")
                failed_count += 1
                continue
            success_count += 1
        except Exception:
            import traceback
            logger.exception(f"插入文档[{doc_url}]到向量库[{collection_name}]异常: %s", traceback.format_exc())
            failed_count += 1
            continue
    
    if failed_count > 0:
        return jsonify({'status': 'fail', 'code': 400,
                        'msg': f'插入文档到向量库[{collection_name}]：成功[{success_count}]个,失败[{failed_count}]个', 'data': ''})
    return jsonify({'status': 'success', 'code': 200, 'msg': f'插入文档到向量库[{collection_name}]成功', 'data': ''})


@app.route('/vector_db_service/update_qa', methods=['POST'])
def update_qa():
    data = request.get_json()
    print(f'====>update_qa(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', '')
    answer = data.get('answer', '')
    source = data.get('source', '')

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    if not answer:
        return jsonify({'status': 'fail', 'msg': '缺少答案参数', 'code': 400, 'data': ''})

    try:
        is_succ, msg = upsert_qa_to_collection(tenant_code, collection_name, question_list=[question],
                                               answer_list=[answer], source_list=[source], metadata_list=[{}])
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"更新向量库[{collection_name}]异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '成功更新问答对到向量库', 'data': ''})


@app.route('/vector_db_service/del_qa', methods=['POST'])
def del_qa():
    data = request.get_json()
    print(f'====>del_qa(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    question = data.get('question', [])

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not question:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    question_list=[q.strip() for q in question]

    try:
        is_succ, msg = delete_qa_from_collection(tenant_code, collection_name, question_list=question_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]删除问答对异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库删除问答对成功', 'data': ''})



@app.route('/vector_db_service/del_document', methods=['POST'])
def del_document():
    data = request.get_json()
    print(f'====>del_document(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    doc_name = data.get('doc_name', [])

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not doc_name:
        return jsonify({'status': 'fail', 'msg': '缺少问题参数', 'code': 400, 'data': ''})

    doc_name_list=[dname.strip() for dname in doc_name]

    try:
        is_succ, msg = delete_docs_from_collection(tenant_code, collection_name, doc_name_list=doc_name_list)
        if not is_succ:
            return jsonify({'status': 'fail', 'msg': msg, 'code': 400, 'data': ''})
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]删除文档异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库删除文档成功', 'data': ''})


@app.route('/vector_db_service/search_from_vector_db', methods=['POST'])
def search_from_vector_db():
    data = request.get_json()
    print(f'====>search_from_vector_db(),data={data}')
    tenant_code = data.get('tenant_code', '')
    collection_name = data.get('collection_name', '')
    api_key = data.get('api_key', '')
    query = data.get('query', '')
    collection_type = data.get('collection_type', '')
    filter_expr = data.get('filter_expr', '')
    limit=data.get('limit',5)

    if not check_api_key(api_key):
        return jsonify({'status': 'fail', 'code': 400, 'msg': 'api_key校验不通过', 'data': ''})

    if not tenant_code:
        return jsonify({'status': 'fail', 'msg': '缺少租户统一编码', 'code': 400, 'data': ''})

    if not collection_name:
        return jsonify({'status': 'fail', 'msg': '缺少知识库名称参数', 'code': 400, 'data': ''})

    if not query:
        return jsonify({'status': 'fail', 'msg': '搜索数据不能为空', 'code': 400, 'data': ''})

    if not collection_type:
        return jsonify({'status': 'fail', 'msg': 'collect_type不能为空', 'code': 400, 'data': ''})

    try:
        res = search_from_collection(tenant_code=tenant_code, collection_name=collection_name,
                                     collection_type=collection_type, query_list=[query], filter_expr=filter_expr, limit=limit)

        print(f"从向量库[{collection_name}]查询成功")
    except Exception:
        import traceback
        logger.exception(f"从向量库[{collection_name}]查询异常: %s", traceback.format_exc())
        return jsonify({'status': 'fail', 'msg': traceback.format_exc(), 'code': 400})
    return jsonify({'status': 'success', 'code': 200, 'msg': '从向量库查询成功', 'data': res})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8005)
