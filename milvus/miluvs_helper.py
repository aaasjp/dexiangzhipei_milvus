from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection, db,SearchResult,Hits,Hit
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import torch
from config.log_config import setup_vector_db_logging
from rank_bm25 import BM25Okapi
import jieba
from collections import defaultdict

import logging
setup_vector_db_logging()
logger = logging.getLogger('vector_db')

##加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 检测CUDA是否可用
try:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"检测到设备: {device}")
except ImportError:
    device = 'cpu'
    logger.warning("未安装torch，使用CPU设备")


embedding_model = HuggingFaceBgeEmbeddings(
    #model_name=config['embedding_model_path'],
    model_name="BAAI/bge-large-zh-v1.5",
    model_kwargs = {'device': device},
    encode_kwargs={'normalize_embeddings': True}  # set True to compute cosine similarity
)


def qa_collection_schema():
    """全局QA collection的schema，包含tenant_code和org_code字段"""
    fields = [
        FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name='question', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='answer', dtype=DataType.VARCHAR, max_length=20000),
        FieldSchema(name='source', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='tenant_code', dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name='org_code', dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name='metadata', dtype=DataType.JSON, max_length=2000)
    ]
    return CollectionSchema(fields=fields)


def doc_collection_schema():
    """全局DOC collection的schema，包含tenant_code和org_code字段"""
    fields = [
        FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name='file_name', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='block_id', dtype=DataType.INT64, is_primary=False),
        FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=20000),
        FieldSchema(name='source', dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name='tenant_code', dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name='org_code', dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name='metadata', dtype=DataType.JSON, max_length=2000)
    ]
    return CollectionSchema(fields=fields)


def get_global_collections():
    """获取全局数据库和collection名称"""
    config_name_convention_dic = config['name_convention']
    global_db_name = config_name_convention_dic['global_database']
    global_collection_qa_name = config_name_convention_dic['global_collection_qa']
    global_collection_doc_name = config_name_convention_dic['global_collection_doc']
    return global_db_name, global_collection_qa_name, global_collection_doc_name


def ensure_index_exists(collection, field_name, index_params):
    """确保字段索引存在，如果不存在则创建"""
    try:
        # 获取collection的所有索引
        indexes = collection.indexes
        # 检查该字段是否已有索引
        field_has_index = any(idx.field_name == field_name for idx in indexes)
        
        if not field_has_index:
            logger.info(f"字段[{field_name}]没有索引，正在创建...")
            collection.create_index(field_name=field_name, index_params=index_params)
            logger.info(f"字段[{field_name}]索引创建成功")
        else:
            logger.debug(f"字段[{field_name}]索引已存在")
    except Exception as e:
        import traceback
        logger.error(f"检查或创建字段[{field_name}]索引时出错: {traceback.format_exc()}")
        raise


def create_collection():
    """创建全局向量库和两个全局collection（如果不存在）"""
    logger.info(f"调用方法:create_collection，创建全局向量库和collection")

    config_milvus_dic = config['milvus']
    index_params = config['index_params']
    varchar_index_params = config.get('varchar_index_params', {'index_type': 'INVERTED'})
    
    global_db_name, global_collection_qa_name, global_collection_doc_name = get_global_collections()

    # 连接并创建全局数据库（如果不存在）
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'])
    if global_db_name not in db.list_database():
        db.create_database(global_db_name)
        logger.info(f"全局数据库[{global_db_name}]创建成功")
    
    # 连接到全局数据库
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()
    
    # 创建全局QA collection（如果不存在）
    if global_collection_qa_name not in exist_collection_list:
        collection = Collection(global_collection_qa_name, schema=qa_collection_schema())
        # 为embedding字段创建向量索引
        collection.create_index(field_name="embedding", index_params=index_params)
        # 为tenant_code和org_code字段创建VARCHAR索引
        collection.create_index(field_name="tenant_code", index_params=varchar_index_params)
        collection.create_index(field_name="org_code", index_params=varchar_index_params)
        collection.load()
        logger.info(f"全局向量库[{global_collection_qa_name}]创建成功，已为embedding、tenant_code、org_code字段创建索引")
    else:
        # collection已存在，检查并创建缺失的索引
        collection = Collection(global_collection_qa_name)
        ensure_index_exists(collection, "embedding", index_params)
        ensure_index_exists(collection, "tenant_code", varchar_index_params)
        ensure_index_exists(collection, "org_code", varchar_index_params)
        logger.info(f"全局向量库[{global_collection_qa_name}]已存在，已确保所有索引存在")
    
    # 创建全局DOC collection（如果不存在）
    if global_collection_doc_name not in exist_collection_list:
        collection = Collection(global_collection_doc_name, schema=doc_collection_schema())
        # 为embedding字段创建向量索引
        collection.create_index(field_name="embedding", index_params=index_params)
        # 为tenant_code和org_code字段创建VARCHAR索引
        collection.create_index(field_name="tenant_code", index_params=varchar_index_params)
        collection.create_index(field_name="org_code", index_params=varchar_index_params)
        collection.load()
        logger.info(f"全局向量库[{global_collection_doc_name}]创建成功，已为embedding、tenant_code、org_code字段创建索引")
    else:
        # collection已存在，检查并创建缺失的索引
        collection = Collection(global_collection_doc_name)
        ensure_index_exists(collection, "embedding", index_params)
        ensure_index_exists(collection, "tenant_code", varchar_index_params)
        ensure_index_exists(collection, "org_code", varchar_index_params)
        logger.info(f"全局向量库[{global_collection_doc_name}]已存在，已确保所有索引存在")

    logger.info(f"全局向量库和collection初始化完成")
    return True, f"全局向量库和collection初始化完成"


def delete_collection(tenant_code=None, org_code=None):
    """删除全局collection中的数据（根据tenant_code和org_code过滤）"""
    logger.info(f"调用方法:delete_collection，参数为:tenant_code={tenant_code}, org_code={org_code}")

    config_milvus_dic = config['milvus']
    global_db_name, global_collection_qa_name, global_collection_doc_name = get_global_collections()

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()

    if global_collection_qa_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_qa_name}]不存在")
        return False, f"全局向量库[{global_collection_qa_name}]不存在"

    if global_collection_doc_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_doc_name}]不存在")
        return False, f"全局向量库[{global_collection_doc_name}]不存在"

    # 构建过滤表达式
    filter_expr = ""
    if tenant_code and org_code:
        filter_expr = f"tenant_code == '{tenant_code}' && org_code == '{org_code}'"
    elif tenant_code:
        filter_expr = f"tenant_code == '{tenant_code}'"
    elif org_code:
        filter_expr = f"org_code == '{org_code}'"

    deleted_count = 0
    if filter_expr:
        # 删除QA collection中的数据
        qa_collection = Collection(global_collection_qa_name)
        qa_collection.delete(filter_expr)
        qa_collection.flush()
        logger.info(f"从全局QA向量库删除数据，过滤条件: {filter_expr}")

        # 删除DOC collection中的数据
        doc_collection = Collection(global_collection_doc_name)
        doc_collection.delete(filter_expr)
        doc_collection.flush()
        logger.info(f"从全局DOC向量库删除数据，过滤条件: {filter_expr}")
    else:
        logger.warning("未提供tenant_code或org_code，无法删除数据")

    logger.info(f"从全局向量库删除数据成功")
    return True, f"从全局向量库删除数据成功"


def insert_qa_to_collection(tenant_code, org_code, question_list, answer_list, source_list, metadata_list):
    """插入QA到全局collection，org_code就是org_code"""
    logger.info(f"调用方法:insert_qa_to_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, 问答对数量={len(question_list)}")
    
    config_milvus_dic = config['milvus']
    global_db_name, global_collection_qa_name, _ = get_global_collections()

    # 连接到全局数据库
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()
    
    if global_collection_qa_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_qa_name}]不存在，请先创建")
        return False, f"全局向量库[{global_collection_qa_name}]不存在，请先创建"

    collection = Collection(name=global_collection_qa_name)

    # org_code就是org_code
    org_code = org_code

    # 检查已存在的问题，如果存在则先删除
    exist_quest_count = 0
    to_delete_questions = []
    for i in range(len(question_list)):
        q = question_list[i]
        escaped_question = q.replace("'", "\\'")
        # 构建过滤表达式，只有当tenant_code和org_code不为空时才加入条件
        filter_parts = [f"question == '{escaped_question}'"]
        if tenant_code:
            filter_parts.append(f"tenant_code == '{tenant_code}'")
        if org_code:
            filter_parts.append(f"org_code == '{org_code}'")
        filter_expr = " && ".join(filter_parts)
        res = collection.query(expr=filter_expr)
        if len(res) > 0:
            exist_quest_count += 1
            to_delete_questions.append(q)
            logger.info(f'新增问答对：问题=[{q}] 已经存在，将先删除再插入')

    # 如果存在相同的问题，先删除
    if len(to_delete_questions) > 0:
        logger.info(f'检测到{len(to_delete_questions)}个已存在的问题，开始删除: {to_delete_questions}')
        for question in to_delete_questions:
            escaped_question = question.replace("'", "\\'")
            filter_expr = f"question == '{escaped_question}' && tenant_code == '{tenant_code}' && org_code == '{org_code}'"
            collection.delete(filter_expr)
        collection.flush()
        logger.info(f'已删除{len(to_delete_questions)}个已存在的问题')

    if len(question_list) == 0:
        logger.info(f'新增问答对0条')
        return True, f'新增问答对0条'

    question_embeddings = embedding_model.embed_documents(question_list)
    
    # 准备数据：question, answer, source, tenant_code, org_code, embedding, metadata
    tenant_code_list = [tenant_code] * len(question_list)
    org_code_list = [org_code] * len(question_list)
    
    data = [question_list, answer_list, source_list, 
            tenant_code_list, org_code_list, question_embeddings, metadata_list]
    collection.insert(data=data)
    collection.flush()
    logger.info(f'插入全局向量库[{global_collection_qa_name}]成功，新增问答对{len(question_list)}条，其中{exist_quest_count}条是删除后重新插入的')

    return True, f"插入全局向量库成功，新增问答对{len(question_list)}条，其中{exist_quest_count}条是删除后重新插入的"


def upsert_qa_to_collection(tenant_code, org_code, question_list, answer_list, source_list, metadata_list):
    """更新QA到全局collection（先删除后插入），org_code就是org_code"""
    logger.info(f"调用方法:upsert_qa_to_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, 问答对数量={len(question_list)}")

    # 先删除已存在的问答对
    is_succ, msg = delete_qa_from_collection(tenant_code, org_code, question_list)
    if not is_succ:
        logger.error(f"更新问答对:先删除已存在的问答对出错:{msg}")
        return False, f"更新问答对:先删除已存在的问答对出错:{msg}"

    # 再插入新的问答对
    is_succ, msg = insert_qa_to_collection(tenant_code, org_code, question_list, answer_list, source_list,
                                           metadata_list)
    if not is_succ:
        logger.error(f"更新问答对：删除之后插入问答对出错:{msg}")
        return False, f"更新问答对：删除之后插入问答对出错:{msg}"

    logger.info(f'更新问答对到全局向量库成功')
    return True, f'更新问答对到全局向量库成功'


def insert_docs_to_collection(tenant_code, org_code, doc_name_list, doc_content_list, source_list,
                              metadata_list):
    """插入文档到全局collection，org_code就是org_code"""
    logger.info(f"调用方法:insert_docs_to_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, 文档数量={len(doc_name_list)}")
    
    config_milvus_dic = config['milvus']
    global_db_name, _, global_collection_doc_name = get_global_collections()

    # 连接到全局数据库
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()
    
    if global_collection_doc_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_doc_name}]不存在，请先创建")
        return False, f"全局向量库[{global_collection_doc_name}]不存在，请先创建"

    collection = Collection(name=global_collection_doc_name)

    # org_code就是org_code
    org_code = org_code

    # 检查已存在的文档，如果存在则先删除
    exist_doc_count = 0
    to_delete_file_names = []
    for i in range(len(doc_name_list)):
        dname = doc_name_list[i]
        escaped_dname = dname.replace("'", "\\'")
        # 构建过滤表达式，只有当tenant_code和org_code不为空时才加入条件
        filter_parts = [f"file_name == '{escaped_dname}'"]
        if tenant_code:
            filter_parts.append(f"tenant_code == '{tenant_code}'")
        if org_code:
            filter_parts.append(f"org_code == '{org_code}'")
        filter_expr = " && ".join(filter_parts)
        res = collection.query(expr=filter_expr)
        if len(res) > 0:
            exist_doc_count += 1
            to_delete_file_names.append(dname)
            logger.info(f'新增文档：file_name=[{dname}] 已经存在，将先删除再插入')

    # 如果存在同名文件，先删除
    if len(to_delete_file_names) > 0:
        logger.info(f'检测到{len(to_delete_file_names)}个已存在的文档，开始删除: {to_delete_file_names}')
        for file_name in to_delete_file_names:
            escaped_file_name = file_name.replace("'", "\\'")
            filter_expr = f"file_name == '{escaped_file_name}' && tenant_code == '{tenant_code}' && org_code == '{org_code}'"
            collection.delete(filter_expr)
        collection.flush()
        logger.info(f'已删除{len(to_delete_file_names)}个已存在的文档')

    if len(doc_name_list) == 0:
        logger.info(f'新增文档0条，已经存在而无需新增的文档{exist_doc_count}条')
        return True, f'新增文档0条，已经存在而无需新增的文档{exist_doc_count}条'

    # 文档分块
    new_doc_name_list = []
    new_doc_block_id_list = []
    new_doc_content_block_list = []
    new_source_list = []
    new_metadata_list = []

    CHUNK_LEN = config['split']['chunk_size']
    OVERLAP = config['split']['overlap']

    text_spliter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_LEN, chunk_overlap=OVERLAP,
        length_function=len, keep_separator=False
    )
    for i in range(len(doc_content_list)):
        cnt = doc_content_list[i]
        dname = doc_name_list[i]
        dsource = source_list[i]
        metadata = metadata_list[i]

        blocks = text_spliter.split_text(cnt)
        for k in range(len(blocks)):
            new_doc_name_list.append(dname)
            new_doc_block_id_list.append(k)
            new_doc_content_block_list.append(blocks[k])
            new_source_list.append(dsource)
            new_metadata_list.append(metadata)

    block_embeddings = embedding_model.embed_documents(new_doc_content_block_list)
    logger.info(f"文档分块完成，共{len(new_doc_content_block_list)}个块，开始生成向量嵌入")
    
    # 准备数据：file_name, block_id, content, source, tenant_code, org_code, embedding, metadata
    tenant_code_list = [tenant_code] * len(new_doc_content_block_list)
    org_code_list = [org_code] * len(new_doc_content_block_list)
    
    data = [new_doc_name_list, new_doc_block_id_list, new_doc_content_block_list, new_source_list,
            tenant_code_list, org_code_list, block_embeddings, new_metadata_list]
    collection.insert(data=data)
    collection.flush()
    logger.info(f"插入docs到全局向量库[{global_collection_doc_name}]成功,新增文档{len(doc_name_list)}条，已经存在而无需新增的文档{exist_doc_count}条，共插入{len(new_doc_content_block_list)}个文档块")
    
    return True, f"插入docs到全局向量库成功,新增文档{len(doc_name_list)}条，已经存在而无需新增的文档{exist_doc_count}条"


def delete_qa_from_collection(tenant_code, org_code, question_list):
    """从全局collection删除QA，org_code就是org_code"""
    logger.info(f"调用方法:delete_qa_from_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, 待删除问题数量={len(question_list)}")
    logger.info(f'待删除的问题列表: {question_list}')

    config_milvus_dic = config['milvus']
    global_db_name, global_collection_qa_name, _ = get_global_collections()

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()
    
    if global_collection_qa_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_qa_name}]不存在")
        return False, f"全局向量库[{global_collection_qa_name}]不存在"

    collection = Collection(global_collection_qa_name)
    
    # org_code就是org_code
    org_code = org_code

    for question in question_list:
        escaped_question = question.replace("'", "\\'")
        # 构建过滤表达式，只有当tenant_code和org_code不为空时才加入条件
        filter_parts = [f"question == '{escaped_question}'"]
        if tenant_code:
            filter_parts.append(f"tenant_code == '{tenant_code}'")
        if org_code:
            filter_parts.append(f"org_code == '{org_code}'")
        filter_expr = " && ".join(filter_parts)
        collection.delete(filter_expr)
    collection.flush()

    logger.info(f"从全局向量库[{global_collection_qa_name}]删除问答对成功，共删除{len(question_list)}条")
    return True, f"从全局向量库删除问答对成功"


def delete_docs_from_collection(tenant_code, org_code, doc_name_list):
    """从全局collection删除文档，org_code就是org_code"""
    logger.info(f"调用方法:delete_docs_from_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, 待删除文档数量={len(doc_name_list)}")
    logger.info(f'待删除的文档列表: {doc_name_list}')

    config_milvus_dic = config['milvus']
    global_db_name, _, global_collection_doc_name = get_global_collections()

    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()
    
    if global_collection_doc_name not in exist_collection_list:
        logger.error(f"全局向量库[{global_collection_doc_name}]不存在")
        return False, f"全局向量库[{global_collection_doc_name}]不存在"

    collection = Collection(global_collection_doc_name)
    
    # org_code就是org_code
    org_code = org_code

    for file_name in doc_name_list:
        escaped_file_name = file_name.replace("'", "\\'")
        # 构建过滤表达式，只有当tenant_code和org_code不为空时才加入条件
        filter_parts = [f"file_name == '{escaped_file_name}'"]
        if tenant_code:
            filter_parts.append(f"tenant_code == '{tenant_code}'")
        if org_code:
            filter_parts.append(f"org_code == '{org_code}'")
        filter_expr = " && ".join(filter_parts)
        collection.delete(filter_expr)
    collection.flush()

    logger.info(f"从全局向量库[{global_collection_doc_name}]删除文档成功，共删除{len(doc_name_list)}个文档")
    return True, f"从全局向量库删除文档成功"


def _tokenize_chinese(text):
    """中文分词函数"""
    return list(jieba.cut(text))


def _build_bm25_index(collection, final_filter, collection_type):
    """从Milvus collection构建BM25索引"""
    logger.info(f"开始构建BM25索引，collection_type={collection_type}, filter={final_filter}")
    
    # 确定要检索的文本字段
    if collection_type == 'QA':
        text_field = 'question'
    else:
        text_field = 'content'
    
    # 从Milvus获取所有文档
    fields = [f.name for f in collection.schema.fields if f.name != 'embedding']
    try:
        # 查询所有符合条件的文档
        # expr参数是必需的，如果final_filter为空，使用主键id >= 0查询所有数据
        if final_filter:
            query_params = {
                'expr': final_filter,
                'output_fields': fields,
                'limit': 16384  # Milvus默认最大查询数量
            }
        else:
            # 当没有过滤条件时，使用主键id >= 0来查询所有数据
            query_params = {
                'expr': 'id >= 0',
                'output_fields': fields,
                'limit': 16384  # Milvus默认最大查询数量
            }
        
        query_result = collection.query(**query_params)
        
        if len(query_result) == 0:
            logger.warning("没有找到符合条件的文档用于构建BM25索引")
            return None, []
        
        # 提取文本和对应的实体信息
        texts = []
        entities = []
        for item in query_result:
            text = item.get(text_field, '')
            if text:
                texts.append(text)
                entities.append(item)
        
        if len(texts) == 0:
            logger.warning("没有找到有效的文本内容用于构建BM25索引")
            return None, []
        
        # 对文本进行分词
        tokenized_texts = [_tokenize_chinese(text) for text in texts]
        
        # 构建BM25索引
        bm25 = BM25Okapi(tokenized_texts)
        logger.info(f"BM25索引构建完成，共{len(texts)}个文档")
        
        return bm25, entities
    except Exception as e:
        import traceback
        logger.error(f"构建BM25索引时出错: {traceback.format_exc()}")
        return None, []


def _bm25_search(bm25, entities, query, limit):
    """使用BM25进行检索"""
    if bm25 is None or len(entities) == 0:
        return []
    
    # 对查询进行分词
    tokenized_query = _tokenize_chinese(query)
    
    # BM25检索
    scores = bm25.get_scores(tokenized_query)
    
    # 获取top-k结果
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:limit]
    
    results = []
    for idx in top_indices:
        result = entities[idx].copy()
        result['bm25_score'] = scores[idx]
        results.append(result)
    
    return results


def _reciprocal_rank_fusion(vector_results, bm25_results, k=20, bm25_weight=1.2):
    """使用RRF（Reciprocal Rank Fusion）融合向量检索和BM25检索结果
    
    Args:
        vector_results: 向量检索结果
        bm25_results: BM25检索结果
        k: RRF参数k，默认20
        bm25_weight: BM25权重系数，默认1.2（加大BM25的rank比重）
    """
    # 构建id到rank的映射
    vector_ranks = {}
    bm25_ranks = {}
    
    # 向量检索结果排名
    for rank, entity in enumerate(vector_results, start=1):
        doc_id = entity.get('id')
        if doc_id is not None:
            vector_ranks[doc_id] = rank
    
    # BM25检索结果排名
    for rank, entity in enumerate(bm25_results, start=1):
        doc_id = entity.get('id')
        if doc_id is not None:
            bm25_ranks[doc_id] = rank
    
    # 合并所有文档ID
    all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
    
    # 计算RRF分数，加大BM25的权重
    rrf_scores = {}
    for doc_id in all_ids:
        rrf_score = 0.0
        if doc_id in vector_ranks:
            rrf_score += 1.0 / (k + vector_ranks[doc_id])
        if doc_id in bm25_ranks:
            # 使用权重系数加大BM25的rank比重
            rrf_score += bm25_weight * 1.0 / (k + bm25_ranks[doc_id])
        rrf_scores[doc_id] = rrf_score
    
    # 按RRF分数排序
    sorted_ids = sorted(all_ids, key=lambda x: rrf_scores[x], reverse=True)
    
    # 构建结果映射
    vector_dict = {entity.get('id'): entity for entity in vector_results if entity.get('id') is not None}
    bm25_dict = {entity.get('id'): entity for entity in bm25_results if entity.get('id') is not None}
    
    # 合并结果
    fused_results = []
    for doc_id in sorted_ids:
        # 优先使用向量检索的结果（包含更多字段）
        if doc_id in vector_dict:
            result = vector_dict[doc_id].copy()
        elif doc_id in bm25_dict:
            result = bm25_dict[doc_id].copy()
        else:
            continue
        
        # 添加融合分数
        result['rrf_score'] = rrf_scores[doc_id]
        if doc_id in vector_ranks:
            result['vector_rank'] = vector_ranks[doc_id]
        if doc_id in bm25_ranks:
            result['bm25_rank'] = bm25_ranks[doc_id]
        
        fused_results.append(result)
    
    return fused_results


def search_from_collection(tenant_code, org_code, collection_type, query_list, filter_expr='', limit=5, use_hybrid=False, vector_similarity_threshold=None, rrf_similarity_threshold=None):
    """从全局collection搜索
    
    Args:
        tenant_code: 租户代码
        org_code: 部门代码
        collection_type: 集合类型，'QA'或'DOC'
        query_list: 查询文本列表
        filter_expr: 过滤表达式
        limit: 返回结果数量限制
        use_hybrid: 是否使用混合检索（向量+BM25），默认False
        vector_similarity_threshold: 向量相似度阈值，默认从配置文件读取
        rrf_similarity_threshold: RRF相似度阈值，默认从配置文件读取
    
    Returns:
        检索结果字典，包含ids、distances、entities
    """
    # 如果参数是None，则不进行阈值过滤；如果不是None，则使用该值进行过滤
    logger.info(f"调用方法:search_from_collection，参数为:tenant_code={tenant_code}, org_code={org_code}, collection_type={collection_type}, 查询数量={len(query_list)}, limit={limit}, use_hybrid={use_hybrid}, vector_similarity_threshold={vector_similarity_threshold}, rrf_similarity_threshold={rrf_similarity_threshold}")
    logger.info(f"查询内容: {query_list}, 过滤条件: {filter_expr}")
    
    config_milvus_dic = config['milvus']
    global_db_name, global_collection_qa_name, global_collection_doc_name = get_global_collections()

    assert collection_type in ('QA', 'DOC'), 'collection_type必须是[QA,DOC]之一'

    # 连接到全局数据库
    connections.connect(host=config_milvus_dic['host'], port=config_milvus_dic['port'], db_name=global_db_name)
    exist_collection_list = utility.list_collections()

    if collection_type == 'QA':
        if global_collection_qa_name not in exist_collection_list:
            logger.error(f"全局向量库[{global_collection_qa_name}]不存在")
            return False, f"全局向量库[{global_collection_qa_name}]不存在"
        collection = Collection(global_collection_qa_name)
    else:
        if global_collection_doc_name not in exist_collection_list:
            logger.error(f"全局向量库[{global_collection_doc_name}]不存在")
            return False, f"全局向量库[{global_collection_doc_name}]不存在"
        collection = Collection(global_collection_doc_name)

    # 构建过滤表达式
    base_filter = ""
    if tenant_code and org_code:
        base_filter = f"tenant_code == '{tenant_code}' && org_code == '{org_code}'"
    elif tenant_code:
        base_filter = f"tenant_code == '{tenant_code}'"
    elif org_code:
        base_filter = f"org_code == '{org_code}'"
    
    # 合并用户提供的过滤表达式
    if filter_expr:
        if base_filter:
            final_filter = f"({base_filter}) && ({filter_expr})"
        else:
            final_filter = filter_expr
    else:
        final_filter = base_filter

    fields = [f.name for f in collection.schema.fields if f.name != 'embedding']
    
    # 如果使用混合检索
    if use_hybrid:
        logger.info("使用混合检索模式（向量检索 + BM25检索）")
        
        # 构建BM25索引
        bm25, bm25_entities = _build_bm25_index(collection, final_filter, collection_type)
        
        ids = []
        distances = []
        entities = []
        
        # 对每个查询进行混合检索
        for query in query_list:
            # 向量检索
            logger.info(f"开始向量检索，查询: {query}")
            query_embeddings = embedding_model.embed_documents([query])
            search_params = {
                'data': query_embeddings,
                'anns_field': "embedding",
                'param': config['search_params'],
                'limit': limit * 5,  # 获取更多结果用于融合
                'output_fields': fields
            }
            if final_filter:
                search_params['expr'] = final_filter
            vector_res = collection.search(**search_params)
            
            vector_results = []
            for hits in vector_res:
                for hit in hits:
                    ent = {}
                    # 确保包含id字段（Milvus的Hit对象有id属性）
                    ent['id'] = hit.id
                    for f in fields:
                        if f != 'id':  # id已经单独处理
                            ent[f] = hit.get(f)
                    ent['score'] = hit.score
                    vector_results.append(ent)
            
            # BM25检索
            logger.info(f"开始BM25检索，查询: {query}")
            bm25_results = _bm25_search(bm25, bm25_entities, query, limit * 5)
            
            # RRF融合
            logger.info(f"开始RRF融合结果")
            rrf_k = config.get('hybrid_search', {}).get('rrf_k', 20)
            bm25_weight = config.get('hybrid_search', {}).get('bm25_weight', 1.2)
            fused_results = _reciprocal_rank_fusion(vector_results, bm25_results, k=rrf_k, bm25_weight=bm25_weight)
            
            # 根据RRF相似度阈值过滤结果（如果提供了阈值）
            if rrf_similarity_threshold is not None:
                filtered_results = [r for r in fused_results if r.get('rrf_score', 0.0) >= rrf_similarity_threshold]
                logger.info(f"RRF融合后共{len(fused_results)}条结果，阈值过滤后剩余{len(filtered_results)}条（阈值={rrf_similarity_threshold}）")
            else:
                filtered_results = fused_results
                logger.info(f"RRF融合后共{len(fused_results)}条结果，未应用阈值过滤")
            
            # 取top-k结果
            top_results = filtered_results[:limit]
            
            # 格式化结果
            query_ids = [r.get('id') for r in top_results if r.get('id') is not None]
            # 直接使用RRF分数，不进行转换
            query_distances = [r.get('rrf_score', 0.0) for r in top_results if r.get('id') is not None]
            query_entities = [r for r in top_results if r.get('id') is not None]
            
            ids.append(query_ids)
            distances.append(query_distances)
            entities.append(query_entities)
        
        ret_dic = {
            "ids": ids,
            "distances": distances,
            "entities": entities
        }
        # 计算总结果数量
        total_results = sum(len(e) for e in entities)
        logger.info(f'混合检索完成，{len(ids)}个查询，共返回{total_results}条结果')
        return ret_dic
    
    else:
        # 纯向量检索（原有逻辑）
        logger.info("使用纯向量检索模式")
        logger.info(f"开始生成查询向量嵌入，查询数量={len(query_list)}")
        query_embeddings = embedding_model.embed_documents(query_list)
        logger.info(f"查询向量嵌入生成完成，开始搜索，过滤条件: {final_filter}")

        search_params = {
            'data': query_embeddings,
            'anns_field': "embedding",
            'param': config['search_params'],
            'limit': limit,
            'output_fields': fields
        }
        if final_filter:
            search_params['expr'] = final_filter
        res = collection.search(**search_params)

        ids = []
        distances = []
        entities = []

        for hits in res:
            query_ids = []
            query_distances = []
            ents = []

            for rank, hit in enumerate(hits, start=1):
                # 根据向量相似度阈值过滤结果（如果提供了阈值）
                if vector_similarity_threshold is None or hit.score >= vector_similarity_threshold:
                    ent = {}
                    for f in fields:
                        ent[f] = hit.get(f)
                    ent['score'] = hit.score  # 向量相似度分数
                    ent['vector_rank'] = rank  # 向量排名
                    ents.append(ent)
                    query_ids.append(hit.id)
                    # 对于COSINE相似度，score就是相似度值，可以直接使用
                    query_distances.append(hit.score)
            
            if vector_similarity_threshold is not None:
                logger.info(f"向量检索共{len(hits)}条结果，阈值过滤后剩余{len(ents)}条（阈值={vector_similarity_threshold}）")
            else:
                logger.info(f"向量检索共{len(hits)}条结果，未应用阈值过滤")
            ids.append(query_ids)
            distances.append(query_distances)
            entities.append(ents)

        ret_dic = {
            "ids": ids,
            "distances": distances,
            "entities": entities
        }
        # 计算总结果数量
        total_results = sum(len(e) for e in entities)
        logger.info(f'搜索结果: {json.dumps(ret_dic, ensure_ascii=False, indent=2)}')
        logger.info(f'从全局向量库搜索完成，{len(ids)}个查询，共返回{total_results}条结果')
        return ret_dic
