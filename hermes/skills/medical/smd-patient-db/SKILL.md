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
- 金医生口头报某人的用药情况/用药指导（如"X，用药：A药…每日…mg；指导：早/中/晚各多少"）→ 走「录入用药情况」节
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

## 录入用药情况（用户口头报"X，用药…；用药指导：早/中/晚各多少"）

1. **落库位置 = `report_cards.drug1-3`**（表3报告卡"目前用药情况"）。不要写进 follow_up_records——那是事件表，只记某次随访当时的用药。
2. 该人没有报告卡就 INSERT 一条只含 patient_id + drug 字段的记录；其余字段留空不臆造。
3. **格式约定**：剂量与指导合并为一个字符串 `药名片Xmg，每日Ymg（早A/中B/晚C）`，0mg 的时段可省略。多药依次填 drug1-3。
4. **药名按通用名规范化**（如"舒比利"→"舒必利"），回复时主动说明改了什么，让用户确认是否写错。
5. 每字段各写一条 change_log（action='add'/'update'）；脚本 write_file 到 /tmp 再执行，读回验证后报告。
6. 录完顺手 `python3 smd.py forms --name <姓名>`：若必填四表缺失，提醒金医生补（8月批量导入的人员普遍四表全空）。

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

- 备注列不主动填：金医生明确纠正过——除非他明确告知要写什么，否则备注/说明类栏目一律留空。其他有数据依据的字段正常填。
- 无数据的字段留空并提醒金医生补（如用药情况、监护情况），不要臆造。
- **部分 .xls 是加密工作簿**：xlrd/openpyxl 报 `Workbook is encrypted` 时，先问金医生要密码或换 xlsx 版本，不要反复试读。

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
- **表8多选字段带"其他"项时须补文字**：如目前症状选12(其他)且实际无症状 → 存 `12 无`；有具体表现则 `12 <描述>`。金医生确认的格式（编码+空格+文字）。
- **表8右上角编号**存 follow_up_records.record_no（非报告卡卡片编号，勿混入 report_cards.card_no）；schema 已含该列+幂等迁移。
- 表9/表14 是县级汇总，不挂患者，按 period/year 维度录入。

## 填写对外纸质表单（表8随访记录 docx）

模板：`~/下载/精神障碍管理/16、附件1-2严重精神障碍管理治疗工作用表.docx`（tables[6] 即表8，横向节）。输出到 `~/下载/精神障碍管理/YYYY.M/随访记录/随访服务记录表-<姓名>-YYYYMMDD.docx`。

**填写规则（金医生手填样表为准，2026-09 二次纠正后定稿）**：
1. **所有选中的数字必须写在方框内**——不是打勾，也不是把数字打在方框位置却让方框消失（金医生原话："选项填写不在方框内"）。实现：把该 run 改写成**全角数字** + **run 边框 `w:bdr`**（single / sz=4 / **space=0**）+ **字号 `w:sz`/`w:szCs`=12（6pt，脚本里 `FILL_SIZE`）**。三条都关键：
   - **全角**：半角数字渲染出来是窄长矩形，与原表格的 □ 不一致（金医生反馈："所有填写方框与原表格不一致"）。
   - **字号 6pt**：LibreOffice 里 run 边框高度≈字号×1.6（6pt→方框 24-28px，7pt→27-34px，9pt→27-38px，10.5pt→42px）；行高普遍 39-41px（单行）/73-81px（双行）。用 9pt 时 本次随访形式/本次随访对象 行（行高 284twips=0.5cm）的方框会胀到 38px **压住上下行线**（金医生反馈："填写的方框还是太大，突破上下间隔线"）；7pt 在随访形式行仍差 1px 压线；**6pt 全表零压线**，且方框与印刷 □（约 24px）等大。
   - **space=0**：边框内边距归零，方框不再额外变大。
   验收标准：200dpi 渲染后量每行方框竖边高度，必须 < 行高-2px。
   - **行距必须是 exact 而非 atLeast**：模板答案格用 `w:line="240" w:lineRule="atLeast"` 时，run 边框会被拉成整行高（40px）压线；改成 exact（保留原 line 值）后边框只包住字身。段落里除方框/斜线外无正文时直接设 `exact 200`；含正文的段落用 exact + 原 line 值（保住正文行高）。相邻带框 run 会粘连成一个框，需各自成框时在中间插**细空格 U+2009**（编号行用这招；零宽空格 U+200B 无效，仍会合并）。多位数（如目前症状选12）写在第一个框内，但**不能让它被 distribute 拉开**——见规则 10。
2. **单选题行的数字要落在表格最右侧的答案格**（金医生原话："填写位置不在表格右侧原位置"）。模板中部分行（随访形式/随访对象/若失访/住院/治疗效果/转诊）的方框是用"行内大量空格"排版的，需**把该单元格拆成 span7 + span1 答案格**：答案格 tcW=875、tcBorders 仅 left=nil + bottom=single、段落 jc=right、vAlign=center（照抄模板 r21 的 tc2），原宽格补 right=nil、gridSpan 改 7、tcW 改 6258。拆完后数字与相邻行的答案格左右对齐。
3. **本次随访对象**（3 框）：数字写在**对应选项序号的框**（选 2 → 中间框）。
4. **本次随访形式**（模板有 2 框，样表只有 1 框）：按样表只保留最右侧一个框，数字写在框内（去掉多余空框）。
5. **危险行为**（6 框）：选 "7 无" 时 7 写在**第一个**框内。
6. **目前症状**（12 框）：编号从第一个框起填（如 12）；选 12(其他) 还要在选项行"其他"后的**下划线填空**写实际描述（无症状写"无"）。
7. **康复措施**（5 框）：按左到右填（选 1、4 → 第 1、2 框）。
10. **同一行并排多个方框的行（目前症状 12 框、康复措施 5 框）要专门处理 `jc=distribute`**：
   - 这些行的方框串是 `jc=distribute`（原表靠它把方框均分铺满整行）。**多位数字必须先 `set_jc(p,'left')`**：distribute 按“每字一格”拉开，run 边框跟着被拉开，“12”就变成很宽的扁长框、两字间还有大空隙（金医生反馈：“目前症状的表格扁长，里面的数字是12,不是1 2”）。
   - 改 left 后整串方框比原表短约 33pt，要**从第 2 个 □ 起每个前面加一个半角空格**（10×3.15pt）把整串拉回原长（验收：框串右端落在表格右边框内）。
   - 这些行填写用 **半角数字**（`fullwidth=False`，脚本自动补一个半角空格）：方框 22-26px 高、约 8-11pt 宽，与印刷 □（10.5pt）及原框距对得上；用全角会把整串宽出 12pt（曾把康复措施 5 框串撑成 85pt，原表 73.5pt）。
   - **填多个框务必一次性取框**：先 `pairs = box_pairs(p)` 再 `fill_pair(pairs[i], val)`；循环里反复调 `fill_box_in()` 会因为已填的框不再是 □ 而整体错位（曾把“4”填进第 3 个框）——金医生反馈：“康复措施的方框也不符合表格原格式”。
   - **但并排多方框行（目前症状/康复措施）的 run 边框方案已废弃**，改用规则 11 的整组图片：run 边框内边距固定约 8.6pt（`w:space=0` 压不下去），带框数字最窄也有 33-38px，比印刷 □（23px）宽一大截，金医生两次反馈“方框不符合原表格格式”。
11. **并排多方框行（目前症状 12 框、康复措施 5 框）改用「整组方框图片」**（`scripts/postfix_t8_groupimg.py`，对生成好的 docx 跑一次即可）：
    - 用 PIL 画一张整组方框图（600dpi、白底），几何按原模板 200dpi 实测像素复刻：方框墨迹 8.3pt 见方（对应印刷 □ 的 23×23px）、框粗 0.48pt、框内数字 5.6pt、框间斜线（右端距下一框左端 5px@200、水平跨 9px、上下各超出 2px）。症状 12 框左端 `[15,118,159,200,240,281,321,362,402,443,484,524]`（第 1 框前留 15px 内部左边距）、宽 537px；康复 5 框 `[0,52,92,133,174]`、宽 202px。
    - 把该行所有方框/斜线 run（含旧的带框数字 run）删掉，换成一个 run 内嵌该图（`add_picture(width=Pt(...), height=Pt(...))`），段落设 **`jc=right` + `w:ind w:right="-200"`**（见下方“方框组贴表格右侧”条）：`jc=distribute` 会横向拉伸内嵌图片（曾拉成 2.4 倍），只用 `jc=left` 则图堆在左边。
    - 图高公式 = 斜线溢出(px@200 先换算) ×2 + 方框墨迹(pt)，**不要把 px@200 与 pt 直接相加**（曾算出 44px 画布，方框被裁得只剩顶边）。图高须小于该段落行高（症状行 `exact 240`=12pt，图 9.7pt 可容）。
    - 康复措施行用“5 其他”后的填空线定位方框组：填空 run 设为 **89 个带下划线的空格**（长度与模板相当），方框组即落到表格右侧、与模板位置一致。
- **“目前症状”/“康复措施”方框组须贴表格右侧**（金医生要求，2026-09-24 像素级验收通过）：模板这两行是 `jc=distribute`，方框串被拉开铺满整格、自然贴右。交付件换成整组图片后，段落须设 **`jc=right` + `w:ind w:right="-200"`（负右缩进把图继续往右推）**——只设 `jc=right` 仍离表格右竖线差约 20px（≈200 twips），必须补负右缩进。实测交付件与模板一致：症状 12 框组 x=666..1064、康复 5 框组右端 x=1064，距表格右竖线 x=1077 为 13px（模板症状行 x=665..1064）。
    - **“表格右边距过大、与下方文字不对齐”的真因＝页面边距取了别的节**（2026-09-24 定位并修复）：模板是多节文档，表8 所在节的边距由**表8 之后最近的那个 sectPr** 决定 —— `w:pgMar` **left=1797 right=1797 top=1361 bottom=1361**、pgSz **11906×16838**。生成交付件时若沿用 body 末尾 sectPr（1134/1418），表格右竖线会比下方注释文字窄 76px，就是金医生说的“右边距过大、与下边文字没对齐”。修法：把交付件唯一 sectPr 的 pgMar 直接写成 1797/1797/1361/1361。验收：150dpi 渲染后表格左/右竖线应在 **x=168 / x=1077**（模板渲染完全相同），且表格右竖线＝整页最右内容（下方文字右端 ≈1047、起点 ≈188）。
    - 症状行要去掉该段落首行缩进（`w:ind` 的 firstLine/firstLineChars/left），否则整张图右移约 13pt。
    - 验收：渲染后看两行方框是否完整正方形、数字在框内、斜线在框之间、无压线。
8. **表头右上角编号**（如 201－03456）要落在表头行的**右侧**（金医生反馈："编号的位置应该在表头的右侧"，样表也在右侧）。做法：给姓名/编号段落的 pPr 加**右对齐制表位** `<w:tabs><w:tab w:val="right" w:pos="7917"/></w:tabs>`（7917 twips 使编号右端落在表格右边框内约 11mm，与样表≈13mm 相当），并把原来的长空格 run 换成 `<w:tab/>`；编号后的 8 个数字各占一个全角带框 run（数字间细空格）。**不要用空格排版**：空格宽度随字号/字体变化，在 Word 里会偏到行中间。段落本体只保留 `adjustRightInd/snapToGrid`，无缩进；表格右边框在段落坐标 **8659 twips**（该值只与文本区左原点相关，不随左右页边距变化，故制表位 7917 在边距改成 1797 后仍适用）。
9. **用药情况行和用药指导行都要填药名**（金医生反馈："用药指导中的药物品名，没有填写"）：用药情况行 药物1 写"药名+规格"（如 舒必利片100mg）+ 每日(月)剂量数字；用药指导行 药物1 同样填药名，并把早/中/晚剂量写在 用法 的下划线空格 run 上。
9. 日期行（随访日期/下次随访日期）把数字写进下划线空格 run，保留"年/月/日"；用药情况/用药指导把药名追加到"药物1："后、剂量与用法写下划线空格 run。

**技术要点**：
- 表8是每次随访一张（非横向多列）。生成独立文档：打开模板 → body 只保留 111(表8标题段)/112(姓名编号段)/113(表8表格)/114(注释段) + 末尾 sectPr，其余元素全删 → 页面与表格几何与模板完全一致（9 列网格、tblW=8731、tblInd=-72）；**保留的 sectPr 必须把 pgMar 强制成 1797/1797/1361/1361**（模板中表8 所属节的边距；沿用 body 末尾 sectPr 的 1134/1418 会导致“表格右边距过大、与下方文字不对齐”），不要自己重建表格，否则空格排版会整体左移。
- 行索引（templates[6]，即新文档 tables[0]）：0随访日期 1随访形式 2对象 3若失访 4-5死亡 6危险性评估 7目前症状 8自知力 9睡眠 10饮食 11-15社会功能 16危险行为 17关锁 18住院 19实验室检查 20用药依从性 21药物不良反应 22治疗效果 23转诊 24-26用药情况 27-29用药指导 30康复措施 31本次随访分类 32下次随访日期。
- 注意：**11-15 社会功能行有 4 个 tc（答案格索引 3）**，其余单选行答案格索引 2（多选行 症状/危险行为/康复措施的框在同一个宽格内的独立 run）。
- 姓名行 runs=[姓名：, 空白 run, 长空格, 编号□□□－□□□□□]：只改第一个空白 run（防重名），编号 run 改成"编号"后逐个补带框数字。
- 参考实现：`scripts/fill_t8_follow_up.py`（本 skill 内，v6，只改 DATA 块即可复用；含全角+6pt 方框、编号右对齐制表位、拆答案格、exact 行距修正、两处药名填写）；**生成后再跑 `scripts/postfix_t8_groupimg.py <docx>`**（跑之前先 `cp <docx> <docx>.bak` 备份）把目前症状/康复措施的并排方框组换成整组图片（规则 11）。
- **写 docx 脚本的坑**：`qn` 必须 `from docx.oxml.ns import qn` 且传带前缀的 `'w:xxx'`——自己拼命名空间字符串会匹配不到任何元素（报“未找到段落”），传 `'p'`（无前缀）直接 ValueError。
- **验证**：`soffice --headless --convert-to pdf` + `pdftotext -layout` 逐行核对 → `pdftoppm -r 200 -png` 渲染后用 numpy 量行线 y 与方框竖边高度（10-70px 的竖向暗线段），逐行确认无越线；再用 vision_analyze 看图确认（deepseek 云端模型可靠；本地模型必超时）。
- **页面级布局问题（右边距过大、表格与下方文字不对齐等）先读 XML 再动刀**：对比模板与交付件的 `w:pgMar`（页边距）、`w:tblW`/`w:tblInd`（表格宽度/缩进），用像素测量定位差异，不要靠反复截图猜。
- vision_analyze 非要用本地模型时无解；图片大于 ~2000px 宽建议先裁剪到 <1500px 再分析。
- **vision_analyze 连续超时（≥3 次）立即停止重试**：不要靠反复缩小/重裁同一张图硬试——本会话曾因此空转上百轮。正确做法：改用 numpy 像素测量直接回答布局问题（表格左右竖线 x、行线 y、方框组右端位置），或读 docx XML（`w:pgMar` 页边距 / `w:tblW` 表格宽度）对比模板与交付件；视觉确认只在关键节点做一次，且优先用带参考线的对比图。
- **探测要有新目标：同一段检查脚本不要重跑**——参数和输入都没变的 probe（尤其一遍遍跑同一个 docx XML 检查）不会产生新信息，只会耗尽迭代预算并被中断（曾两次触发 “maximum number of tool-calling iterations”）。每轮要么换个探针（换对象／换量纲／换数据来源），要么直接收敛给结论。
- **版式验收（与模板逐像素对比）的完整方法见 `references/layout-verification.md`**：模板表8 页定位、双方 150dpi 渲染、numpy 量竖线／方框组、带参考线的对比图做法、以及“两文档分页不同时不能按 y 配对行”的坑。
- **交付件要压成单页**（金医生要求）：模板里表8 的注释段没任何行距设定（自然行高 31px），交付件表体整体落在第 1 页后，注释第 3 行会溢到第 2 页（只差 3px）。修法：给注释段（body 里最后一个 `w:p`）加 `w:spacing w:line="260" w:lineRule="exact"`（13pt）——三行即全部落到第 1 页且字迹不裁切。
  - **必须用 `exact`**：设 `line=240 lineRule=auto`（单倍）对这段**完全无效**（该段行高本来就不是段落级 spacing 决定的，渲染逐像素不变）；也不要靠改下页边距掩。
  - 验收：`pdfinfo` 页数=1；150dpi 下注释三行 y≈1529/1556/1583（行距 27px、字高 20px），末行底部 1602 < 可打印底 1612；表格左右竖线仍为 x=168/1077。

## 与月度工作量表的联动

公卫工作量统计表（见 skill: medical-guideline-kb 的 2c 节）"其他"栏的"新增N份"= 本月新增管理对象，用户随后会报明细，按本流程录入；录入人数应与工作量表累计新增份数对得上。

### 完善月度工作量统计表（金医生要求"根据这个月工作量完善统计表"时）

**权威文件 = `~/private_db/knowledge/medical/工作量统计/YYYY年M月公卫工作量统计表.xlsx`**（历次口头汇报的工作量都录在这里，含其他同事的条目）。改完后同步覆盖到当月目录 `~/下载/精神障碍管理/YYYY.M/` 同名文件。两份必须一致。

1. **数据源优先级**：① 权威文件里已有的行（金医生历次口头汇报录入的，最权威——如"9月22日董春霞档案录入28份"这类条目只存在于该文件）；② `smd.py log`（change_log 留痕）；③ 在册基本信息 xlsx 备注列（"YYYY-MM-DD 新增管理对象"）。**不要凭印象编日期、编数字，也不要覆盖已有行**。
2. **逐行核对**：每条工作写一行（序号/时间/姓名/档案录入/电话访视/上门访视/其他），按日期排序；"其他"栏沿用既有简记风格（如"新增N份"）；数字列只填有依据的，无则留空。
3. **日期格式**：B 列用 datetime + `number_format='m"月"d"日"'`（与模板一致），不要写字符串。
4. **改前先备份**：`cp <统计表> <统计表>.bak-YYYYMMDD`，openpyxl load→填→save，再读回验证全部行；最后把权威文件同步到当月目录。
5. 完成后向金医生报告合计（档案录入/电话访视/上门访视/新增份数），并主动指出存疑项请他确认。
