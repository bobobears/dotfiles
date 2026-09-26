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
- **导出Excel** → `~/下载/档案终止、移交、封存管理表<时间戳>.xls`，真 OLE2 格式，pandas+xlrd 读，**header=2**（前两行是标题和查询地区）
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

周对比时建议对新增人员补查死亡日期后写入明细 CSV 的「终止原因/死亡日期」两列。

## 死亡后服务记录核查（健康档案浏览器）

查某人「死亡后是否还有服务记录」：列表页按姓名定位行 → **读该行档案号链接 onclick 里的真实 personid** → `Visiting(personid, name)` 打开健康档案浏览器（ShortcutsList.aspx）→ 遍历子标签提取含日期的数据行。

- ⚠️ **personid 坑**：`Visiting()` 第一参数是行内 `<a onclick="Visiting('...','姓名')">` 里的值，**可能是 GUID**（如操乐成 `8113432c-...`），不一定是档案编号。传错会打开空白页（基本信息全空、导航菜单不渲染）——这是参数错的信号，不是数据缺失。
- 健康档案浏览器结构：顶层 `.headerMenu li`（居民健康档案/慢性病管理…）→ 子标签 `.headersubMenu li`（个人档案/健康体检/接诊记录/高血压确诊·随访管理/糖尿病确诊·随访管理/慢阻肺确诊管理…，按该人慢病动态增减）→ 内容在 `id=子标签名+'_IFrame'` 的 iframe 里。
- 服务记录 = 各子标签表格中含 `yyyy-MM-dd` 的行（体检日期、随访日期等）。个人档案页底部还有「卫生健康服务活动记录」表。基本信息区含**终止日期**（可交叉验证死亡日期）。
- 参考脚本：`scripts/check_services.js`（自动读行链接 personid → Visiting → 遍历全部子标签回传数据行，relay 输出 `SUB[模块/子标签] ROWS(n): [...]`）。每人跑一次约 1.5 分钟。

## 周对比基准文件

- 位置 `~/下载/档案终止管理/`，命名 `迎江区死亡人员花名册_档案终止且死亡_<N>条[_<日期>].csv`；最新一份（2026-09-25：2200条）即下次对比的基准。每次跑完周对比用新导出重建该 CSV 并更新技能里的数字。
- **导出文件落点不固定**：有时在 `~/下载/` 根目录，有时在 `~/下载/档案终止管理/`——按 mtime 找最新 .xls 即可，别写死路径。

## 坑补充

- **relay.py 端口冲突**：上次会话遗留的 relay 进程可能仍占着 8899（cwd 在 skill scripts 目录），新启动的会静默退出。先 `ss -tlnp | grep 8899` 查占用，kill 旧 PID 再启自己的；relay.log 写在**该进程 cwd**，别找错地方。
- **get_death_date.js / check_services.js 的目标名单是硬编码的**（targets 数组 / `__NAME__` 占位符），每周跑前必须替换成本周新增人员。check_services.js 用 `sed "s/__NAME__/姓名/" check_services.js > cs_xxx.js` 生成临时文件再 fetch。
- **终止原因栏可能填的是日期**（如吴仲伦 reason=2017年03-30），以 dEndingDate 为准；健康档案浏览器基本信息区的「终止日期」可交叉验证。
- **健康体检表的列序**：…| 体检服务开始 | 下次服务 | 单位 | 医生 | … | **录入时间**。最后一列是滞后录入时间，可能晚于死亡日期——判断"死亡后服务"要看实际执行/随访日期列，别被录入时间误导。

## 坑

- **Firefox 窗口可能处于 IsUnmapped**（被切到别的虚拟桌面/隐藏），xwininfo 显示 `Map State: IsUnMapped`、尺寸 1x1。本机**没装 xdotool/wmctrl**，用 python-xlib：先 `w.map()`，再向 root 发 EWMH `_NET_ACTIVE_WINDOW` ClientMessage（data=(32,(1,0,0,0,0))），最后 `D.set_input_focus(w_id,...)`。窗口 id 从 `xwininfo -root -tree | grep Firefox` 找带「迎江区」标题的那个。
- ASP.NET postback 后 iframe document 引用不变（同文档重渲染），JS 里缓存的 doc 引用继续有效。
- 下拉框直接 `el.value='x'` 赋值即可，postback 会带上；无需模拟 change 事件。
- 会话空闲约 20 分钟超时——用户重新登录后立即执行完整计划（验证码无法自动识别）。
