# HRMS API 认证与端到端验证模式（2026-08-17）

## 认证方式：Cookie，不是 Token

HRMS **没有** `/api/login` JSON 接口（POST 返回 `{"detail":"Not Found"}`）。登录是表单 POST `/login`，成功返回 **303** 并种 session cookie。后续所有 API/页面请求带同一个 cookie jar 即可。

服务端口为 **8000**（systemd user service `hrms.service`：uvicorn backend.main:app --port 8000）。注意不是 8188/8189——那些是 HRMS 之外的其他服务。

## 标准验证脚本模式

```bash
cd /tmp && rm -f hrms_cookie.txt
# 1) GET /login 建立会话（拿到初始 cookie）
curl -s -c hrms_cookie.txt http://127.0.0.1:8000/login -o /dev/null
# 2) 表单登录，期望 303
curl -s -b hrms_cookie.txt -c hrms_cookie.txt -X POST http://127.0.0.1:8000/login \
     -d 'username=admin&password=admin123' -o /dev/null -w "登录HTTP状态: %{http_code}\n"
# 3) 带 cookie 访问页面/API
curl -s -b hrms_cookie.txt http://127.0.0.1:8000/ -o /tmp/hrms-index.html
```

## 验证页面渲染类修复（不开浏览器）

拿 HTML 后用 Python re 检查目标 DOM：

```python
import re
html = open('/tmp/hrms-index.html').read()
grid = re.search(r'<div class="field-grid" id="fieldGrid">(.*?)</div>', html, re.S)
boxes = re.findall(r'<input type="checkbox" value="([^"]+)" checked> ([^<]+)', grid.group(1))
print(f"字段复选框数量: {len(boxes)}")  # 期望值与 _ALL_EMPLOYEE_FIELDS 长度一致
```

## 验证 Excel 导出类修复

```bash
curl -s -b hrms_cookie.txt "http://127.0.0.1:8000/api/employees/export?fields=name,phone,department" \
     -o /tmp/test.xlsx -w "%{http_code}\n"   # 期望 200
```

```python
from openpyxl import load_workbook
ws = load_workbook('/tmp/test.xlsx').active
rows = list(ws.iter_rows(values_only=True))
print(rows[0])          # 表头应为所选字段的中文标签
print(len(rows) - 1)    # 数据行数
```

验证完成后清理 `/tmp/hrms_cookie.txt`、下载的 xlsx/html。

## 相关陷阱：Jinja2 未定义变量静默跳过循环

页面"某区块缺失且无报错"时，先检查模板 `{% for %}`/`{% if %}` 引用的变量是否都在该路由 `render()` 上下文里（grep 模板变量名对照 render() 实参）。典型案例：导出弹窗字段网格用 `{% for key, label in export_fields %}` 渲染，但首页路由没传 `export_fields` → Jinja2 静默跳过循环，只剩"全选/全不选"。修复：render() 传入 `export_fields=[(k, LABELS.get(k,k)) for k in _ALL_EMPLOYEE_FIELDS]`，标签映射提为模块级 `_EMPLOYEE_FIELD_LABELS`（页面渲染与导出 API 共用单一数据源）。
