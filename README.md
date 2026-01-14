# Claude Search Skill

Local web search and scraping infrastructure for Claude Code, using SearXNG + Crawl4AI with optional LLM compression.

## Quick Start

```bash
# Copy env and add your OpenRouter key (optional, for compression)
cp .env.example .env

# Start services
docker compose up -d

# Verify
curl "http://localhost:8001/health"
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Proxy | 8001 | Main endpoint with optional LLM compression |
| SearXNG | 8080 | Meta-search (70+ engines) |
| Crawl4AI | 8000 | Web scraping with Playwright |
| Redis | 6379 | Caching |

## Usage

Use the proxy service (port 8001) for all requests:

```bash
# Search
curl -s "http://localhost:8001/search?q=query&format=json"

# Search with compression (requires OPENROUTER_API_KEY)
curl -s "http://localhost:8001/search?q=query&format=json&compress=true&max_tokens=300"

# Scrape
curl -s -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Scrape with compression
curl -s -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "compress": true, "max_tokens": 500}'
```

## Usage with Claude

Use the `/web-search` skill or ask Claude to search/scrape using the local services.

## Stop

```bash
docker compose down
```

## Attribution

Based on [Bionic-AI-Solutions/open-search](https://github.com/Bionic-AI-Solutions/open-search).
