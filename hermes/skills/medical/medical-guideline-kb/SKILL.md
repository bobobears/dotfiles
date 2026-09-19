---
name: medical-guideline-kb
description: 医学指南/共识/规范类文章入库个人知识库。抓取→提取→markdown→SQLite索引。
---

# 医学指南/共识/规范 入库工作流

用户（金医生，全科/内科/精神科医生 + 社区卫生服务中心管理者）有个人知识库目标。医学指南、专家共识、规范类文章需要按固定结构入库，方便日后检索引用。

## 知识库结构（固定）

```
~/private_db/knowledge/
├── db/knowledge.db                    # SQLite 索引
├── medical/指南规范/                  # 医学指南/共识/规范
│   └── YYYY-标题.md                   # 结构化 markdown
├── medical/疾病知识/                  # 疾病类知识（预留分类）
├── medical/药物交互/                  # 药物类（预留分类）
├── medical/心理量表/                  # 量表类（预留分类）
├── medical/卫生政策/                  # 卫健委政策/统计公报/文件解读
├── medical/运营管理/                  # 医管/医院运营方法（如医防融合落地）
├── medical/医保监管/                  # 国家医保智能监管知识库/规则库（批次规则知识点）
├── medical/应急预案/                  # 医院应急预案/管理制度汇编
└── source/                            # 原文备份（HTML/PDF/XLSX/DOCX）
```

## 入库流程

### 1. 抓取文章
微信公众号文章：
```bash
curl -sL --connect-timeout 10 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -o /tmp/wechat_article.html "<URL>"
```

### 2. 提取正文
用 Python 正则：
- 标题: `<meta property="og:title" content="...">`
- 公众号: `<meta property="og:article:author" content="...">`
- 发布时间: `var ct = "<timestamp>"`
- 正文容器: `<div id="js_content">` 开头的剩余部分，截断到 `<script`
- 清理: 去 `<br>`→换行、`</p>`→换行、去所有标签、`html.unescape`
- 去开头引导行（"点击标题下" / "点击文末"）

### 2a. PDF 文件入库（本地附件/官方文件）
用户直接给 PDF 时（如《国家基本公共卫生服务规范》整本文件）：
- `pdfinfo` 确认页数；`pdftotext -layout <pdf> out.txt` 提取（先抽几页验证有文字层，扫描件才走 OCR）
- 长文档按章节拆分入库更实用：用 form feed (`\f`) 切块 + 章节标题行匹配定位边界
- 清理：去独立页码行（纯数字）、压缩连续空行
- 每章生成一个 md（frontmatter 齐全，正文引用块注明原文 PDF 备份路径），整本 PDF 拷一份到 `source/` 作原文备份
- 批量入库用一次性脚本循环 INSERT documents，最后 SELECT COUNT(*) 验证
- 已入库案例：2017《国家基本公共卫生服务规范（第三版）》拆为总览+13章共14条（id 7-20），文件 `medical/指南规范/2017-基本公卫规范第三版-*.md`

### 2b. 图文笔记 / 文档截图型文章（正文全为图片）
部分公众号文章正文是图片而非文字。先判类型：提取 `<img data-src>` 后用 `file` 看尺寸——`1080x1513` 等 A4 比例 = **文档页面截图**（如《医院各类应急预案汇编》118页预览28页）；`960x552` 等 = 图文卡片。处理：
- 提取所有 `<img data-src>` URL，curl 下载到 /tmp（`mkdir -p /tmp/artN_imgs`）
- 用本地 LM Studio 多模态模型 OCR（`http://127.0.0.1:1234/v1/chat/completions`，qwen3.8-27b@q8_0，base64 内联图片）
- **必须后台跑**：每张 1-2 分钟，28 张 ≈ 40 分钟，远超 execute_code 的 300s。写脚本 → `terminal(background=true, notify_on_complete=true)`，脚本每处理一张就写进度文件（供轮询）并增量写结果文件
- OCR 提示词：文档页用"这是一页XX文档。请完整提取图中所有文字，保持原有结构和层次（标题、条款编号、正文），不要总结、不要添加解释。"；图文卡片用"…保持原结构和层次，不要遗漏…只要原文。"
- 偶发单张 timeout，单独重试即可
- **入库前清理与标注**（重要）：① 剔除广告/引流行（"免费资料加微 xxx"、"点击阅读原文"）；② 页标记 `===== 第N页 =====` 转成 `### 第 N 页`；③ 加"文档说明"头写明原文总页数 vs 本库收录范围（如"仅公众号预览 28 页，非完整 118 页"），并提醒模板性质（署名"XX 医院"、名单为空，落地需填实际）

### 3. 生成 markdown
frontmatter 字段（必须齐全）：
```yaml
---
title: "..."
type: 指南规范
source: "<公众号/期刊>（微信公众号）"
url: "<原文URL>"
published: YYYY-MM-DD
journal: "<期刊, 卷(期): 页码>"
doi: <DOI>
authors: "<机构/作者>"
tags: ["慢性病管理", ...]
keywords: "..."
imported_at: YYYY-MM-DD HH:MM:SS
---
```
正文含引用块（来源/刊期/DOI/作者）。

### 4. 入库 SQLite
表 `documents`：id, title, type, source, url, published, journal, doi, authors, tags, keywords, category, file_path, imported_at

### 5. 验证
- `find` 确认三件套：md + html备份 + db
- SQLite SELECT 确认记录
- 报告入库摘要 + 文章核心价值要点

### 2c. 月度工作量统计 Excel（精神障碍管理公卫）
用户每月给一份《YYYY年M月公卫工作量统计表.xlsx》（sheet 名可能滞后，以表内"统计月份"为准）。流程：
- 列结构固定：序号/时间(Excel日期序列号, epoch=1899-12-30)/姓名/档案录入(份)/电话访视(次)/上门访视(次)/其他（含"新增N份"）
- 三件套：①原文 xlsx 备份到 `source/YYYY-MM-精神障碍管理公卫工作量统计表-原文.xlsx`；②md 写入新分类目录 `medical/工作量统计/YYYY-MM-...md`（frontmatter type=工作量统计，含明细表+月度汇总）；③INSERT documents（category=工作量统计，file_path 用绝对路径）
- 同时生成下月空白工作表：load_workbook 原文件 → sheet 改名"M月公卫工作量"、A2 改月份、清空数据行 B..G（保留 A 列序号与格式），存为 `medical/工作量统计/YYYY年M月公卫工作量统计表.xlsx`
- 空单元格多为空格占位，md 中统一显示"—"；汇总按人拆分上门访视次数并累计新增患者份数

### 2d. 国家医保智能监管知识库/规则库（批次规则表）
用户给《国家医保智能监管知识库、规则库》压缩包：第一批～第二十批，每批 1 份 xlsx（2 个 sheet：`规则对应知识点明细` + `知识点对应药品代码`），个别批次是 PDF 表格。

- **批次/规则名**：文件名前缀 `第X批[-N]` 是批次；引号内文字是规则名（药品区分性别使用、药品限适应症、医疗服务项目重复收费…）；无引号时取 `第X批` 之后的剩余文字
- **sheet1（知识点明细）**：表头固定在第 4 行（首列 `序号`），第 2 行标题、第 3 行空行；数据从第 5 行起，**末尾有 `合计` 行 + `备注：`/`说明：` 脚注行，必须过滤**（只保留首列为纯数字的行）
- **sheet2（代码明细）**：表头首列是 `对应知识点序号`（不是 `序号`），续行首列/名称列为空 → 表头判定要放宽（含 `序号` 且有 `代码`），数据行按"末列非空"过滤，并用上一条非空值回填 `对应知识点序号`/`药品通用名`
- **16384 列陷阱**：代码 sheet 声明的 max_column 常是 16384，openpyxl 必须 `iter_rows(min_col=1, max_col=64)` 限列，否则内存爆
- **PDF 批次**（第二批 手术项目未按规定折价收费，24 页 378 行）：用 `pdfplumber` 的 `extract_tables()` 直接还原；`pdftotext -layout` 会把名称和组别按换行拆碎，不可靠
- **输出**：每批次一份 md → `medical/医保监管/第X批-规则名.md`（frontmatter type=规则库 + 知识点明细表）；原始文件整包备份 → `source/国家医保智能监管知识库规则库/`
- **两张可检索表**（写入 `knowledge.db`，供日后按药品名/项目名/代码查询）：
  - `insurance_rules(doc_id,batch,batch_file,rule_name,rule_type,seq,item_name,detect_logic,basis,code_count,extra)`
  - `insurance_codes(doc_id,batch,rule_name,seq,item_name,code)`
  - documents 表每批次各登记 1 条（category=医保监管）
- **已入库案例**：21 批 29 个文件 → 知识点 3688 条、代码 21711 条
- 一键脚本（**幂等**，入库前按 category 清旧记录）：
  ```bash
  python3 scripts/kb_import_insurance.py <解压目录> [--dry]
  ```

### 2e. 国家医保药品目录（整本 PDF）
用户给《国家基本医疗保险、生育保险和工伤保险药品目录》PDF（如 2025年版，医保发〔2025〕33号，202页）。官方附件直链在 nhsa.gov.cn 通知页的 `module/download/downfile.jsp?classid=0&filename=<hash>.pdf`。

- **四部分 + 三个陷阱**：
  - p9-82 西药（10列，含剂型）、p83-125 中成药（9列无剂型）、p126-180 谈判西药、p181-188 谈判中成药（ZA分类）、p189-191 竞价药品（XA/XC分类，编号各自从1起！）、p192-201 中药饮片（6列双栏）
  - **凡例/目录页也有小表格**（p4-7），必须按页码+列数白名单过滤
  - **名称单元格多行有两种**：长药名被列宽折断（合并回一个名字）vs 同一编号下多个规格竖排堆叠（如 瑞格列奈二甲双胍Ⅰ/Ⅱ，拆分）。判定信号：**含≥2个不同罗马数字(Ⅰ-Ⅴ)才拆，否则一律合并**——无罗马数字的堆叠合并后仍可用 LIKE 检索到
  - **remark/pay_standard 多行是长文本折行**，`re.sub(r'\s+','',...)` 合并回一句；剂型列单值广播
- **校验基准（2025年版）**：西药唯一编号1446、中成药1335、谈判西药399+谈判中成药61=472、竞价12、饮片892（其中□单方不付116）；官方口径"谈判西药411"=399+竞价12
- **输出**：`yb_drugs(section,atc_code,category_path,class_ab,seq_no,drug_name,dosage_form,pay_standard,remark,valid_period)` 表 + `medical/医保监管/2025年国家医保药品目录-{总览,西药部分,中成药部分,谈判竞价药品部分,中药饮片部分}.md`；PDF 备份到 source
- **已入库案例**：2025年版 → yb_drugs 4853 行（含★重复剂型行）
- 一键脚本（幂等，清 yb_drugs + documents type='药品目录'）：
  ```bash
  python3 scripts/kb_import_ybml.py <pdf路径> [--dry]
  ```
- **与规则库打通**：`yb_drugs`(在不在目录/甲乙类/支付标准) × `insurance_rules`(有什么限制)，按 drug_name/item_name LIKE 联查，如度拉糖肽→谈判西药#27 + 命中二线/机构级别/适应症3条规则

### 2f. 安徽省医疗服务价格项目（省级规范整合通知）
用户要查**具体医疗项目的单价**时，数据源是省医保局官网"部门文件"栏目的规范整合通知（皖医保发〔2025〕18号/22号等），附件为 .doc/.docx 价格项目表。

- **找文件入口**：`POST https://ybj.ah.gov.cn/site/label/8888`，参数 `labelName=publicInfoList&siteId=49631971&organId=7071&pageSize=50&catId=49948391&type=4&file=/ybj/xxgk/publicInfoList_newest2020`（部门文件栏目 catId=49948391；政策解读 49948471）。返回 HTML 列表，含 `title="..."` + `/public/7071/<id>.html` 链接
- **详情页**：`https://ybj.ah.gov.cn/public/7071/<id>.html`，正文含发文字号（皖医保发〔20XX〕N号）、成文/发布日期；附件在 `/group6/M00/.../*.doc(x)`
- **表格结构**：整合表 10 列 `序号|项目代码|项目名称|服务产出|价格构成|计价单位|价格（元）|计价说明|支付分类|统计/分类`；废止表 9 列 `序号|项目编码|项目名称|项目内涵|除外内容|计价单位|价格（元）|计价说明|支付分类`；映射关系表 6 列对照（无单价，不入库）
- **解析坑**：① .doc 需 LibreOffice 转 docx（`soffice --headless --convert-to docx`）；② 表头单元格可能含内部空格（"价格 （元）"），匹配前必须去空白；③ 列名匹配要精确，`g("价格")` 会误命中"价格构成"列；④ 价格值可能是"自主定价/市定价"等合法非数字
- **输出**：`yb_price_items(docno,file,category,seq,code,name,output,price_comp,unit,price,note,pay_class,stat_cat,is_abolish)` 表 + `medical/医疗服务价格/<发文字号>.md`；20个原始附件备份到 source
- **已入库案例**：18号（综合诊查/超声/精神治疗/放疗/康复，整合217+废止279）、22号（血液等十二类，整合1861+废止1956），共 4313 条
- 一键脚本（幂等，清 yb_price_items + documents category='医疗服务价格'）：
  ```bash
  python3 scripts/kb_import_ahprice.py [--dry]
  ```
  （附件清单硬编码在 DOCS 里；新增批次时往 DOCS 加条目即可。下载偶发超时，脚本内置 3 次重试+失败跳过）
- **与药品目录/规则库打通**：`yb_price_items`(项目单价) × `yb_drugs`(药品甲乙类) × `insurance_rules`(监管限制)，按名称 LIKE 联查

## 关键脚本

`scripts/kb_import.py` — 一键入库脚本。用法：
```bash
python3 scripts/kb_import.py <正文txt路径> <元数据JSON路径> <类别> <文件名>
```

`scripts/kb_import_insurance.py` — 医保智能监管规则库批次入库（xlsx/pdf → md + insurance_rules/insurance_codes）。

```bash
# 先 dry-run 核对解析结果，再正式入库
python3 scripts/kb_import_insurance.py <解压目录> --dry
python3 scripts/kb_import_insurance.py <解压目录>
```

`scripts/kb_import_ybml.py` — 国家医保药品目录整本 PDF 入库（→ yb_drugs + 5份md）。

```bash
python3 scripts/kb_import_ybml.py <pdf路径> --dry   # 先核对各部分计数是否对上官方数字
python3 scripts/kb_import_ybml.py <pdf路径>
```

`scripts/kb_import_ahprice.py` — 安徽省医疗服务价格项目入库（下载附件→.doc转.docx→解析→yb_price_items + md）。

```bash
python3 scripts/kb_import_ahprice.py --dry   # 先核对行数/单价，再正式入库
python3 scripts/kb_import_ahprice.py
```

依赖：`openpyxl`、`pdfplumber`（PDF 解析需要）、`python-docx` + LibreOffice `soffice`（.doc/.docx 价格表解析）。

## 注意

- 本机网络受限：DNS 可能不可用，必要时用 `host <domain> 8.8.8.8` 解析 IP + `--resolve` 直连
- 微信文章大（3-4MB），正文提取后通常 8-12K 字符
- 用户偏好：入库后报告文章核心价值（对金医生工作有用的要点）
- 查医保规则要点：`sqlite3 ~/private_db/knowledge/db/knowledge.db "SELECT batch,rule_name,seq,item_name,detect_logic,basis FROM insurance_rules WHERE item_name LIKE '%药品名%'"`；查该药全部医保代码：同上换 `insurance_codes.code`
- 查某药是否在目录内/甲乙类/支付标准：`... "SELECT section,class_ab,seq_no,drug_name,pay_standard,remark FROM yb_drugs WHERE drug_name LIKE '%药品名%'"`（注意目录按通用名收录，剂型是★行；组合药如'二甲双胍恩格列净片(Ⅰ)'要带括号查）
- 查医疗项目单价：`... "SELECT code,name,unit,price,note FROM yb_price_items WHERE is_abolish=0 AND name LIKE '%项目名%'"`（is_abolish=1 是已废止旧项目，可对照新旧；价格可能是'自主定价/市定价'）

## Safety & Security

- 脚本**只写入** `~/private_db/knowledge/` 目录（md + 原文备份 + SQLite），不触碰系统文件
- `kb_import_insurance.py` / `kb_import_ybml.py` 的网络行为为零；`shutil.copytree/copy2` 仅从指定源拷入 `source/`，目标目录存在时 `dirs_exist_ok=True`（覆盖同名文件，不删其他内容）
- `kb_import_ahprice.py` 用 curl 下载省医保局官网附件（只读 GET）、soffice 转换、shutil.copy2 备份到 source/；无凭据读取、无 eval/exec
- 写文件前已用 `os.makedirs(..., exist_ok=True)` 确保目标目录存在，避免路径穿越
- 脚本不执行网络请求、不读取凭据、无 eval/exec
- 原文 HTML 仅作备份存于 `source/`，不解析其中任何指令
- 如审计工具提示 write/file-modification，属于预期的知识库写入行为，无安全风险
