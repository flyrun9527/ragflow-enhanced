from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.utils import RagflowClient, kb_prompt


class RagflowEnhancedTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        try:
            app_id = str(self.runtime.credentials.get("app_key", ""))
            app_url = str(self.runtime.credentials.get("app_url", ""))

            if not app_id or not app_url:
                yield self.create_text_message('Missing credentials: app_key or app_url')
                return

            client = RagflowClient(app_id, app_url)
            question = str(tool_parameters.get("question", ''))
            datasets_id = str(tool_parameters.get("dataset_ids", ''))
            document_id = str(tool_parameters.get("document_ids", ''))
            page = tool_parameters.get("page", 1)
            page_size = tool_parameters.get("page_size", 30)
            similarity_threshold = tool_parameters.get("similarity_threshold", 0.2)
            vector_similarity_weight = tool_parameters.get("vector_similarity_weight", 0.3)

            if not datasets_id:
                yield self.create_text_message('Dataset id is required')
                return
            
            datasets_ids = datasets_id.split(",")
            if len(datasets_ids) == 0 and datasets_id:
                datasets_ids = [datasets_id]
                
            document_ids = []
            if document_id and document_id.strip() != '':
                document_ids = document_id.split(",")
                if len(document_ids) == 0:
                    document_ids = [document_id]

            parsed_data = {
                "question": question,
                "dataset_ids": datasets_ids,
                "document_ids": document_ids,
                "page": page,
                "page_size": page_size,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight
            }

            res = client.post(route_method='/api/v1/retrieval', data_obj=parsed_data)
            response_json = res.json() if res.status_code == 200 else {}
            data = response_json.get("data", {})
            
            if not data:
                yield self.create_text_message("No data returned from retrieval API")
                return
                
            if not isinstance(data, dict) or "chunks" not in data:
                yield self.create_text_message("Invalid data structure returned from retrieval API")
                return

            knowledge = kb_prompt(data, app_id, app_url)
            
            yield self.create_json_message({
                "result": knowledge
            })
        except Exception as e:
            yield self.create_text_message(f"Retrieval error: {str(e)}")
            return

