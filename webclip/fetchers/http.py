from __future__ import annotations

import httpx

from webclip.fetchers.base import FetchRequest, FetchResult


class HttpFetcher:
    name = "http"

    async def fetch(self, request: FetchRequest) -> FetchResult:
        headers = {"User-Agent": "webclip/0.1 (+https://local.cli)"}
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=headers,
        ) as client:
            response = await client.get(request.url)
            response.raise_for_status()

        return FetchResult(
            url=request.url,
            final_url=str(response.url),
            status_code=response.status_code,
            html=response.text,
        )
