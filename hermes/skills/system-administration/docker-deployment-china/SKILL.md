---
name: docker-deployment-china
description: >-
  Deploy Docker containers from mainland China — Docker Hub mirror configuration,
  image pull workarounds, volume permission fixes, and China-network service
  configuration. Covers Ubuntu 24.04+ ARM64/x86_64.
---

# Docker Deployment in China (Mainland Network)

Deploy Docker containers when Docker Hub is unreachable or severely throttled
from mainland China. Covers mirror setup, image acquisition, volume permission
fixes, and China-network service configuration.

## 1. Docker Hub Mirror Configuration

### Problem
`docker pull` fails with `lookup registry-1.docker.io: server misbehaving` — DNS resolution blocked in China.

### Fix: Configure registry mirrors

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://hub.rat.dev",
    "https://docker.xuanyuan.me"
  ]
}
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
```

### Verify
```bash
docker info 2>&1 | grep -A3 "Registry Mirrors"
```

### Mirror reliability
Mirrors go down periodically. If one fails, Docker tries the next. Update the list when mirrors stop working — common ones include:
- `docker.1ms.run` (usually reliable)
- `hub.rat.dev`
- `docker.xuanyuan.me`
- `mirror.ccs.tencentyun.com` (Tencent)
- `registry.docker-cn.com` (official, often down)

## 2. Image Pull Strategies (when mirrors fail)

### Strategy A: Mirror retry
Try multiple mirrors in sequence:
```bash
for mirror in docker.1ms.run hub.rat.dev docker.xuanyuan.me; do
  echo "Trying $mirror..."
  docker pull "${mirror}/searxng/searxng:latest" 2>/dev/null && break
done
```

### Strategy B: Pull via proxy
If a local HTTP proxy is running (Clash Verge, v2rayA, Hiddify):
```bash
# Configure Docker to use system proxy
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf <<'EOF'
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
```

### Strategy C: Save/load from another machine
```bash
# On a machine with Docker Hub access
docker save -o image.tar searxng/searxng:latest
# Transfer via scp/rsync, then on target:
docker load -i image.tar
```

## 3. Volume Permission Pitfalls

### Problem
Container crashes with `Permission denied` when writing to mounted volumes.
SearXNG uses container UID 977; other containers use different UIDs.

### Fix: Set ownership before first run
```bash
# Find the container's UID
docker run --rm --entrypoint id searxng/searxng:latest
# Output: uid=977(searxng) gid=977(searxng)

# Set ownership
mkdir -p ~/searxng/data
sudo chown -R 977:977 ~/searxng/data
```

### Alternative: Use chmod 777 (less secure but simpler)
```bash
sudo chmod -R 777 ~/searxng/data
```

### Common container UIDs
| Service | UID:GID |
|---------|---------|
| SearXNG | 977:977 |
| Nginx | 101:101 |
| Redis | 999:999 |
| PostgreSQL | 999:999 |
| MongoDB | 999:999 |

## 4. China-Network Service Configuration

### Problem
Services like SearXNG that aggregate foreign search engines time out from China.

### Fix: Configure China-available engines only
For SearXNG (`settings.yml`):
```yaml
engines:
  - name: baidu
    engine: baidu
    disabled: false
  - name: sogou
    engine: sogou
    disabled: false
  - name: 360search
    engine: generic_json
    disabled: false
  - name: quark
    engine: quark
    disabled: false
  - name: bilibili
    engine: bilibili
    disabled: false
  - name: github
    engine: github
    disabled: false
```

### Enable JSON API (SearXNG)
```yaml
search:
  formats:
    - html
    - json
```

### Bing 中国版 (cn.bing.com) 配置
SearXNG 内置 Bing 引擎默认指向 `www.bing.com`（国际版），国内无法访问。通过 `base_url` 参数覆盖为中国版：
```yaml
engines:
  - name: bing
    engine: bing
    base_url: https://cn.bing.com
    disabled: false
  - name: bing images
    engine: bing_images
    base_url: https://cn.bing.com
    disabled: false
  - name: bing videos
    engine: bing_videos
    base_url: https://cn.bing.com
    disabled: false
  - name: bing news
    engine: bing_news
    base_url: https://cn.bing.com
    disabled: false
```
**注意**：`base_url` 放在引擎配置层级（与 `engine` 同级），**不是**放在 `args` 下。

### Container DNS 不稳定
Docker 容器默认继承宿主机 DNS（如 `192.168.31.1`），在国内网络下可能出现间歇性 `Temporary failure in name resolution` 错误。

**修复**：在 `docker-compose.yml` 中显式指定国内 DNS：
```yaml
services:
  your-service:
    dns:
      - 223.5.5.5      # 阿里云 DNS
      - 114.114.114.114 # 114 DNS
```
修改后需要 `docker compose down && docker compose up -d` 重建容器才能生效。

## 5. Deployment Checklist

1. [ ] Docker Hub mirrors configured (`/etc/docker/daemon.json`)
2. [ ] Docker restarted after mirror config
3. [ ] Image pulled successfully (`docker images | grep <name>`)
4. [ ] Volume directory created with correct ownership
5. [ ] Service-specific config adapted for China network
6. [ ] Container started and health-checked
7. [ ] API/service endpoint verified with curl

## 6. Common Commands

```bash
# Check container status
docker ps --filter name=<container>

# View logs
docker logs <container> --tail 50

# Restart
docker restart <container>

# Stop and remove
docker stop <container> && docker rm <container>

# Check image architecture
docker inspect <image> --format '{{.Architecture}}'
```

## Pitfalls

- **`docker compose up -d` blocked by Hermes terminal** — use `docker run -d` directly instead
- **Mirrors go down** — always have 2-3 mirrors configured; update when they stop working
- **Container UID mismatch** — check `docker run --rm --entrypoint id <image>` before creating volumes
- **JSON API disabled by default** — many services (SearXNG) require explicit config to enable JSON endpoints
- **Foreign services time out** — SearXNG, Wikipedia APIs, and other services accessing Google/Bing/DuckDuckGo will fail without a proxy
- **Container DNS intermittent failures** — Docker inherits host DNS which can be unstable in China; fix by adding `dns: [223.5.5.5, 114.114.114.114]` to docker-compose.yml
- **Bing engines default to international version** — SearXNG's `bing` engine hits `www.bing.com` (blocked in China); override with `base_url: https://cn.bing.com` at engine config level (not under `args`)
- **`docker compose down` may silently fail to remove containers** — if `docker compose up -d` reports name conflict, manually run `docker stop <name> && docker rm <name>` first
- **ARM64 vs x86_64** — verify image architecture matches host; some images don't support ARM64
