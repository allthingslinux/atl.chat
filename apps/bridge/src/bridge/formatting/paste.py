"""Upload code blocks to PrivateBin and return a URL.

Direct PrivateBin v2 API implementation — the `privatebin` PyPI package (0.3.0)
has a serialization bug where enum values are not unwrapped before JSON encoding.
We reuse its crypto primitives but handle serialization ourselves.

Configure the instance URL via `paste_service_url` in config.yaml,
e.g. https://paste.atl.tools/
"""

from __future__ import annotations

import asyncio
import base64
import enum
import functools
import json
import os

import httpx
from loguru import logger

from bridge.config import cfg

_DEFAULT_SERVER = "https://paste.atl.tools/"
_MAX_CHARS = 50_000


def _unwrap(obj: object) -> object:
    """Recursively unwrap enum values and tuples for JSON serialization."""
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (tuple, list)):
        return [_unwrap(i) for i in obj]
    return obj


def _create_paste_sync(content: str, lang: str, server: str) -> str:
    """Synchronous PrivateBin v2 paste creation with correct enum serialization."""
    import base58
    from privatebin._crypto import encrypt
    from privatebin._enums import (
        Compression,
        Expiration,
        Formatter,
        PrivateBinEncryptionSetting,
    )
    from privatebin._models import (
        AuthenticatedData,
        PrivateBinUrl,
    )
    from privatebin._utils import to_compact_jsonb

    formatter = Formatter.SOURCE_CODE if lang else Formatter.PLAIN_TEXT
    compression = Compression.ZLIB
    expiration = Expiration.NEVER

    passphrase = os.urandom(32)
    iv = os.urandom(16)
    salt = os.urandom(8)
    password = b""

    data = {"paste": content}
    encoded_data = to_compact_jsonb(data)

    from privatebin._utils import Compressor

    compressed_data = Compressor(mode=compression).compress(encoded_data)

    adata = AuthenticatedData.new(
        initialization_vector=iv,
        salt=salt,
        formatter=formatter,
        open_discussion=False,
        burn_after_reading=False,
        compresssion=compression,
    )

    encrypted = encrypt(
        data=compressed_data,
        length=PrivateBinEncryptionSetting.KEY_SIZE // 8,
        salt=salt,
        iterations=PrivateBinEncryptionSetting.ITERATIONS,
        key_material=passphrase + password,
        initialization_vector=iv,
        associated_data=adata.to_bytes(),
    )

    # Manually serialize — unwrap all enums to their .value
    raw_tuple = adata.to_serializable_tuple()
    serializable_adata = _unwrap(raw_tuple)

    payload = {
        "v": 2,
        "adata": serializable_adata,
        "ct": base64.b64encode(encrypted).decode(),
        "meta": {"expire": _unwrap(expiration)},
    }

    with httpx.Client(
        headers={
            "X-Requested-With": "JSONHttpRequest",
            "User-Agent": "atl-bridge/1.0",
        }
    ) as client:
        resp = client.post(server, content=json.dumps(payload), headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        result = resp.json()

    if result.get("status") != 0:
        raise RuntimeError(result.get("message", "Unknown PrivateBin error"))

    url = PrivateBinUrl(
        server=server,
        id=result["id"],
        passphrase=base58.b58encode(passphrase).decode(),
    )
    return url.unmask()


async def upload_paste(content: str, lang: str = "") -> str | None:
    """Encrypt and upload content to PrivateBin; return the full URL or None on failure."""
    server = cfg.paste_service_url or _DEFAULT_SERVER

    if len(content) > _MAX_CHARS:
        content = content[:_MAX_CHARS]
        logger.warning("paste: content truncated to {} chars", _MAX_CHARS)

    loop = asyncio.get_event_loop()
    try:
        url = await loop.run_in_executor(
            None,
            functools.partial(_create_paste_sync, content, lang, server),
        )
        logger.info("paste: uploaded to PrivateBin -> {}", url)
        return url
    except Exception as exc:
        logger.warning("paste: PrivateBin upload failed (server={}): {}", server, exc)
        return None
