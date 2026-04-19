import base64
import json
import os
from typing import Any

from app.domain.errors import Unauthorized


async def verify_token(token: str) -> dict[str, Any]:
    """v1 的轻量 SSO 校验。

    - `APP_ENV=dev` 且 token 以 `dev.` 起头 → 直接 base64 解码 claims(开发旁路)
    - 否则:用 PyJWT 做非严格 decode(签名校验 TODO,10 章按真实 SSO 协议补齐)

    Claims 至少需要 `sub`(external_id)。
    """
    if os.environ.get("APP_ENV") == "dev" and token.startswith("dev."):
        try:
            payload = token[4:]
            padded = payload + "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(padded))
        except Exception as e:
            raise Unauthorized(f"malformed dev token: {e}") from e
    try:
        import jwt  # type: ignore[import-not-found]

        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        raise Unauthorized(str(e)) from e
