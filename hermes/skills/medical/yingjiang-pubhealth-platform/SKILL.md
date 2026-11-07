---
name: yingjiang-pubhealth-platform
description: 迎江区公卫平台数据提取——页面入口、筛选控件、导出流程。
---

# 迎江区基本公共卫生服务管理平台（基恩）

- **地址**：`http://39.145.39.228:9098/pages/defaultMain.aspx`
- **登录态位置**：用户本机 Firefox（xrdp DISPLAY :10，profile `kzyn6wqk.default-release`），会话仅存内存不落盘——**绝不可关闭该浏览器窗口**。登录需人工验证码。
- **操作方式**：按 `web-session-extraction` 技能走 X11 + Web Console JS 通道（browser_exec/CDP 无法附加）。全程控制请求量，不惊动对方防火墙。

## 关键页面入口（内部标签系统）

主框架是 frame portal，子页面必须用站点自己的 `addTab(Pages, '标题', '/pages/...aspx','')` 打开（在顶层或任一 frame 的 window 上找 `addTab` + `Pages`）。直接导航 URL 会被弹回主框架。

| 模块 | URL |
|------|-----|
| 居民死亡管理 | `/pages/PersonInfoManagement/DeathManagement/DeathManagementList.aspx` |
| 档案终止、移交、封存管理 | `/pages/PersonInfoManagement/FilesTransferring/FilesTransferringList.aspx` |

菜单结构可从缓存的 `defaultMain.html` 里 grep `addTab(Pages,` 拿到全部模块 URL。

## FilesTransferringList（档案终止/移交/封存）筛选控件

| 控件 | id | 取值 |
|------|----|------|
| 档案状态 | `ctl00_ContentPlaceHtml_ddlState` | 正常=1, 移交=2, **终止=3**, 封档=4, 失访=5 |
| 是否死亡 | `ctl00_ContentPlaceHtml_ddlsDeath` | ⚠️ **否=1, 是=0**（值与直觉相反） |
| 查询按钮 | `lbtnSearch` | `<a>`，`.click()` 触发 postback |
| 导出Excel | `ctl00_ContentPlaceHtml_lbtnExport` | 先 stub `confirm/alert` 再 click |

- 结果总数在页面文本：`显示N条记录 当前页X/Y 次`
- 数据行是 Repeater（`RepeaterData_ctlNN_`），非 ExtJS grid；表头列：档案编号/姓名/性别/年龄/证件号码/联系电话/家庭地址/是否死亡/档案状态/建档日期/录入单位
- **导出Excel** → `~/下载/档案终止、移交、封存管理表<时间戳>.xls`，真 OLE2 格式，xlrd 读，**header=2**（前两行是标题和查询地区，表头在 row index 2）
- **query_and_export.js 完整流程**（自包含：addTab 打开列表页→等8s加载→设筛选→查询→等8s postback→点导出→等15s下载）：
  ```
  fetch('http://127.0.0.1:8899/query_and_export.js').then(r=>r.text()).then(eval)
  ```
  relay.log 输出序列：TAB_OPENED → TAB_READY → LIST_FOUND → FILTERS_SET → QUERY_CLICKED → QUERY_DONE total=N → EXPORT_CLICKED → EXPORT_WAIT_DONE
  ⚠️ 会话过期时 TAB_ERR（addTab/Pages 不存在），此时需用户重新登录。relay.py 8899 端口自带 CORS 头，直接 serve scripts/ 目录下的 JS 文件。
- **周对比方法**：用档案编号做主键，新导出 vs 基线 CSV 做集合差，得到新增人员。xlrd 解析时跳过前 2 行（标题+地区），第 3 行是表头，第 4 行起是数据。
- 死亡人员花名册 = 档案状态选终止 + 是否死亡选是 → 查询 → 导出Excel（金医生确认的正确口径，比"居民死亡管理"模块更全：2194 vs 1191 条，后者基本是前者的子集）

## DeathManagementList（居民死亡管理）

- 查询按钮：value 含"查询"的 input/button（排除"读卡"）；导出按钮 id `ctl00_ContentPlaceHtml_lbtnExport`
- 导出文件 `~/下载/居民死亡管理<日期>.xls`，header=3（首行标题、次行地区说明）

## 死亡日期的获取（导出表没有此列！）

导出的 Excel/CSV **不含死亡日期**，只有建档日期。要拿死亡日期须走详情页：

1. 列表页勾选目标行复选框 `input[id*='chkKey']`（带 `sno`=档案编号、`value`=gKey 属性），先取消其他已勾选项；可再调 `RepeaterCheckedOne(checkbox)`。
2. 点工具栏「查看终止、移交、封存详细信息」按钮 id=`ctl00_ContentPlaceHtml_lbtnViewInfo` → 新标签打开 `/pages/PersonInfoManagement/FilesTransferring/FilesEndingReason.aspx?gKey=...`
3. 详情页字段：`ctl00_ContentPlaceHtml_sEndingReason`=终止原因（死亡/去世）、`ctl00_ContentPlaceHtml_dEndingDate`=**日期即死亡日期**（yyyy-MM-dd）。
4. **目标不在第一页时**：用姓名查询框 `ctl00_ContentPlaceHtml_txtPersonName` 填精确姓名 + 保持 ddlState=3/ddlsDeath=0，点 `lbtnSearch` 重新查询后再按 sno 找行。每页15条共147页，别翻页。
5. 参考脚本：`scripts/get_death_date.js`（逐个姓名查询→勾选→读详情页，relay 回传 reason/date）。

**金医生偏好**：查询成功后优先导出 Excel 解析，比逐条查详情页快得多。标准流程：筛选→查询→导出→pandas 解析→对比基线→生成花名册。死亡日期如需补充再走详情页。`scripts/query_and_export.js` 是自包含脚本（addTab 开列表页→设筛选→查询→导出），一次注入跑完。周对比时建议对新增人员补查死亡日期后写入明细 CSV 的「终止原因/死亡日期」两列。

## 死亡后服务记录核查（健康档案浏览器）

查某人「死亡后是否还有服务记录」：列表页按姓名定位行 → **读该行档案号链接 onclick 里的真实 personid** → `Visiting(personid, name)` 打开健康档案浏览器（ShortcutsList.aspx）→ 遍历子标签提取含日期的数据行。

- ⚠️ **personid 坑**：`Visiting()` 第一参数是行内 `<a onclick="Visiting('...','姓名')">` 里的值，**可能是 GUID**（如操乐成 `8113432c-...`），不一定是档案编号。传错会打开空白页（基本信息全空、导航菜单不渲染）——这是参数错的信号，不是数据缺失。
- 健康档案浏览器结构：顶层 `.headerMenu li`（居民健康档案/慢性病管理…）→ 子标签 `.headersubMenu li`（个人档案/健康体检/接诊记录/高血压确诊·随访管理/糖尿病确诊·随访管理/慢阻肺确诊管理…，按该人慢病动态增减）→ 内容在 `id=子标签名+'_IFrame'` 的 iframe 里。
- 服务记录 = 各子标签表格中含 `yyyy-MM-dd` 的行（体检日期、随访日期等）。个人档案页底部还有「卫生健康服务活动记录」表。基本信息区含**终止日期**（可交叉验证死亡日期）。
- 参考脚本：`scripts/check_services.js`（自动读行链接 personid → Visiting → 遍历全部子标签回传数据行，relay 输出 `SUB[模块/子标签] ROWS(n): [...]`）。每人跑一次约 1.5 分钟。
- ⚠️ **check_services.js 假设列表页标签已打开**：`findListDoc()` 只遍历已加载的 frame，找不到 FilesTransferringList 就返回 `NOLIST`——这是页面状态问题，不是执行失败。若不确定列表页是否打开，用 `scripts/open_and_check.js`（自包含：先 addTab 打开列表页→等 8s 加载→设筛选→查询→Visiting→遍历子标签，一次跑完约 2 分钟）。

## 周对比基准文件

- 位置 `~/下载/档案终止管理/`，命名 `迎江区死亡人员花名册_档案终止且死亡_<N>条[_<日期>].csv`；最新一份（2026-11-06：2224条）即下次对比的基准。新增人员花名册命名 `新增死亡人员花名册_<N>人_<日期>.xlsx`。每次跑完周对比用新导出重建该 CSV 并更新技能里的数字。
- **导出文件落点不固定**：有时在 `~/下载/` 根目录，有时在 `~/下载/档案终止管理/`——按 mtime 找最新 .xls 即可，别写死路径。
- **上次查询时间**：用 `session_search` 全文检索（关键词如「死亡花名册」「档案终止 死亡」），不要翻 `sessions.json` 元数据——会话标题是通用的，只有消息内容被索引。命中后用 `around_message_id` + `window` 取上下文，提取精确时间戳、记录数、新增人员。

## 历史基准（死亡人员花名册：档案终止 + 死亡）

| 日期 | 条数 | 备注 |
|------|------|------|
| 2026-09-15 | 2197 | |
| 2026-09-19 | 2199 | |
| 2026-09-25 | 2200 | |
| 2026-09-28 | 2201 | |
| 2026-10-04 | 2202 | 新增：简秀兰（档案编号 34080200300501571，女，64岁） |
| 2026-11-06 | 2224 | 当前基准（本周对比用） |

每周跑完周对比后，把新日期/条数/新增人员追加到本表，并更新上方「周对比基准文件」里的最新份数字。

## 输入法开关（XTest 注入前必关，收尾必开）

平台控制台需要纯英文输入，fcitx 会把字母变成拼音。**成对使用两个脚本，不要手工 pkill/fcitx -r**：

```bash
~/.hermes/scripts/ime_off.sh      # 关输入法，并挂 25 分钟自动恢复的死人开关
~/.hermes/scripts/ime_on.sh       # 收尾恢复，必须看到 IME_ON service=active
```

- `ime_off.sh` = `systemctl --user stop fcitx-ime.service` + 一个 systemd 计时器（即使本 turn 卡在压缩/被中断，到点也会自动拉起输入法）。
- **恢复要提前做**：relay.log 出现 `ALL_DONE` 后先跑 `ime_on.sh`，再去解析数据、生成报告——把恢复排在长耗时步骤之前，避免后面卡住又忘。
- 旧做法已作废：`pkill -f fcitx` 现在会被 `Restart=always` 五秒内复活（拼音垃圾会中途回来）；`DISPLAY=:10.0 fcitx -r &` 起的进程落在网关 cgroup，网关一重启就丢（历史上两次"输入法又丢了"都是这个原因）。
- **开跑前自检**：`systemctl --user is-active fcitx-ime.service` 应为 active（说明保险丝已归位）；若是 inactive 说明上次任务异常退出、计时器尚未触发，先开跑（本来也要关），收尾时务必 `ime_on.sh`。

## 收尾与防卡死

- **先把输入法恢复再谈别的**：见上节，`ALL_DONE` → `ime_on.sh` → 解析数据。
- **先查 relay.log 再调试**：数据提取完成后，agent 不应再进入 X11 键盘注入调试循环（如尝试打开 DevTools）。relay.log 中的 `ALL_DONE` 标记是提取完成的可靠信号——看到它就解析日志、生成报告、结束，不要再碰浏览器输入通道。
- **阻塞式命令必须加 timeout**：`xinput test`、`xev` 等 X11 事件监听命令会无限阻塞（没有超时机制），在 Hermes 终端里调用会导致整个 turn 挂死数小时。若必须监听事件，用 `timeout 5 xinput test ...` 包裹，或改用 `xinput test --once`（只捕获一次事件后退出）。
- **X11 输入通道失效时的降级策略**：如果 Web Console JS 通道正常工作（relay 能收到 POST），不要尝试用 X11 键盘注入修复/调试输入问题——直接跳过该步骤。JS 通道是主通道，键盘注入只是打开 DevTools 的辅助手段，DevTools 本身不是数据提取的必要条件。

## 坑补充

- **平台会话随时会过期**（ASP.NET 服务端会话超时，比 20 分钟更激进——会话中途也会丢）：开跑前先验证登录态，`curl -s -o /dev/null -w '%{http_code}' http://39.145.39.228:9098/pages/defaultMain.aspx` 返回 **200=已登录、302=已过期**（302 的 Location 指向 /Login.aspx）。过期则等用户重新人工登录（验证码）后立即执行完整计划。注意：本地 curl 探测**不要带 -L** 跟随重定向，避免无谓的额外请求。**会话过期后浏览器会回到 Login.aspx**——此时 addTab/Pages 变量全部消失，所有依赖主框架的 JS 注入都会失败（NOLIST、Pages is not defined）。看到这些错误先探测 location.href 确认是否在登录页，而不是反复重试 JS。
- **relay.py 端口冲突**：上次会话遗留的 relay 进程可能仍占着 8899（cwd 在 skill scripts 目录），新启动的会静默退出。先 `ss -tlnp | grep 8899` 查占用，kill 旧 PID 再启自己的；relay.log 写在**该进程 cwd**，别找错地方。
- **get_death_date.js / check_services.js 的目标名单是硬编码的**（targets 数组 / `__NAME__` 占位符），每周跑前必须替换成本周新增人员。⚠️ **替换必须用 Python 的 `re.sub(...flags=re.S)`**，不要用 `sed 's|...|...|'`——sed 表达式里含 `\n` 或中文引号时容易报错，而 `> 临时.js` 重定向会先把目标文件截断成 0 字节，导致 relay fetch 到空 payload（HTTP 200 但 body 0 字节）、脚本静默不执行。生成临时文件后先 `wc -c` 确认非零再 fetch。
- **终止原因栏可能填的是日期**（如吴仲伦 reason=2017年03-30），以 dEndingDate 为准；健康档案浏览器基本信息区的「终止日期」可交叉验证。
- **健康体检表的列序**：…| 体检服务开始 | 下次服务 | 单位 | 医生 | … | **录入时间**。最后一列是滞后录入时间，可能晚于死亡日期——判断"死亡后服务"要看实际执行/随访日期列，别被录入时间误导。

## 坑

- **Firefox 窗口可能处于 IsUnmapped**（被切到别的虚拟桌面/隐藏），xwininfo 显示 `Map State: IsUnMapped`、尺寸 1x1。本机装了 xdotool（`/usr/bin/xdotool`）：`DISPLAY=:10 xdotool windowfocus <winid> && xdotool key F12` 可简单可靠地打开 DevTools。需要字符级输入时用 python-xlib（先 `w.map()`，再向 root 发 EWMH `_NET_ACTIVE_WINDOW` ClientMessage（data=(32,(1,0,0,0,0))），最后 `D.set_input_focus(w_id,...)`。窗口 id 从 `xwininfo -root -tree | grep Firefox` 找带「迎江区」标题的那个。
- ASP.NET postback 后 iframe document 引用不变（同文档重渲染），JS 里缓存的 doc 引用继续有效。
- 下拉框直接 `el.value='x'` 赋值即可，postback 会带上；无需模拟 change 事件。
- 会话空闲约 20 分钟超时——用户重新登录后立即执行完整计划（验证码无法自动识别）。
