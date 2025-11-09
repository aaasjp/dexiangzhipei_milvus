import requests
import json

base_url = 'http://127.0.0.1:8005/vector_db_service/'
api_key = '2024_hello_ai'


def post_request(url, data):
    try:
        json_data = json.dumps(data)
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json_data)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()  # 返回JSON格式的响应内容
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"OOps: Something Else: {err}")


def test_new_collection():
    print('测试创建知识库接口')
    api_url = base_url + 'new_collection'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key
    }
    result = post_request(api_url, data)
    print(result)


def test_del_collection():
    print('测试删除知识库接口')
    api_url = base_url + 'del_collection'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key
    }
    result = post_request(api_url, data)
    print(result)


def test_add_qa():
    print('测试插入问答对接口')
    api_url = base_url + 'add_qa'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'question': '1+1=？',
        'answer': '1+1=3',
        'source': '/data/qa/bad_wiki.txt'
    }

    result = post_request(api_url, data)
    print(result)


def test_add_qa_from_template():
    print('测试从模版导入问答对接口')
    api_url = base_url + 'add_qa_from_template'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'template_path': '/data/projects/milvus_service/vector_db_server/data/问答库模板.xlsx',
    }

    result = post_request(api_url, data)
    print(result)


def test_add_document(doc_path):
    print('测试增加文档接口')
    api_url = base_url + 'add_document'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'doc_path': doc_path
    }

    result = post_request(api_url, data)
    print(result)


def test_update_qa():
    print('测试更新问答对接口')
    api_url = base_url + 'update_qa'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'question': '1+1=？',
        'answer': '1+1=2',
        'source': 'data/qa/good_wiki.txt'
    }

    result = post_request(api_url, data)
    print(result)


def test_del_qa():
    print('测试删除问答对接口')
    api_url = base_url + 'del_qa'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'question': '1+1=？',
    }

    result = post_request(api_url, data)
    print(result)


def test_del_qa2():
    print('测试删除问答对接口')
    api_url = base_url + 'del_qa'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'question': 'x+y=1,x=1,y=?',
    }

    result = post_request(api_url, data)
    print(result)


def test_del_document():
    print('测试删除文档接口')
    api_url = base_url + 'del_document'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'doc_name': '智能客服技术汇总',
    }

    result = post_request(api_url, data)
    print(result)


def test_search(query):
    print('测试查询接口')
    api_url = base_url + 'search_from_qa_collection'
    data = {
        'tenant_code': 'xiaomi',
        'collection_name': 'xiaoshou',
        'api_key': api_key,
        'query': query,
        'collection_type': 'DOC'
    }

    result = post_request(api_url, data)
    print(result)


# 使用示例
if __name__ == "__main__":
    # test_new_collection()
    # test_add_qa()
    # test_del_qa()
    # test_del_collection()
    test_add_document('/data/projects/milvus_service/vector_db_server/data/美容产品介绍.pdf')
    test_add_document('/data/projects/milvus_service/vector_db_server/data/威士忌产品知识.pdf')
    test_add_document('/data/projects/milvus_service/vector_db_server/data/智师益友20条快问快答.pdf')
    test_add_document('/data/projects/milvus_service/vector_db_server/data/智师益友产品手册.pdf')
    # test_update_qa()
    # test_add_qa_from_template()
    # test_del_qa()
    # test_search('杭小信')
