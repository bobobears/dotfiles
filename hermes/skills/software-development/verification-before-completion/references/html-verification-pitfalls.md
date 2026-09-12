# HTML 验证常见假阳性陷阱

验证 HTML 渲染结果时，测试脚本自身可能产生假阳性。以下是经过实战验证的陷阱及其规避方法。

## 1. `display:none` 检测窗口过宽

### 问题
```python
# ❌ 取前 200 字符作上下文 — 可能包含邻近元素的 display:none
if 'display:none' not in html[m.start()-200:m.end()]:
```

当多个导航按钮相邻时，检测窗口覆盖了前一个按钮的 `style="display:none"`。

### 修复
```python
# ✅ 仅取前 5 字符（紧贴标签名）
if 'display:none' not in html[max(0,m.start()-5):m.end()]:
```

### 根因
CSS（`display:none`）是 `style` 属性写在 `<a>` 标签上的，属于同一个标签。但窗口过大时，会看到上一个相邻标签的 `display:none`。窗口只需要覆盖 `<a ... style="display:none">` 即可。

## 2. emoji 前缀 vs 纯文本

### 问题
首页导航链接用 emoji 前缀：
```html
<a href="/contracts" ...>📄 合同管理</a>
```
其他页面（salary_list.html, salary_standards.html）的导航链接用纯文本：
```html
<a href="/contracts">合同管理</a>
```

如果用 `📄 合同管理` 做正则匹配，会在非首页全部漏掉。

### 修复
```python
def has_visible_contract(html: str) -> bool:
    for text in ('📄 合同管理', '合同管理'):  # 同时匹配两种格式
        ...
```

### 经验
页面模板可能来自不同开发阶段，链接样式不一致。**验证脚本必须覆盖所有已知格式变体。**

## 3. CSS 定义中的 class 名称被误匹配

### 问题
```python
# 在 <style> 中找 header-nav → 在 CSS 定义中找到了 class 名
re.findall(r'header-nav', html)  # 匹配了 class 定义而非 HTML 元素
```

CSS 定义和 HTML 元素使用相同的 class 字符串，用简单文本搜索会混淆。

### 修复
搜索 HTML 结构而非文本：先跳过 `<style>...</style>` 块，或在 `<a>` 标签层面匹配。

## 4. 多个相同 class 的按钮被重复匹配

### 问题
首页导航按钮和每位员工行尾的"编辑"、"删除"按钮都用了 `btn-outline btn-sm`：
```python
re.findall(r'<a [^>]*class="btn btn-outline btn-sm"[^>]*>([^<]+)</a>', html)
# 返回：['📥 导出 Excel', '📄 合同管理', '💰 薪资标准', ..., '编辑', '编辑', '编辑', ...]
```

### 修复
过滤只取目标导航按钮：
```python
TARGET = {'👥 用户管理', '📄 合同管理', '💰 薪资标准', '📋 工资表', '🔑 账户'}
visible = [l for l in links if l.strip() in TARGET]
```

## 5. 渲染结果与代码逻辑不符却怀疑代码

### 模式
当验证显示异常时：
1. ✅ 先检查 token/cookie 是否过期（`_active_tokens` 在内存中，重启后会清除）
2. ✅ 再检查数据库权限值是否被前次测试污染（用 `sqlite3` 直查确认）
3. ✅ 再检查 uvicorn 是否重启过（模板修改不需要重启，但路由修改需要）
4. ✅ 最后检查测试脚本本身是否有上述陷阱

**排序原则：** 测试脚本缺陷 > 代码逻辑缺陷，因为验证工具代码通常是跑完即扔的临时脚本，更容易有 bug。
