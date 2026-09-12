# 路由不注册调试记录

## 场景
在 HRMS FastAPI 项目中新增 `/salary/basics` 路由（行内编辑薪酬参数），访问返回 422，OpenAPI 中找不到该路由。

## 错误现象

```
GET /salary/basics → HTTP 422
{"detail":[{"type":"int_parsing","loc":["path","sheet_id"],
  "msg":"Input should be a valid integer, unable to parse string as an integer",
  "input":"basics"}]}
```

这说明路由被 `/salary/{sheet_id}`（期待 int）错误捕获了。

## 根源

`main.py` 第 757 行：
```python
from contract_templates.contracts_template import TEMPLATES, render_contract
```

`contract_templates/` 目录之前被删除过，`ModuleNotFoundError` 导致 Python 在导入到此行时中止。**该行之后的所有路由装饰器（包括 `@app.get("/salary/basics")`）从未执行**，所以：

- OpenAPI 中没有 `/salary/basics`
- `uvicorn` 仍能启动（之前注册的路由还在运行）
- 旧的路由 `/salary/{sheet_id}` 捕获了 `/salary/basics` 的请求

## 调试命令

```bash
# 检查 OpenAPI 路由表 — 看是否有 /salary/basics
python3 -c "
import http.client, json
conn = http.client.HTTPConnection('192.168.31.149', 8000, timeout=10)
conn.request('GET', '/openapi.json')
r = conn.getresponse()
paths = json.loads(r.read().decode())['paths']
for p in sorted(paths):
    if 'salary' in p or 'basics' in p:
        print(p)
"

# 检查 uvicorn 启动日志（如果是 background 进程）
process(action='log', session_id='xxx')

# 验证 main.py 能否完整加载
cd /home/bobobears/hrms/backend && python3 -c "from main import app; print('OK')"

# 查找 main.py 中的 import 语句
grep -n "^from\|^import" backend/main.py | head -20
```

## 修复

重建缺失的 `contract_templates/contracts_template.py` 模块。根据现有代码中的使用方式推断接口：

```python
# contracts_template.py 所需的接口：
# TEMPLATES: dict[str, str] — 合同类型 → Jinja2 模板字符串
# render_contract(contract_type: str, variables: dict) -> str — 渲染合同 HTML
```

可从 `main.py` 中 `render_contract()` 的调用处反向推导所需参数：
- `contract["contract_type"]` → 合同类型
- 变量字典包含：name, phone, id_card, position, employment_type, start_date, end_date, probation_start, probation_end, work_hours_weekly, probation_salary, formal_salary, signed_date, pay_day
