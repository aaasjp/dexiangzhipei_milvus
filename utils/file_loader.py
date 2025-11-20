import pandas as pd
from docx import Document
import subprocess
from langchain_community.document_loaders import PyPDFLoader
import requests
import json
import logging

logger = logging.getLogger(__name__)


def load_qa_template(template_file_path):
    sheet_name = '问答对数据'
    col_ques_name = '问题'
    col_ans_name = '答案'
    col_source_name = '关联文档名称'

    df = pd.read_excel(template_file_path, sheet_name=sheet_name)
    df = df.fillna('')

    question_list = df[col_ques_name].values
    answers_list = df[col_ans_name].values
    source_list = df[col_source_name].values

    assert len(question_list) == len(answers_list) == len(source_list)
    assert '' not in question_list
    assert '' not in answers_list

    return question_list, answers_list, source_list


def extract_content_from_file(file_url, ocr_config=None):
    """
    通过OCR接口解析文档内容（支持URL链接）
    :param file_url: 文档URL链接
    :param ocr_config: OCR服务配置，包含base_url、parse_mode、timeout等
    :return: (is_success, content_or_error_message)
    """
    if ocr_config is None:
        # 如果没有传入配置，尝试从配置文件读取
        try:
            with open('./config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                ocr_config = config.get('ocr_service', {})
        except Exception as e:
            logger.error(f"读取OCR配置失败: {e}")
            return False, f"OCR配置读取失败: {repr(e)}"
    
    base_url = ocr_config.get('base_url', 'http://localhost:8000')
    parse_mode = ocr_config.get('parse_mode', 'balanced')
    timeout = ocr_config.get('timeout', 300)
    
    # 构建OCR接口URL
    parse_url = f"{base_url.rstrip('/')}/parse"
    
    try:
        # 调用OCR接口解析文档
        payload = {
            "document": file_url,
            "parse_mode": parse_mode,
            "include_raw_result": False
        }
        
        logger.info(f"调用OCR接口解析文档: {parse_url}, 文档URL: {file_url}")
        response = requests.post(parse_url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('success', False):
            text_content = result.get('text_content', '')
            if text_content:
                logger.info(f"OCR解析成功，文档URL: {file_url}")
                return True, text_content
            else:
                logger.warning(f"OCR解析返回内容为空，文档URL: {file_url}")
                return False, "OCR解析返回内容为空"
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"OCR解析失败，文档URL: {file_url}, 错误: {error_msg}")
            return False, f"OCR解析失败: {error_msg}"
            
    except requests.exceptions.Timeout:
        error_msg = f"OCR接口请求超时（超过{timeout}秒）"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"OCR接口请求异常: {repr(e)}"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg
    except Exception as e:
        error_msg = f"解析文档异常: {repr(e)}"
        logger.error(f"{error_msg}, 文档URL: {file_url}")
        return False, error_msg

