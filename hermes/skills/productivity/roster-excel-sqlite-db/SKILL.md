---
name: roster-excel-sqlite-db
description: 从名册 Excel（含身份证号）建立并维护本地 SQLite 管理数据库时使用。
---

# 名册 Excel → 本地 SQLite 管理库

从中文单位导出的名册/花名册 Excel（.xls/.xlsx，含身份证号）建立可长期维护的本地 SQLite 数据库：校验、幂等导入、审计留痕、CLI 管理。适用于患者名册、员工花名册、公卫台账等周期性更新的名单数据。

## 何时使用
- 用户给一份名册 Excel，要求"建个库/数据库来管理"
- 收到新一期同名册导出，需要更新已有库（幂等 upsert）
- 名单含身份证号且需要校验、去重、推导性别/出生日期

## 工作流

### 1. 先探查文件结构，不要假设表头位置
```bash
file <path>   # .xls = Composite Document(旧格式, xlrd); .xlsx = Zip
python3 -c "import pandas as pd; df=pd.read_excel('<path>', header=None); print(df.shape)"
# 打印前 5-6 行（不截断），确认：标题行 / 表头行 / 选项说明行 / 数据起始行
```
中文单位导出的表格常见结构：**第1行大标题、第2行表头、第3行"选择：是/否…"选项说明、第4行起才是数据**。表头单元格可能含换行符（`'分色定级情况\n'`），需 strip。

### 2. 解析时显式赋列名
```python
df = pd.read_excel(path, sheet_name=0, header=None)
df.columns = [c for c in COLMAP]   # ← 必须！否则 raw[col] 全部 KeyError（每行×每列报错，极易误判为文件损坏）
for i, raw in df.iloc[DATA_START:].iterrows(): ...
```

### 3. 身份证校验 + 推导（18位）
```python
def id_checksum_ok(s):
    w = [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]
    cks = "10X98765432"
    return cks[sum(int(c)*wi for c, wi in zip(s[:17], w)) % 11] == s[-1].upper()
# gender: int(idc[16]) % 2 → 奇男偶女; birth: idc[6:14] → YYYY-MM-DD
```
导入前全量校验：格式 `^\d{17}[\dXx]$` + 校验位；不合格行列出原因跳过，不中断整批。

### 4. Schema 三件套（敏感名单标配）
- **主表** patients/roster：业务字段 + `id_card UNIQUE` + created_at/updated_at
- **change_log**：patient_id, name(冗余), action(import/update/delete), field, old_value, new_value, source_file — 每次修改留痕，满足管理可追溯要求
- **import_log**：source_file, total_rows, inserted, updated, unchanged, errors

### 5. 按身份证 upsert（幂等导入）
```python
existing = SELECT ... WHERE id_card=?
if existing is None: INSERT + change_log(action='import')
else: 逐字段比较 → 有变化才 UPDATE + 每字段一条 change_log；无变化计入 unchanged
```
同一文件重复执行必须得到 `新增0/更新0/无变化N` — 这是导入正确性的验收标准。

### 6. CLI 管理工具（argparse subparsers）
stats / list(过滤) / show(单人+变更历史) / update(--field --value, 写 change_log) / export(Excel, 中文表头按原列序) / log。字段名用英文 key + FIELD_CN 映射；是/否 ↔ 1/0 转换集中在两处（导入 yn()、导出 yn_out()）。

### 7. 验证清单
- [ ] 行数 = 源文件数据行数
- [ ] 核心字段逐条与源比对一致
- [ ] 重复导入 → unchanged=N, inserted=0
- [ ] update 往返测试（改→还原），log 有两条记录
- [ ] export 行列数正确

## Pitfalls
- **falsy 显示 bug**：`str(v or "")` 会把数值 0（如危险等级 0 级）渲染成空白。用 `"" if v is None else str(v)`；SQL 侧同理，`k or '(空)'` → `'(空)' if k is None else k`。
- **电话字段别过度清洗**：名册里常见座机前缀（0556-8798390）和空格分隔的多个号码（"132… 185…"），保留原文，校验只报告不修改。
- **PII 安全**：库含身份证/住址/电话，README 里明确提醒不要进公开仓库；change_log 是管理要求不是可选项。
- **先 dry-run 再写入**：导入脚本必须支持 --dry-run（只解析+校验+报告）。
- **update 命令的事务边界**：commit 前崩溃会回滚（好事），但函数里要用显式传入的 conn，别依赖 main() 的局部变量。

## 实例参考
- `references/smd-db-instance.md` — 金医生的重型精神障碍患者库（~/smd_db/）：路径、命令、schema、数据概况。收到新一期"在册基本信息"Excel 时直接按该文件更新。
