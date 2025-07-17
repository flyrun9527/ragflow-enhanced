from collections.abc import Generator
import json
import re
from typing import Any
from collections import defaultdict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.utils import RagflowClient


class RagflowEnhancedTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        try:
            app_id = str(self.runtime.credentials.get("app_key", ""))
            app_url = str(self.runtime.credentials.get("app_url", ""))

            if not app_id or not app_url:
                yield self.create_text_message('Missing credentials: app_key or app_url')
                return

            client = RagflowClient(app_id, app_url)
            chunks = json.loads(tool_parameters.get("chunks", "[]"))
            chunks_num = len(chunks)

            parsed_data = {
                "doc_ids": [ck["document_id"] for ck in chunks[:chunks_num]]
            }
            res = client.post(  route_method='/v1/api/document/infos', data_obj=parsed_data)
            docs_data = res.json().get("data", [])
            docs = {}
            if isinstance(docs_data, list):
                docs = {d.get('id', ''): d.get('meta_fields', {}) for d in docs_data if isinstance(d, dict)}

            doc2chunks = defaultdict(lambda: {"chunks": [], "meta": []})
            for i, ck in enumerate(chunks[:chunks_num]):
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
            
            yield self.create_json_message({
                "knowledges": knowledges,
                "docs_data": docs_data
            })
        except Exception as e:
            yield self.create_text_message(f"Retrieval error: {str(e)}")
            return

