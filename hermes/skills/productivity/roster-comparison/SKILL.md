---
name: roster-comparison
description: 对比两份名册/名单表格，按身份证号找出新增和减少的人员。
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [roster, comparison, excel, xls, xlsx, 名册对比, 在册人员, 花名册]
    category: productivity
    related_skills: [xlsx, hybrid-office]
---

# 名册/名单对比（Roster Comparison）

对比两个时期的名册表格（如社区卫生服务中心"在册基本信息"5月 vs 8月），
按**身份证号**找出新增和减少的人员，并标记疑似录入笔误。

## When to Use

- 用户给两份 Excel 名册/花名册/在册名单，问"增加了谁、减少了谁"
- 周期性在册人员核对（精神卫生在册管理、员工花名册等）
- 任何"两表按主键 diff"的表格对比任务

## Quick Start

```bash
pip install openpyxl xlrd msoffcrypto-tool olefile   # 一次性依赖
python scripts/roster_diff.py OLD NEW [--password PW]
```

脚本自动探测格式（zip→xlsx / OLE2加密→解密后读 / OLE2→xls）、
自动定位表头行（含"姓名"+"身份证/证件号"的行），按身份证号 diff，
输出中文摘要 + JSON。桌面端上传的附件在 `~/.hermes/attachments/`。
密码只问用户要，绝不猜测。

## Procedure（脚本不适用时的手工步骤）

1. **先 `file` 探测真实格式**——扩展名不可信：
   - zip / `Microsoft Excel 2007+` → openpyxl
   - `CDFV2 Encrypted` → 加密文件！openpyxl 报 BadZipFile、xlrd 报
     "Can't find workbook in OLE2"，**这不是损坏**。用 msoffcrypto-tool：
     ```python
     import msoffcrypto, io
     with open(path,'rb') as f:
         of = msoffcrypto.OfficeFile(f)
         of.load_key(password='用户给的密码')   # 必须问用户，绝不猜
         out = io.BytesIO(); of.decrypt(out)
     open('/tmp/decrypted.xlsx','wb').write(out.getvalue())
     ```
   - `Composite Document File V2`（无加密流）→ 旧版 .xls → xlrd
     （xlrd 2.x 只支持 .xls，不支持 xlsx——正好互补）
2. **读表**：标题行+表头行常占前 1-3 行；数据从表头下一行开始，
   跳过空姓名行（有些表在表头下还有一行"选择：…"提示行）。
3. **质量检查**：重复身份证、空身份证、重名。
4. **以身份证号为主键 diff**（不是姓名！）→ added / removed。
5. **交叉验证**：同姓名不同证号 → 疑似录入笔误，单独列出请用户确认，
   不要擅自归并；再按姓名算一遍差异做 sanity check。
6. **输出中文表格**：新增 N 人 / 减少 M 人 + 疑点清单（含身份证号）。

## Pitfalls

- **扩展名 ≠ 格式**。WPS/Excel 密码保护的 xlsx 实际是 OLE2 加密容器；
  openpyxl `BadZipFile`、xlrd "Can't find workbook in OLE2 compound
  document" 都是加密信号，不是文件损坏。
- **密码必须问用户**（可与其他确认合并为一次），绝不尝试猜测或爆破。
- **姓名匹配会漏**（改名/错字），**身份证匹配会误判**（录入笔误）——
  两者都要做并报告差异。真实案例：同一人"张鸣"两表证号前两位不同
  （3401 vs 3101，出生日期相同），是笔误还是两人必须让用户定夺。
- **身份证列若被存成数值**，float 精度会丢末位（18 位 > float53）；
  读到科学计数法立即标记 ⚠ 请用户核对原件，不要用该值下结论。
- **序号列常是 float**（"1.0"），忽略它，只用姓名+证件号。
- xlrd 2.x 只读 .xls；openpyxl 不读加密文件也不读 .xls——分工明确。

## Verification

- 数量恒等式：`旧表人数 - 减少 + 新增 == 新表人数`（有重复证号时除外，需说明）。
- 每个 added/removed 人员都带身份证号输出，方便用户逐条核对。
- 同姓名不同证号的疑点必须显式呈现，不能静默归并或丢弃。
