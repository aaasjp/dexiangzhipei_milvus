#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
向量数据库接口完整测试程序
包含所有接口的测试用例
"""

import requests
import json
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置信息
BASE_URL = 'http://127.0.0.1:8005/vector_db_service/'
API_KEY = '2024_hello_ai'
TENANT_CODE = 'ningbo_bank'
COLLECTION_NAME = 'xzb'


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}")


def post_request(url, data, show_request=True):
    """
    发送POST请求
    
    Args:
        url: 请求URL
        data: 请求数据（字典）
        show_request: 是否显示请求信息
    
    Returns:
        响应JSON数据或None
    """
    try:
        if show_request:
            print(f"\n请求URL: {url}")
            print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=data, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        if show_request:
            print(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return result
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP错误: {errh}")
        if hasattr(errh.response, 'text'):
            print(f"错误详情: {errh.response.text}")
        return None
    except requests.exceptions.ConnectionError as errc:
        print(f"连接错误: {errc}")
        print("请确保向量数据库服务已启动（默认端口8005）")
        return None
    except requests.exceptions.Timeout as errt:
        print(f"超时错误: {errt}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"请求异常: {err}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"响应内容: {response.text}")
        return None


def test_new_collection():
    """测试创建知识库接口"""
    print_separator("测试1: 创建知识库")
    api_url = BASE_URL + 'new_collection'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY
    }
    result = post_request(api_url, data)
    return result


def test_del_collection():
    """测试删除知识库接口"""
    print_separator("测试2: 删除知识库")
    api_url = BASE_URL + 'del_collection'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY
    }
    result = post_request(api_url, data)
    return result


def test_add_qa():
    """测试添加问答对接口"""
    print_separator("测试3: 添加问答对")
    api_url = BASE_URL + 'add_qa'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'question': '1+1等于多少？',
        'answer': '1+1=2',
        'source': 'test_source'
    }
    result = post_request(api_url, data)
    return result


def test_add_multiple_qa():
    """测试添加多个问答对"""
    print_separator("测试4: 添加多个问答对")
    api_url = BASE_URL + 'add_qa'
    
    qa_list = [
        {'question': '什么是人工智能？', 'answer': '人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。', 'source': 'wiki'},
        {'question': 'Python是什么？', 'answer': 'Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。', 'source': 'wiki'},
        {'question': '向量数据库的作用是什么？', 'answer': '向量数据库用于存储和检索高维向量数据，常用于相似度搜索和推荐系统。', 'source': 'wiki'}
    ]
    
    results = []
    for qa in qa_list:
        data = {
            'tenant_code': TENANT_CODE,
            'collection_name': COLLECTION_NAME,
            'api_key': API_KEY,
            **qa
        }
        result = post_request(api_url, data)
        results.append(result)
    
    return results


def test_add_qa_from_template():
    """测试从模板添加问答对接口"""
    print_separator("测试5: 从模板添加问答对")
    api_url = BASE_URL + 'add_qa_from_template'
    
    # 注意：需要根据实际路径修改
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '问答库模板.xlsx')
    
    if not os.path.exists(template_path):
        print(f"警告: 模板文件不存在: {template_path}")
        print("跳过此测试")
        return None
    
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'template_path': template_path
    }
    result = post_request(api_url, data)
    return result


def test_add_document():
    """测试添加文档接口"""
    print_separator("测试6: 添加文档")
    api_url = BASE_URL + 'add_document'
    
    # 注意：需要提供有效的文档URL
    # 这里使用示例URL，实际使用时需要替换为真实可访问的URL
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'doc_url': 'http://220.154.134.61:9000/forum-files/2025-11-20-screenshot-20251120-020814-73502e5e-ae2b-428b-ba1c-28e7e9216700.png',
        'doc_name': '简历2.png'
    }
    
    print("注意: 此测试需要有效的文档URL，如果URL不可访问将失败")
    result = post_request(api_url, data)
    return result


def test_add_multi_document():
    """测试批量添加文档接口"""
    print_separator("测试7: 批量添加文档")
    api_url = BASE_URL + 'add_multi_document'
    
    # 注意：需要提供有效的文档URL列表
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'multi_doc_urls': [
            'http://220.154.134.61:9000/forum-files/2025-11-20-screenshot-20251120-020814-73502e5e-ae2b-428b-ba1c-28e7e9216700.png',
        ],
        'doc_names': [
            '简历.png'
        ]
    }
    
    print("注意: 此测试需要有效的文档URL，如果URL不可访问将失败")
    result = post_request(api_url, data)
    return result


def test_update_qa():
    """测试更新问答对接口"""
    print_separator("测试8: 更新问答对")
    api_url = BASE_URL + 'update_qa'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'question': '1+1等于多少？',
        'answer': '1+1=2（已更新）',
        'source': 'updated_source'
    }
    result = post_request(api_url, data)
    return result


def test_del_qa():
    """测试删除问答对接口"""
    print_separator("测试9: 删除问答对")
    api_url = BASE_URL + 'del_qa'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'question': ['1+1等于多少？']  # 支持批量删除
    }
    result = post_request(api_url, data)
    return result


def test_del_multiple_qa():
    """测试批量删除问答对"""
    print_separator("测试10: 批量删除问答对")
    api_url = BASE_URL + 'del_qa'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'question': ['什么是人工智能？', 'Python是什么？']
    }
    result = post_request(api_url, data)
    return result


def test_del_document():
    """测试删除文档接口"""
    print_separator("测试11: 删除文档")
    api_url = BASE_URL + 'del_document'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'doc_name': ['屏幕截图(1).png']  # 支持批量删除
    }
    result = post_request(api_url, data)
    return result


def test_search_from_vector_db():
    """测试搜索向量库接口"""
    print_separator("测试12: 搜索向量库（QA类型）")
    api_url = BASE_URL + 'search_from_vector_db'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': 'AI技术',
        'collection_type': 'QA',
        'limit': 5
    }
    result = post_request(api_url, data)
    return result


def test_search_doc():
    """测试搜索文档"""
    print_separator("测试13: 搜索向量库（DOC类型）")
    api_url = BASE_URL + 'search_from_vector_db'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': 'AI技术',
        'collection_type': 'DOC',
        'limit': 5
    }
    result = post_request(api_url, data)
    return result


def test_search_qa_hybrid():
    """测试混合检索（QA类型）"""
    print_separator("测试14: 混合检索（QA类型）")
    api_url = BASE_URL + 'search_from_vector_db'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': 'AI技术',
        'collection_type': 'QA',
        'limit': 5,
        'use_hybrid': True  # 启用混合检索
    }
    result = post_request(api_url, data)
    
    # 显示检索结果详情
    if result and result.get('status') == 'success':
        data_result = result.get('data', {})
        entities = data_result.get('entities', [])
        if entities and len(entities) > 0:
            print(f"\n混合检索结果（共{len(entities[0])}条）:")
            for idx, entity in enumerate(entities[0][:3], 1):  # 只显示前3条
                print(f"\n结果 {idx}:")
                print(f"  问题: {entity.get('question', 'N/A')}")
                print(f"  答案: {entity.get('answer', 'N/A')[:50]}...")
                print(f"  分数: {entity.get('score', 'N/A')}")
                if 'rrf_score' in entity:
                    print(f"  RRF分数: {entity.get('rrf_score', 'N/A')}")
                if 'vector_rank' in entity:
                    print(f"  向量排名: {entity.get('vector_rank', 'N/A')}")
                if 'bm25_rank' in entity:
                    print(f"  BM25排名: {entity.get('bm25_rank', 'N/A')}")
    
    return result


def test_search_doc_hybrid():
    """测试混合检索（DOC类型）"""
    print_separator("测试15: 混合检索（DOC类型）")
    api_url = BASE_URL + 'search_from_vector_db'
    data = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': 'AI技术',
        'collection_type': 'DOC',
        'limit': 5,
        'use_hybrid': True  # 启用混合检索
    }
    result = post_request(api_url, data)
    
    # 显示检索结果详情
    if result and result.get('status') == 'success':
        data_result = result.get('data', {})
        entities = data_result.get('entities', [])
        if entities and len(entities) > 0:
            print(f"\n混合检索结果（共{len(entities[0])}条）:")
            for idx, entity in enumerate(entities[0][:3], 1):  # 只显示前3条
                print(f"\n结果 {idx}:")
                print(f"  文件名: {entity.get('file_name', 'N/A')}")
                print(f"  内容: {entity.get('content', 'N/A')[:100]}...")
                print(f"  分数: {entity.get('score', 'N/A')}")
                if 'rrf_score' in entity:
                    print(f"  RRF分数: {entity.get('rrf_score', 'N/A')}")
                if 'vector_rank' in entity:
                    print(f"  向量排名: {entity.get('vector_rank', 'N/A')}")
                if 'bm25_rank' in entity:
                    print(f"  BM25排名: {entity.get('bm25_rank', 'N/A')}")
    
    return result


def test_compare_vector_vs_hybrid():
    """对比纯向量检索和混合检索的结果"""
    print_separator("测试16: 对比纯向量检索 vs 混合检索")
    api_url = BASE_URL + 'search_from_vector_db'
    query = 'AI技术'
    
    # 纯向量检索
    print("\n【纯向量检索】")
    data_vector = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': query,
        'collection_type': 'DOC',
        'limit': 5,
        'use_hybrid': False
    }
    result_vector = post_request(api_url, data_vector, show_request=False)
    
    # 混合检索
    print("\n【混合检索（向量+BM25）】")
    data_hybrid = {
        'tenant_code': TENANT_CODE,
        'collection_name': COLLECTION_NAME,
        'api_key': API_KEY,
        'query': query,
        'collection_type': 'DOC',
        'limit': 5,
        'use_hybrid': True
    }
    result_hybrid = post_request(api_url, data_hybrid, show_request=False)
    
    # 对比结果
    print("\n【结果对比】")
    if result_vector and result_vector.get('status') == 'success':
        vector_data = result_vector.get('data', {})
        vector_entities = vector_data.get('entities', [])
        if vector_entities and len(vector_entities) > 0:
            print(f"\n纯向量检索返回 {len(vector_entities[0])} 条结果:")
            for idx, entity in enumerate(vector_entities[0][:3], 1):
                score = entity.get('score', 'N/A')
                # 格式化分数
                if isinstance(score, (int, float)):
                    score_str = f"{score:.4f}"
                else:
                    score_str = str(score)
                question = entity.get('question', 'N/A')
                question_display = question[:50] if isinstance(question, str) else str(question)[:50]
                print(f"  {idx}. {question_display}... (分数: {score_str})")
    
    if result_hybrid and result_hybrid.get('status') == 'success':
        hybrid_data = result_hybrid.get('data', {})
        hybrid_entities = hybrid_data.get('entities', [])
        if hybrid_entities and len(hybrid_entities) > 0:
            print(f"\n混合检索返回 {len(hybrid_entities[0])} 条结果:")
            for idx, entity in enumerate(hybrid_entities[0][:3], 1):
                rrf_score = entity.get('rrf_score', 'N/A')
                vector_rank = entity.get('vector_rank', 'N/A')
                bm25_rank = entity.get('bm25_rank', 'N/A')
                # 格式化RRF分数
                if isinstance(rrf_score, (int, float)):
                    rrf_score_str = f"{rrf_score:.4f}"
                else:
                    rrf_score_str = str(rrf_score)
                # 处理question字段（可能是content字段，取决于collection_type）
                question = entity.get('question') or entity.get('content', 'N/A')
                question_display = question[:50] if isinstance(question, str) else str(question)[:50]
                print(f"  {idx}. {question_display}...")
                print(f"     RRF分数: {rrf_score_str}, "
                      f"向量排名: {vector_rank}, BM25排名: {bm25_rank}")
    
    return result_vector, result_hybrid


def run_all_tests():
    """运行所有测试"""
    print_separator("向量数据库接口完整测试")
    print(f"服务地址: {BASE_URL}")
    print(f"租户编码: {TENANT_CODE}")
    print(f"知识库名称: {COLLECTION_NAME}")
    
    # 测试流程
    tests = [
        ("创建知识库", test_new_collection),
        ("添加文档", test_add_document),
        #("批量添加文档", test_add_multi_document),
        ("搜索文档", test_search_doc),
        #("混合检索QA", test_search_qa_hybrid),
        ("混合检索DOC", test_search_doc_hybrid),
        ("对比检索方式", test_compare_vector_vs_hybrid),
        #("删除文档", test_del_document),
        #("删除知识库", test_del_collection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n测试 '{test_name}' 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, None))
    
    # 打印测试总结
    print_separator("测试总结")
    for test_name, result in results:
        if result:
            # 处理返回元组的情况（如test_compare_vector_vs_hybrid）
            if isinstance(result, tuple):
                # 对于对比测试，检查两个结果是否都成功
                result_vector, result_hybrid = result
                if result_vector and result_hybrid:
                    vector_success = result_vector.get('status') == 'success' if isinstance(result_vector, dict) else False
                    hybrid_success = result_hybrid.get('status') == 'success' if isinstance(result_hybrid, dict) else False
                    status = "✓" if (vector_success and hybrid_success) else "✗"
                    print(f"{status} {test_name}: 对比测试完成")
                else:
                    print(f"✗ {test_name}: 对比测试失败")
            elif isinstance(result, dict):
                # 处理返回字典的情况（常规测试）
                status = "✓" if result.get('status') == 'success' else "✗"
                print(f"{status} {test_name}: {result.get('msg', 'N/A')}")
            else:
                print(f"✗ {test_name}: 未知的结果类型")
        else:
            print(f"✗ {test_name}: 测试失败或未执行")


def run_single_test(test_name):
    """运行单个测试"""
    test_map = {
        'new_collection': test_new_collection,
        'add_document': test_add_document,
        'add_multi_document': test_add_multi_document,
        'search_doc': test_search_doc,
        #'del_document': test_del_document,
        #'del_collection': test_del_collection,
        'add_qa': test_add_qa,
        'add_multiple_qa': test_add_multiple_qa,
        #'add_qa_from_template': test_add_qa_from_template,
        #'update_qa': test_update_qa,
        #'del_qa': test_del_qa,
        #'del_multiple_qa': test_del_multiple_qa,
        'search_qa': test_search_from_vector_db,
        'search_qa_hybrid': test_search_qa_hybrid,
        'search_doc_hybrid': test_search_doc_hybrid,
        'compare_hybrid': test_compare_vector_vs_hybrid,
    }
    
    if test_name in test_map:
        test_map[test_name]()
    else:
        print(f"未知的测试名称: {test_name}")
        print(f"可用的测试: {', '.join(test_map.keys())}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 运行指定的测试
        test_name = sys.argv[1]
        run_single_test(test_name)
    else:
        # 运行所有测试
        run_all_tests()
    
    print("\n测试完成！")

