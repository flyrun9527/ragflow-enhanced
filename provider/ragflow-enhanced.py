from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.utils import auth


class RagflowApiProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            app_url = credentials.get("app_url", "")
            app_key = credentials.get("app_key", "")
            
            if not app_url or not app_key:
                raise ToolProviderCredentialValidationError("App URL and App Key are required")
            
            # 确保URL格式正确
            if not app_url.startswith(('http://', 'https://')):
                raise ToolProviderCredentialValidationError("App URL must start with http:// or https://")
            
            auth(credentials)
        except Exception as e:
            raise ToolProviderCredentialValidationError(f"Credential validation error: {str(e)}")
