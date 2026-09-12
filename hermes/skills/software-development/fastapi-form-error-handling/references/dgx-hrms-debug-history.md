# 本地面板（DGX HRMS）排查记录

## 背景
- 系统：FastAPI + Jinja2 + SQLite + openpyxl
- 用户登录 admin/editor/viewer 角色，session token 认证
- 员工表单有 63 列字段，部分字段在前端已被删除但后端仍是必填

## 遇到的错误

### 1. [object Object]
**现象**：表单提交失败，右上角红叉提示 `[object Object]`
**根因**：fastapi validation error 的 `detail` 是数组 `[{"loc":[...], "msg":"Field required", "type":"missing"}]`，JavaScript 中直接 `result.detail.toString()` 或字符串拼接导致 `[object Object]`
**修复**：判断 `Array.isArray(result.detail)`，每个元素取 `e.loc` 字段名 + `e.type` 翻译成中文

### 2. {file required}
**现象**：同上，提示变为 `{file required}{file...`
**根因**：只用了 `e.msg`（英文 `Field required`），且类型对应 `missing`/`string_type` 未处理
**修复**：在 `typeLabel` 映射中加入 `missing` → `缺少` 等中文映射

### 3. 提交后提示 department:缺少;position:缺少;...
**现象**：翻译生效后，提示具体的字段名和"缺少"，但该字段网页表单上已没有
**根因**：前端在`组织归属调整`修改中删除了 department/position/hire_date/employment_type 四个字段，但后端 `EmployeeCreate` 模型仍是 `str` 必填
**修复**：后端改为 `Optional[str] = ""`

### 4. oninput 冲突（上一次对话）
**现象**：身份证号字段有 `oninput="this.value.replace(/\D/g,'')"`，提交后返回空白值
**根因**：oninput 清除非数字字符后，FastAPI 收到空字符串，产生 validation error；同时和表单提交的事件循环冲突
**修复**：将 `oninput` 改为 `onchange`，仅在输入完成后联动
