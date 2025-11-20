import json
##加载配置文件
with open('./config/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

def check_api_key(api_key):
    auth_api_key = config['api_key']
    if auth_api_key == api_key:
        return True
    else:
        return False
