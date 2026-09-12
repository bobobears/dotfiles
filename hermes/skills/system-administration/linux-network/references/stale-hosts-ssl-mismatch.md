# 修复 /etc/hosts 过期固定 IP 导致的 SSL Hostname mismatch（2026-08-27 实战）

## 症状

某服务（本例飞书）突然报：
```
SSLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
Hostname mismatch, certificate is not valid for 'open.feishu.cn'. (_ssl.c:1016)"))
```
- 只在**本机**发生，只针对**一个域名**
- Hermes cron 任务表现为 `last_status: ok` 但 `last_delivery_error` 含上述 SSL 错误
- 其他平台（微信）正常

## 根因

`/etc/hosts` 里有**过期的固定 IP**（之前网络受限时期手动加的 domain→IP 绕过 DNS）。
CDN 节点后来被重新分配，旧 IP 现在后面是别的服务器，证书 hostname 对不上。
DNS 本身没问题。

## 诊断四步（先验证再动手）

```bash
# 1. 系统解析器返回什么（应用实际用的）
getent hosts <domain>

# 2. 干净外部 DNS 返回什么（对比！）
host <domain> 8.8.8.8 | grep "has address"

# 3. 检查 /etc/hosts 里的固定条目
grep -v "^#" /etc/hosts | grep -v "^$"

# 4. 对每个候选 IP 做证书测试，找出真正给正确证书的
python3 -c "
import ssl, socket
for ip in ['IP_A', 'IP_B']:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname='<domain>') as ssock:
                print(f'{ip}: OK cert')
    except Exception as e:
        print(f'{ip}: FAIL {type(e).__name__}: {str(e)[:100]}')
"
```

判定：
- hosts 里有证书测试失败的条目 → **过期固定 IP**，修 hosts
- hosts 无条目且 getent 与解析器返回同样的坏 IP → 路由器/上游 DNS 污染，改用 `resolvectl dns <iface> 8.8.8.8` 覆盖

## 修复

```bash
# 删掉域名所有旧固定条目，写入验证过的好 IP
sudo sed -i '/<domain>/d' /etc/hosts
echo "<GOOD_IP> <domain>" | sudo tee -a /etc/hosts
getent hosts <domain>   # 确认生效
```

**不需要重启服务！** Python requests/urllib 每次连接都重新解析 DNS，下一请求自动用新 hosts 条目。
这避开了"gateway 进程内无法重启 gateway"的陷阱（Hermes 会拦截 systemctl/hermes gateway restart/cron 重启等所有路径）。

## 端到端验证（真实凭据）

```bash
source ~/.hermes/.env
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}"
# code:0 → TLS + API 都通；code:10003 "invalid param" → TLS 通但凭据是假的
```

## 陷阱

- `curl -sI` / `openssl s_client` 遇到黑洞 IP 会挂住——必须 `timeout 10` 包裹
- 修完一个域名后，**检查 /etc/hosts 里其他固定条目**（微信 ilinkai、DeepSeek API 等），可能同样过期只是还没报错；但没报错的**别动**，等它坏了再修
- 重推失败报告时，shell 变量传 JSON 给 curl 会被转义搞坏（`msg_type is required` 之类），**改用 Python urllib 脚本**发送更稳（见本会话 /tmp/resend_feishu.py 模式：token → 分块 → send）
