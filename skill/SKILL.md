---
name: web-search
description: Efficiently search the web and scrape pages using local SearXNG + Crawl4AI services, with natural language responses and optional compression
---

# Web Search & Scrape (Local Services)

Search the web and scrape page content using locally-running services via a proxy on port 8001.

## Prerequisites

Docker services must be running:

```bash
cd ~/Codings/Ai/claude-search-skill && docker compose up -d
```

Services:
- Proxy: http://localhost:8001 (use this for all requests)
- SearXNG: http://localhost:8080 (direct, don't use normally)
- Crawl4AI: http://localhost:8000 (direct, don't use normally)

## Important Notes

- **Always use `--noproxy '*'`** in all curl commands to avoid SOCKS/HTTP proxy interference.
- **Chinese and non-ASCII queries are supported** — the proxy automatically handles URL encoding and character set conversion (GBK→UTF-8).
- **URL-encode query parameters** — use `%XX` encoding for non-ASCII characters or `+` for spaces. For Chinese text, properly percent-encode the UTF-8 bytes (e.g., `今天` → `%E4%BB%8A%E5%A4%A9`).
- **Default search language is `auto`** — for Chinese queries, add `&language=zh-CN` for best results.

## Search the Web

```bash
curl -s --noproxy '*' "http://localhost:8001/search?q=QUERY&format=json" | jq '.results[:10] | .[] | {title, url, content}'
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `q` | (required) | Search query (URL-encoded) |
| `format` | `json` | Response format |
| `compress` | `false` | Set to `true` to have LLM summarize results |
| `instruction` | `summarize briefly` | Natural language instruction for LLM compression |
| `language` | `auto` | Search language. Use `zh-CN` for Chinese queries |
| `categories` | (all) | Filter: `general`, `images`, `news`, `videos`, `music`, `map`, `it`, `science`, `files`, `social media` |
| `engines` | (all) | Specific engines (comma-separated). See Available Engines below |
| `pageno` | `1` | Page number |
| `time_range` | (none) | Time filter: `day`, `week`, `month`, `year` |

### Available Engines

| Category | Engines |
|---|---|
| General (Web) | `google`, `bing`, `duckduckgo`, `brave`, `startpage` |
| General (中文) | `baidu`, `sogou`, `360search`, `quark` |
| General (其他) | `wikipedia`, `wikidata`, `currency`, `dictzone` |
| Images | `google images`, `bing images`, `duckduckgo images`, `baidu images`, `sogou images`, `quark images`, `flickr`, `unsplash`, `pinterest` |
| Videos | `google videos`, `bing videos`, `duckduckgo videos`, `youtube`, `dailymotion`, `bilibili`, `acfun`, `iqiyi`, `sogou videos`, `vimeo`, `sepiasearch` |
| News | `google news`, `bing news`, `duckduckgo news`, `brave.news`, `yahoo news`, `wikinews`, `sogou wechat`, `reuters` |
| IT | `github`, `stackoverflow`, `docker hub`, `pypi`, `npm`, `mdn`, `arch linux wiki`, `mankier`, `baidu kaifa` |

### Response Format

**Without compression** (`compress=false` or omitted):
```json
{
  "query": "search terms",
  "results": [
    {"url": "...", "title": "...", "content": "snippet...", "engine": "google", ...}
  ],
  "suggestions": ["..."],
  "number_of_results": 0
}
```

**With compression** (`compress=true`):
```json
{
  "query": "search terms",
  "compressed": true,
  "instruction": "summarize briefly",
  "result": "LLM-generated summary text",
  "original_result_count": 20
}
```

**Compression timeout fallback** (LLM takes >15s):
```json
{
  "query": "search terms",
  "compressed": false,
  "timeout": true,
  "note": "LLM compression timed out, returning raw results",
  "results": [
    {"title": "...", "url": "...", "content": "..."}
  ],
  "original_result_count": 20
}
```

### Search Examples

```bash
# Basic search (English)
curl -s --noproxy '*' "http://localhost:8001/search?q=rust+async+tutorial&format=json" | jq '.results[:10]'

# Chinese search — always add language=zh-CN for best results
curl -s --noproxy '*' "http://localhost:8001/search?q=%E4%BB%8A%E5%A4%A9A%E8%82%A1%E8%A1%8C%E6%83%85&format=json&language=zh-CN" | jq '.results[:10]'

# Compressed search with natural language instruction
curl -s --noproxy '*' "http://localhost:8001/search?q=rust+async+tutorial&format=json&compress=true&instruction=summarize+the+top+results+with+links"

# Chinese compressed search
curl -s --noproxy '*' "http://localhost:8001/search?q=%E4%B8%8A%E8%AF%81%E6%8C%87%E6%95%B0+%E4%BB%8A%E6%97%A5%E8%A1%8C%E6%83%85&format=json&language=zh-CN&compress=true&instruction=%E6%8F%90%E5%8F%96%E4%B8%8A%E8%AF%81%E6%8C%87%E6%95%B0%E7%9A%84%E5%85%B7%E4%BD%93%E6%95%B0%E6%8D%AE"

# Detailed compression
curl -s --noproxy '*' "http://localhost:8001/search?q=weather+london&format=json&compress=true&instruction=extract+temperature+and+conditions+for+today+and+tomorrow"

# Page 2 of results
curl -s --noproxy '*' "http://localhost:8001/search?q=query&format=json&pageno=2" | jq '.results'

# Search specific category (general, images, news, videos, music, it, science, files)
curl -s --noproxy '*' "http://localhost:8001/search?q=query&format=json&categories=news" | jq '.results'

# Search specific engine(s)
curl -s --noproxy '*' "http://localhost:8001/search?q=query&format=json&engines=google,bing" | jq '.results'

# 中文视频搜索 (bilibili, acfun, iqiyi)
curl -s --noproxy '*' "http://localhost:8001/search?q=%E7%BC%96%E7%A8%8B%E6%95%99%E7%A8%8B&format=json&categories=videos&language=zh-CN" | jq '.results'

# 微信公众号文章搜索 (sogou wechat)
curl -s --noproxy '*' "http://localhost:8001/search?q=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&format=json&engines=sogou+wechat&language=zh-CN" | jq '.results'

# IT 技术搜索 (github, stackoverflow, pypi)
curl -s --noproxy '*' "http://localhost:8001/search?q=fastapi+websocket&format=json&categories=it" | jq '.results'

# Time filter (day, week, month, year)
curl -s --noproxy '*' "http://localhost:8001/search?q=query&format=json&time_range=week" | jq '.results'
```

## Scrape a URL

Use this to get full page content (not just search snippets). This is essential when search results don't contain enough detail.

```bash
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq '.markdown'
```

Add `"compress": true, "instruction": "your instruction"` to the JSON body to have the LLM process the page content.

### Scrape Examples

```bash
# Full response with metadata
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq '{markdown, metadata, links}'

# Compressed scrape with brief summary
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "compress": true, "instruction": "brief summary"}'

# Compressed scrape with detailed extraction
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://docs.example.com", "compress": true, "instruction": "extract all API endpoints and their parameters"}'

# Target specific CSS selector
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "css_selector": "article"}' | jq '.markdown'

# Longer timeout for slow sites
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "timeout": 60}' | jq '.markdown'
```

## Common Workflows

### Search → Crawl (for detailed data)

When search results only provide summaries (e.g. stock prices, detailed articles), use a two-step approach:

1. **Search** to find relevant URLs:
```bash
curl -s --noproxy '*' "http://localhost:8001/search?q=QUERY&format=json&language=zh-CN" | jq '.results[:5] | .[] | {title, url}'
```

2. **Crawl** the most relevant URL for full content:
```bash
curl -s --noproxy '*' -X POST "http://localhost:8001/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "BEST_URL_FROM_SEARCH", "compress": true, "instruction": "extract specific data you need"}'
```

### Real-time Data Queries (stock prices, weather, sports scores)

Search snippets rarely contain complete real-time data. For these:
- Use specific, data-oriented search terms (e.g. `上证指数 今日行情 开盘 收盘` instead of just `上证指数`)
- Add `language=zh-CN` for Chinese financial data
- Consider crawling financial data sites directly for structured data

## Search Tips

- **Be specific**: `python asyncio tutorial beginner 2024` > `python async`
- **Use Chinese for Chinese content**: Add `&language=zh-CN` for Chinese queries
- **Compression instructions matter**: Be specific about what you want extracted
  - Good: `extract all prices and product names with URLs`
  - Bad: `summarize`
- **Use time_range for recent info**: `&time_range=day` for today's news
- **Combine search + crawl**: Search finds URLs, crawl gets full content

## Performance Expectations

| Operation | Typical Time | Notes |
|---|---|---|
| Search (no compress) | 1-2s | SearXNG query only |
| Search + compress | 3-8s | Adds LLM processing |
| Compress timeout | 15s max | Falls back to slim results if LLM is slow |
| Crawl (no compress) | 3-10s | Depends on target site |
| Crawl + compress | 5-15s | Depends on page size + LLM |

## Health Check

```bash
curl -s --noproxy '*' "http://localhost:8001/health" | jq
```

## Troubleshooting

```bash
# Check container status
docker ps | grep -E "searxng|crawl4ai|redis|proxy"

# Restart services
cd ~/Codings/Ai/claude-search-skill && docker compose restart

# View logs
docker logs search-proxy
docker logs searxng
docker logs crawl4ai-service
```

### Common Issues

- **ECONNRESET / Empty reply**: System HTTP proxy interfering → ensure `--noproxy '*'` is used
- **Garbled Chinese in results**: SearXNG language not set → add `&language=zh-CN` to query
- **"LLM compression timed out"**: The LLM API was slow → results are returned without compression, still usable
- **No relevant results for Chinese queries**: Use `language=zh-CN` parameter

## When to Use This

- Searching for current information beyond your knowledge cutoff
- Getting full content from a URL (not just snippets)
- Researching topics that need multiple sources
- Scraping JavaScript-heavy sites that WebFetch can't handle
- Use compression with specific instructions to control how much detail you get back
- **Use Search→Crawl workflow** when you need detailed data that search snippets don't contain
