# Common HF API / hf-mirror.com Query Patterns

All use `hf-mirror.com` (works from mainland China with no DNS/gateway issues).

## Search by model family
```
curl -sL "https://hf-mirror.com/api/models?search=llama+3.3" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
for m in data[:20]:
    mid = m.get('modelId','')
    likes = m.get('likes',0)
    downloads = m.get('downloads',0)
    print(f'{mid} | likes={likes} downloads={downloads}')
"
```

## Find models in the same size tier (同量级 competitor discovery)

Use multiple search queries to cast a wide net, then deduplicate by size:

```
# Search by param range + architecture
curl -sL "https://hf-mirror.com/api/models?search=moe+30B&sort=likes&limit=15"
curl -sL "https://hf-mirror.com/api/models?search=moe+35B&sort=likes&limit=15"
curl -sL "https://hf-mirror.com/api/models?search=moe+40B&sort=likes&limit=15"

# Search by family name for specific competitors
curl -sL "https://hf-mirror.com/api/models?search=deepseek+coder+v2+moe&sort=likes&limit=10"
curl -sL "https://hf-mirror.com/api/models?search=mixtral+moe&sort=likes&limit=10"
curl -sL "https://hf-mirror.com/api/models?search=nemotron+nano&sort=likes&limit=10"

# Search for GGUF availability
curl -sL "https://hf-mirror.com/api/models?search=Qwen3-Coder+GGUF&sort=likes&limit=5"
```

Handle the response format correctly — the API sometimes returns a dict with 'models' key, sometimes a bare list:

```python
import sys, json
data = json.load(sys.stdin)
if isinstance(data, dict):
    items = data.get('models', [])
elif isinstance(data, list):
    items = data
for m in items:
    if isinstance(m, dict):
        print(m.get('modelId', '?'), 'likes:', m.get('likes', 0))
```

## Check GGUF file size without downloading

Use curl HEAD request to get Content-Length from the GGUF file:

```
curl -sI "https://hf-mirror.com/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/raw/main/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf" 2>&1 | grep -i content-length
```

**Note:** This often returns a small HTML redirect page instead of the real file. Alternative: check the unsloth collection page or the model's `blobs/` listing. Most reliable: check the unsloth/bartowski README which lists the quant options and their file sizes.

## Check if a model version exists
```
curl -sL "https://hf-mirror.com/api/models?search=Qwen3.7+Qwen" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
print(json.dumps([m['modelId'] for m in data], indent=2) if data else 'No results')
"
```

## Get detailed model cardData
```
curl -sL "https://hf-mirror.com/api/models/meta-llama/Llama-3.3-70B-Instruct" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
cd = data.get('cardData', {})
print(f'base_model: {cd.get(\"base_model\")}')
print(f'language: {cd.get(\"language\")}')
print(f'tags: {cd.get(\"tags\")}')
"
```

## Search download-sorted
```
curl -sL "https://hf-mirror.com/models?search=llama3.3&sort=downloads"
```
Parsing HTML — look for `<a>` tags with model IDs, often in format `<org>/<model>`.

## Check community/hub-quantized versions
```
curl -sL "https://hf-mirror.com/api/models?search=llama+3.3+GGUF"
```

## Known limitations
- `api.hf-mirror.com` sometimes returns shortened output (1 line) for search queries
- `hf-mirror.com/<org>` org page may not list all models (e.g. meta-llama page doesn't show Llama 3.3)
- Direct README URL is the most reliable source when it works
- Use `timeout 15` (not 10) for slow mirror responses
- Background: `google/bing search from China often time out — skip them and rely on hf-mirror + GitHub raw content
