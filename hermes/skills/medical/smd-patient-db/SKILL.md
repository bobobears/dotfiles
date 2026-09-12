---
name: smd-patient-db
description: 严重精神障碍患者库(~/smd_db)：新增在册、改信息、导花名册、序号规则。
version: 1.0.0
author: hermes (for BoboBears)
license: private
metadata:
  hermes:
    tags: [精神障碍, 公卫管理, sqlite, 患者数据库]
    related_skills: [medical-guideline-kb]
---

# 重型精神障碍患者库（华中）管理

## When to Use

- 金医生口头报"新增管理对象/新增N份"并给出姓名、身份证、监护人、电话、地址、诊断 → 走「新增患者流程」
- 要修改在册人员信息、查单人详情、看变更日志 → 「日常命令」表
- 要导出花名册 Excel（参照 .bak 样式）→ `python3 smd.py export`，注意「两套序号」规则
- 涉及 ~/smd_db/ 的任何操作前先读本 skill 的安全红线

用户是社区卫生服务中心管理者，维护严重精神障碍在册患者数据库 `~/smd_db/`：
`smd.db`（SQLite 核心数据）、`smd.py`（日常管理 CLI）、`make_table.py`（花名册导出）、`import_excel.py`（Excel upsert）。

## ⚠️ 安全红线（最高优先级）

- **本库一切管理活动只能调用本地模型（LM Studio @ 127.0.0.1:1234），严禁云上模型**——数据含身份证号、住址、电话等敏感个人信息。
- `smd.db` 不得上传任何公开仓库/云端。
- 每次修改必须写 `change_log` 留痕（谁改了什么字段，原值→新值）。

## ⚠️ 两套序号，严禁混淆（金医生明确纠正过）

| | 管理序号（库内 seq_no） | 花名册呈现序号 |
|---|---|---|
| 含义 | 数据库内部编号，只增不减，已转出不回收 | `make_table.py` 导出时按在册顺序从 1 重新编起 |
| 用途 | change_log 追溯、库内查询 | 对外花名册展示 |

- 新增患者：`seq_no = MAX(seq_no)+1`（含已转出占号）。
- **向金医生报告新患者的"序号"时，用呈现序号**（= 在册列表中的位置），或两个都报并标明。曾把管理序号当花名册序号汇报被纠正过。

## 新增患者流程（用户口头报信息）

用户通常一次报：姓名、身份证、监护人+电话、户籍/常住地址、诊断。步骤：
1. 校验身份证：18位 + 校验位（权重 [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]，模11查 "10X98765432"）；性别=第17位奇男偶女，出生日期=7-14位。
2. 查重：`SELECT id FROM patients WHERE name=? OR id_card=?`。
3. INSERT patients：`seq_no=max+1, town='华中', institution='华中中心', status='在册'`（户籍地=现住址时两字段同值），remark 记"YYYY-MM-DD 新增管理对象"。
4. INSERT change_log（action='add'，new_value 摘要关键信息）。
5. 验证：`python3 smd.py show <姓名>` + `sqlite3 smd.db "SELECT status, COUNT(*) FROM patients GROUP BY status;"`，报告在册总数变化。
6. **必填四表**（金医生规定）：每个新增管理对象必须补齐 表5知情同意(documents) / 表6基本信息(personal_info) / 表7补充表(info_supplement) / 表8随访记录(follow_up_records)。用户报信息时若含这些表的字段就一并录入；缺的提醒金医生补。用 `python3 smd.py forms --name <姓名>` 核查该人四表是否齐全。

注意：execute_code 里嵌 heredoc Python 易出引号/转义问题（`\d` 被吞），**把脚本 write_file 到 /tmp 再 terminal 执行更稳**。

## 指定管理序号新增（插入+顺延）

用户明确要求"将 X 的管理序号定位为 N"且 N 已被占用时：
1. 先备份 `cp smd.db smd.db.bak-<ts>-before-shift`。
2. `UPDATE patients SET seq_no=seq_no+1 WHERE seq_no>=N`，**每个受影响人员各写一条 change_log**（action='update', field='seq_no'）。
3. INSERT 新患者 seq_no=N；验证后报告顺延范围（首尾两人旧号→新号）和在册总数变化。

## 解除管理/转出流程（用户报"X 解除管理，档案转给 Y"）

沿用库内既有转出惯例（先 `SELECT name,institution,remark FROM patients WHERE status='已转出'` 看先例），三字段 + change_log：
1. 备份 smd.db。
2. UPDATE patients：`status='已转出'`、`institution=<接收机构>`、`remark='<YYYY-MM-DD 解除管理，档案移交<接收机构>>'`（原 remark 有内容则追加）。每字段各写一条 change_log（action='update'，旧值→新值）。
3. **seq_no 保留占号不回收**——已转出人员继续占号，新增仍取 max+1；花名册导出自动排除、不占呈现序号。
4. 验证：`smd.py show <姓名>` + `smd.py stats`（在册 -1、已转出 +1）。

## 日常命令（在 ~/smd_db/ 下）

| 操作 | 命令 |
|------|------|
| 总体统计 | `python3 smd.py stats` |
| 列表查询 | `python3 smd.py list --color 红色 / --risk 1 / --diag 精神分裂症 / --name 张`（--all 含已转出） |
| 单人详情+变更历史 | `python3 smd.py show <姓名或身份证>` |
| 改字段 | `python3 smd.py update <key> --field phone --value ...`（可改字段见 smd.py FIELD_CN：seq_no/name/id_card/guardian_name/phone/hukou_addr/cur_addr/diagnosis/risk_level/color_status/guardianship/color_type/dual_supervision/four_party/town/institution/out_area_addr/platform_transfer/has_cert/status/remark） |
| 导出花名册 | `python3 smd.py export [输出.xlsx]`（默认 ~/下载/精神障碍管理/在册基本信息（华中）-美化版_YYYYMMDD.xlsx） |
| 变更日志 | `python3 smd.py log [--patient 姓名]` |
| 必填四表检查 | `python3 smd.py forms [--name 张]`（核查表5知情同意/表6基本信息/表7补充表/表8随访记录是否齐全） |

## 填写对外表格（警情处置表等）

- **备注列不主动填**：金医生明确纠正过——除非他明确告知要写什么，否则备注/说明类栏目一律留空。其他有数据依据的字段正常填。
- 无数据的字段留空并提醒金医生补（如用药情况、监护情况），不要臆造。

## 导出注意事项

- 样式模板 `.bak`：`~/下载/精神障碍管理/在册基本信息（华中）8.20.xls.bak`（make_table.py 的 BAK/OUT_DEFAULT 已指向此路径；若再报 FileNotFoundError，先 find 定位 .bak 实际位置）。
- 导出时 DB 行数 > .bak 数据区行数会打印提示——正常现象（新增人员超出模板行数），非错误。
- **新增行必须格式统一、纳入表格外边框**（金医生明确要求）：.bak 尾部存在"有名有框"之后的无边框空行，DB 新人员落到这些位置时不能取模板原样式。make_table.py 已实现回退逻辑：`_has_border()` 判定该位置在模板里有无边框 → 无则整行逐列沿用 `base_row`（最后一个有边框且有姓名的数据行）的字体/填充/边框/对齐，且 `n_out_rows = max(sh.nrows, 3+len(db_rows))` 防止静默丢行。若再出现新增行无框或样式不一致，先查这段逻辑是否被改动；验证方法：openpyxl 读导出文件，逐行检查 20 列四边 border.style 非空。
- 身份证/电话强制文本格式；已转出人员不出现在花名册、不占呈现序号。

## 国标工作用表（附件1 表1-14）已纳入库

《严重精神障碍管理治疗工作用表》全部 14 张表已建成 13 个库表（schema：`~/smd_db/forms_schema.py`，幂等可重跑；字段详解另见知识库 `medical/指南规范/严重精神障碍管理治疗工作用表（附件1-2）.md`）。`patients` 保持核心不变，其余用 `patient_id` 关联。

| 国标表 | 库表(字段数) | 性质 |
|---|---|---|
| 表3 报告卡 | `report_cards`(38) | 主档/每人一份：card_no, source, family_history, first_onset_date, past_lockup, past_dangerous_behavior, confirmed_hospital/date, icd10_code, drug1-3, informed_consent |
| 表6 个人基本信息 | `personal_info`(33) | 主档/每人一份：blood_type, occupation, medical_payment, drug_allergy, family_history_*, disability, 生活环境(kitchen/fuel/water/toilet/livestock) |
| 表7 信息补充表 | `info_supplement`(34) | 主档/每人一份：past_main_symptoms, last_treatment_effect, dangerous_behavior(次数), economic_status, precise_poverty, guardianship_subsidy, disability_cert, community_rehab |
| **表8 随访记录** | `follow_up_records`(38) | **事件/每人多次（核心）**：follow_up_date, form_type, risk_level, current_symptoms, insight, social_*(5项), medication_adherence, treatment_effect, follow_up_category(1不稳定2基本稳定3稳定), next_follow_up_date |
| 表4 出院信息单 | `discharge_records`(25) | 事件/每次住院：admission/discharge_date, discharge_diagnosis, inpatient_drug1-3, treatment_effect, rehab_measures |
| 表12 应急处置记录 | `emergency_records`(22) | 事件/每次应急：start/end_time, scene_description, disposal_reason, main_measures, effect, target_category |
| 表13 肇事肇祸调查 | `offense_records`(43) | 事件/每次案(事)件：incident_trigger, current_status, managed/manage_date, reimbursement_ratio, guardian_fulfillment |
| 表2 线索复核登记 | `clue_records`(16) | 发现工作/可未建档：matched_item, diagnosis(或"待核查"), re_diagnosis；确诊后回填 patient_id |
| 表5/10/11 文书 | `documents`(8) | 协议/转诊单：doc_type(社区管理知情同意/双向转诊单/应急处置知情同意), content_text, attachment_path |
| 表9 信息交换表 | `info_exchange_reports`(26) | 汇总/按周期不挂患者：period, institution_type(乡镇卫生院/派出所/民政办/残联办/综治中心), registered_total, managed_count, lost_followup... |
| 表14 年度统计报表 | `annual_statistics`(27) | 汇总/按年不挂患者：year, county_name, 各类机构人员数, screening/confirmed_count, central/local_funding, subsidy_amount |

**录入约定**：
- 单选字段存整数编码（risk_level=0~5、form_type=1门诊2家访3电话），多选字段存 TEXT（编码或文字，逗号分隔）。
- 事件表 patient_id 必填；clue_records/documents 的 patient_id 可空（未建档/线索阶段）。
- 随访分类 follow_up_category：1不稳定 / 2基本稳定 / 3稳定——公卫考核核心指标。
- 新增表单数据同样要写 change_log 留痕（action='add'，patient_id 关联）。
- 表9/表14 是县级汇总，不挂患者，按 period/year 维度录入。

## 与月度工作量表的联动

公卫工作量统计表（见 skill: medical-guideline-kb 的 2c 节）"其他"栏的"新增N份"= 本月新增管理对象，用户随后会报明细，按本流程录入；录入人数应与工作量表累计新增份数对得上。
