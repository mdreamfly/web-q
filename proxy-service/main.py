"""
Proxy service that forwards requests to SearXNG and Crawl4AI,
with optional response compression via OpenRouter.
"""

import os
import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import httpx

from compressor import compress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:8000")

app = FastAPI(
    title="Search Proxy Service",
    description="Proxy for SearXNG and Crawl4AI with optional LLM compression",
    version="1.0.0"
)


class CrawlRequest(BaseModel):
    url: HttpUrl
    compress: bool = False
    max_tokens: int = 500
    # Pass-through options for Crawl4AI
    extraction_strategy: str = "auto"
    timeout: int = 30
    css_selector: Optional[str] = None
    wait_for: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    searxng: bool
    crawl4ai: bool


@app.get("/health")
async def health_check() -> HealthResponse:
    searxng_ok = False
    crawl4ai_ok = False

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{SEARXNG_URL}/healthz")
            searxng_ok = r.status_code == 200
        except Exception:
            pass

        try:
            r = await client.get(f"{CRAWL4AI_URL}/health")
            crawl4ai_ok = r.status_code == 200
        except Exception:
            pass

    status = "healthy" if (searxng_ok and crawl4ai_ok) else "degraded"
    return HealthResponse(status=status, searxng=searxng_ok, crawl4ai=crawl4ai_ok)


@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    compress_response: bool = Query(False, alias="compress", description="Compress results via LLM"),
    max_tokens: int = Query(500, description="Target tokens for compression"),
    # Pass-through params for SearXNG
    format: str = Query("json", description="Response format"),
    categories: Optional[str] = Query(None, description="Search categories"),
    engines: Optional[str] = Query(None, description="Specific engines"),
    language: str = Query("en", description="Search language"),
    pageno: int = Query(1, description="Page number"),
    time_range: Optional[str] = Query(None, description="Time filter"),
):
    """Proxy search requests to SearXNG with optional compression."""

    params = {
        "q": q,
        "format": format,
        "language": language,
        "pageno": pageno,
    }
    if categories:
        params["categories"] = categories
    if engines:
        params["engines"] = engines
    if time_range:
        params["time_range"] = time_range

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"SearXNG request failed: {e}")
            raise HTTPException(status_code=502, detail=f"SearXNG request failed: {e}")

    data = response.json()

    if compress_response and data.get("results"):
        logger.info(f"Compressing search results to {max_tokens} tokens")
        try:
            raw_content = json.dumps(data["results"], indent=2)
            compressed = await compress(raw_content, max_tokens)
            return JSONResponse({
                "query": data.get("query"),
                "compressed": True,
                "summary": compressed,
                "original_result_count": len(data.get("results", [])),
            })
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise HTTPException(status_code=500, detail=f"Compression failed: {e}")

    return JSONResponse(data)


@app.post("/crawl")
async def crawl(request: CrawlRequest):
    """Proxy crawl requests to Crawl4AI with optional compression."""

    crawl_payload = {
        "url": str(request.url),
        "extraction_strategy": request.extraction_strategy,
        "timeout": request.timeout,
    }
    if request.css_selector:
        crawl_payload["css_selector"] = request.css_selector
    if request.wait_for:
        crawl_payload["wait_for"] = request.wait_for

    async with httpx.AsyncClient(timeout=float(request.timeout + 30)) as client:
        try:
            response = await client.post(
                f"{CRAWL4AI_URL}/crawl",
                json=crawl_payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Crawl4AI request failed: {e}")
            raise HTTPException(status_code=502, detail=f"Crawl4AI request failed: {e}")

    data = response.json()

    if request.compress and data.get("markdown"):
        logger.info(f"Compressing crawl results to {request.max_tokens} tokens")
        try:
            compressed = await compress(data["markdown"], request.max_tokens)
            return JSONResponse({
                "url": str(request.url),
                "compressed": True,
                "summary": compressed,
                "metadata": data.get("metadata", {}),
            })
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise HTTPException(status_code=500, detail=f"Compression failed: {e}")

    return JSONResponse(data)


@app.get("/")
async def root():
    return {
        "name": "Search Proxy Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "search": "/search?q=query[&compress=true&max_tokens=500]",
            "crawl": "/crawl (POST with JSON body)",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
