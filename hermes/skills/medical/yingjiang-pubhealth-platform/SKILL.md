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

## 坑

- ASP.NET postback 后 iframe document 引用不变（同文档重渲染），JS 里缓存的 doc 引用继续有效。
- 下拉框直接 `el.value='x'` 赋值即可，postback 会带上；无需模拟 change 事件。
- 会话空闲约 20 分钟超时——用户重新登录后立即执行完整计划（验证码无法自动识别）。
