import requests
import json
import logging

logger = logging.getLogger(__name__)

with open('./config/config.json', 'r', encoding='utf8') as f:
    config = json.load(f)

MILVUS_HOST = config['milvus_api_server']['host']
MILVUS_PORT = config['milvus_api_server']['port']
MILVUS_URL = f'http://{MILVUS_HOST}:{MILVUS_PORT}/vector_db_service/search_from_vector_db'
MILVUS_API_KEY=config['api_key']


def search_qa_from_vector_db(tenant_code, collection_name, query, filter_expr='', limit=5, use_hybrid=False):
    questions, answers, scores, sources = [], [], [], []
    res = search_from_vector_db_api(tenant_code, collection_name, 'QA', query, filter_expr, limit, use_hybrid)

    ids=res['ids'][0]
    distances=res['distances'][0]
    entities=res['entities'][0]

    for ent in entities:
        questions.append(ent['question'])
        answers.append(ent['answer'])
        scores.append(ent['score'])
        sources.append(ent['source'])

    return questions, answers, scores, sources


def search_docs_block_from_vector_db(tenant_code, collection_name, query, filter_expr='', limit=5, use_hybrid=False):
    doc_contents, doc_scores, doc_block_ids, doc_sources, doc_file_names = [], [], [], [], []
    res = search_from_vector_db_api(tenant_code, collection_name, 'DOC', query, filter_expr, limit, use_hybrid)

    ids=res['ids'][0]
    distances=res['distances'][0]
    entities=res['entities'][0]

    for ent in entities:
        doc_contents.append(ent['content'])
        doc_scores.append(ent['score'])
        doc_block_ids.append(ent['block_id'])
        doc_sources.append(ent['source'])
        doc_file_names.append(ent['file_name'])

    return doc_contents, doc_scores, doc_block_ids, doc_sources, doc_file_names


def search_from_vector_db_api(tenant_code, collection_name, collection_type, query, filter_expr='', limit=5, use_hybrid=False):
    logger.info(f"请求milvus服务器: tenant_code={tenant_code}, collection_name={collection_name}, collection_type={collection_type}, query={query}, filter_expr={filter_expr}, limit={limit}, use_hybrid={use_hybrid}")

    data = {
        'tenant_code': tenant_code,
        'collection_name': collection_name,
        'collection_type': collection_type,
        'query': query,
        'filter_expr': filter_expr,
        'limit': limit,
        'use_hybrid': use_hybrid,
        'api_key':MILVUS_API_KEY
    }
    try:
        json_data = json.dumps(data)
        response = requests.post(MILVUS_URL, headers={'Content-Type': 'application/json'}, data=json_data)
        res_body = response.json()
        #print(f'====>search_from_vector_db_api,res_body={json.dumps(res_body,ensure_ascii=False,indent=2)}')
        code = res_body['code']
        if code == 200:
            res_data = res_body['data']
            return res_data
        raise ValueError(res_body['msg'])
    except Exception as e:
        import traceback
        logging.error(f'request vector db failed。%s', traceback.format_exc())
        raise


if __name__ == "__main__":
    tenant_code = 'xiaomi'
    collection_name = 'xiaoshou'
    query = '中国电信咋样'
    limit = 3


    questions, answers, scores, sources = search_qa_from_vector_db(tenant_code, collection_name, query, limit=limit)
    logger.info(f'questions={questions}')
    logger.info(f'answers={answers}')
    logger.info(f'scores={scores}')
    logger.info(f'sources={sources}')

    query = '粤省心'
    doc_contents, doc_scores, doc_block_ids, doc_sources, doc_file_names = search_docs_block_from_vector_db(tenant_code,
                                                                                                            collection_name,
                                                                                                            query,
                                                                                                            limit=limit)

    logger.info(f'doc_contents={doc_contents}')
    logger.info(f'doc_scores={doc_scores}')
    logger.info(f'doc_sources={doc_sources}')
    logger.info(f'doc_file_names={doc_file_names}')




