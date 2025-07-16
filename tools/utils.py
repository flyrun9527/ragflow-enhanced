import logging
import os
import re
from collections import defaultdict

import requests
import tiktoken
import urllib.parse

from dify_plugin.errors.tool import ToolProviderCredentialValidationError


# 设置缓存目录（可选，但推荐）
def get_project_base_directory():
    # 实现获取项目基础目录的函数
    # 可以简单地使用当前工作目录
    return os.getcwd()

tiktoken_cache_dir = get_project_base_directory()
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# 获取编码器
encoder = tiktoken.get_encoding("cl100k_base")


def kb_prompt(kbinfos,app_id,app_url):
    """
    根据检索内容，拼接提示词信息
    :param kbinfos: 检索结果
    :param max_tokens:
    :return:
    """

    knowledges = [ck["content"] for ck in kbinfos["chunks"]]
    chunks_num = len(knowledges)

    client = RagflowClient(app_id, app_url)
    parsed_data = {
        "doc_ids": [ck["document_id"] for ck in kbinfos["chunks"][:chunks_num]]
    }
    # print(parsed_data)
    res = client.post(route_method='/v1/api/document/infos', data_obj=parsed_data)
    # print(res.json())
    docs_data = res.json().get("data", [])
    docs = {}
    if isinstance(docs_data, list):
        docs = {d.get('id', ''): d.get('meta_fields', {}) for d in docs_data if isinstance(d, dict)}

    doc2chunks = defaultdict(lambda: {"chunks": [], "meta": []})
    for i, ck in enumerate(kbinfos["chunks"][:chunks_num]):
        cnt = f"---\nID: {i}\n" + (f"URL: {ck['url']}\n" if "url" in ck else "")
        cnt += re.sub(r"( style=\"[^\"]+\"|</?(html|body|head|title)>|<!DOCTYPE html>)", " ", ck["content"], flags=re.DOTALL|re.IGNORECASE)
        doc2chunks[ck["document_keyword"]]["chunks"].append(cnt)
        doc2chunks[ck["document_keyword"]]["meta"] = docs.get(ck["document_id"], {})

    knowledges = []
    for nm, cks_meta in doc2chunks.items():
        txt = f"\nDocument: {nm} \n"
        for k, v in cks_meta["meta"].items():
            txt += f"{k}: {v}\n"
        txt += "Relevant fragments as following:\n"
        for i, chunk in enumerate(cks_meta["chunks"], 1):
            txt += f"{chunk}\n"
        knowledges.append(txt)
    return knowledges

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        return len(encoder.encode(string))
    except Exception:
        return 0

class RagflowClient:
    """RagFlow接口的處理器"""

    def __init__(self, app_key: str = '', app_url: str = ''):
        self.base_url = app_url
        self.app_id = app_key

    @property
    def get_app_id(self):
        return self.app_id

    def get_header(self):
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.app_id,
        }

    def post(self, route_method, data_obj=None, params=None):
        """
        請求方法
        @param route_method: 路由方法
        @param kwargs: 傳送的業務資料
        @return:
        """
        if params is None:
            params = {}
        if data_obj is None:
            data_obj = {}
        url = self.base_url + route_method
        # 如果params有值，則將params轉為url參數
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        return requests.post(
            url=url,
            headers=self.get_header(),
            json=data_obj,
            verify=False
        )

    def get(self, route_method, params=None):
        """
        請求方法
        @param route_method: 路由方法
        @param kwargs: 傳送的業務資料
        @return:
        """
        if params is None:
            params = {}
        url = self.base_url + route_method
        # 如果params有值，則將params轉為url參數
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        return requests.get(
            url=url,
            headers=self.get_header(),
            verify=False
        )
def auth(credentials):
    app_url = credentials.get("app_url", "")
    app_key = credentials.get("app_key", "")
    
    if not app_key or not app_url:
        raise ToolProviderCredentialValidationError("App Key and URL are required")
    
    try:
        client = RagflowClient(app_key, app_url)
        # 简单的连接测试，使用GET请求验证连接性
        response = client.get('/api/v1/health')
        if response.status_code != 200:
            raise ToolProviderCredentialValidationError(f"API connection failed with status code: {response.status_code}")
    except requests.RequestException as e:
        raise ToolProviderCredentialValidationError(f"Connection error: {str(e)}")
    except Exception as e:
        raise ToolProviderCredentialValidationError(str(e))
