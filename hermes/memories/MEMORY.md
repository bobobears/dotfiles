LAN 192.168.31.0/24, 路由 .1, Dell .113, 本机 .149。局域网端口：HRMS 8000、会议通知 8077、dsh-web 3080(token从journal取)。systemd陷阱：ExecStartPre 里 pkill -f "xxx" 会匹配到执行它的 sh -c 自身命令行致自杀重启循环，用 pgrep -x <进程名> -f 精确匹配
§
新技能安全审计规则：创建/安装任何新技能后，必须用 security-audit 的 audit_skills.py 审计该技能（批量入库等场景用户也会主动要求），确认无 HIGH/MEDIUM 问题才交付。
§
三者DM策略均pairing。WeCom自建应用回调需公网HTTPS; 日志查 logs/gateway.log。微信渠道已停用(config.yaml weixin.enabled=false, 2026-11-12 用户要求解除托管，日报cron f61b57775a68已删)；cron通知统一走飞书
§
通达信盘后数据路径: /home/bobobears/thinclient_drives/E:/zd_hazq_gm/vipdoc/{sz,sh}/lday/。深交所 sz{code}.day，上交所 sh{code}.day。struct格式 <iiiiifii，价格缩放100。每日分析 cron job (c1da698090bf) 已配置为外网搜索失败时的 fallback 数据源。
§
salary_basics 参数：8分类41条（基本工资、四项补助等级、社保、公积金、考勤）。加班：一般50/节日100/春节160元每天。事假病假扣款=(基本工资+四项补助)/21.75。公积金按行政等级5档(正职7500~无级别2500)。无“其他”分类
§
HRMS 部门字段回退用 COALESCE(department, admin_dept, '未分配')
§
HRMS admin 账号密码: admin / admin123（SHA256 哈希存于 db/hrms.db users 表）。数据库路径: /home/bobobears/hrms/db/hrms.db（非 backend/employees.db，后者为空文件）。systemd user service 位于 ~/.config/systemd/user/hrms.service，已修复 User= 指令问题。
§
本地Qwen长上下文可卡死~57分钟(流中断自动切回deepseek)；vision/标题辅助任务走lmstudio会全超时；股票cron(c1da698090bf)固定deepseek-flash。DeepSeek官方仅两个id: deepseek-flash(=V4.1-Flash,1M,多模态)、deepseek-v4-pro；deepseek-v4-flash是旧版号别名，deepseek-chat/-reasoner已退役(靠本地重映射救)
§
HRMS 薪酬参数计算公式：病/事假扣款日工资基数=(基本工资+岗位补助+技能补助+工龄补助+行政补助+特殊补助)/21.75；deduct_*_day=0表示按比例(事假全额/病假30%)，>0为固定金额。行政级公积金映射详见 skill。
§
HRMS 薪酬手动修改优先规则：基本工资、四项补助（行政/岗位/技能/工龄）、社保、公积金一旦手动修改，新建工资表时优先沿用上月手动值，不从薪酬参数重新计算。结算考勤时不覆盖 deduct_social、deduct_housing、deduct_other 手动值。
§
HRMS 返聘人员不计工龄：employment_type='返聘' 时 allow_seniority=0。
§
HRMS 考勤结算小数问题：api_batch_settle_attendance 中所有考勤数量用 round(float()*rate, 2) 而非 int()，避免 0.5 次外勤被截断为 0。
§
HRMS 工资表固定排序(27人)由 employees.display_order 字段决定，名单见库内
§
用户偏好：先看效果再决定下一步；Piper zh_CN-huayan-medium在~/.hermes/cache/piper-voices/（piper下载器硬编码hf.co，国内不可用）
§
大模型/GGUF 下载优先 ModelScope：列表 https://www.modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true；直链 .../models/{repo}/resolve/master/{文件}（302 cdn-lfs-cn-1）。aria2c --user-agent="Mozilla/5.0"；预分配大小中途看似完成，须 sha256 验证。
§
GitHub Releases 镜像：ghproxy.com 超时不可用，ghfast.top 可用且快
§
重型精神障碍患者库:~/smd_db/(smd.db+smd.py),新增先查 change_log 同姓同名防重，再INSERT patients(seq_no=max+1)+change_log留痕。seq_no管理序号,花名册呈现号导出重编勿混;.bak在~/下载/精神障碍管理/。只用本地模型。导出新增行须格式统一纳入外边框(make_table base_row回退)。国标14表已建库(forms_schema.py);每新增对象必填四表:5知情同意/6基本信息/7补充表/8随访记录,smd.py forms核查
§
公卫工作量统计表：权威文件 ~/private_db/knowledge/medical/工作量统计/YYYY年M月公卫工作量统计表.xlsx，录入后同步到 ~/下载/精神障碍管理/YYYY.M/ 同名文件。格式：序号|时间(m"月"d"日")|姓名|档案录入(份)|电话访视(次)|上门访视(次)|其他；新增患者记"其他"列"新增N份"，不编造未汇报条目
§
/etc/hosts: open.feishu.cn 固定IP已注释改用真实DNS（CDN IP轮换勿pin飞书）；weixin/deepseek仍固定。推送失败先查hosts；改文件用 pkexec sed -i。网关重启会中断运行中cron任务，修完手动补跑
§
Hermes web 后端=tavily(密钥在.env)，firecrawl 作 keyless 兜底；排障见 skill: hermes-web-search-backend
§
企微机器人显示名『小卫』（改名只在企微管理后台，Hermes 侧无名称配置；仅改显示名不动 Bot ID/Secret）。企微群已接管: chatid=wr7Gw1CwAAEFxK5lWVLCSXk6NC-rnVKg（华中路街道社区卫生服务中心）—— 单位办公群，仅办公事务，禁提股票/投资/私人话题；群级规矩写在 platforms.wecom.channel_overrides.<群id>.system_prompt（网关层，非适配器 channel_prompts；替换临时提示层不动 SOUL.md）。group_policy=allowlist 仅放行 bobobears; 群内只收@、只能被动回复，主动推送需另建群机器人 webhook
§
本机桌面=xrdp DISPLAY :10(2560x1440，单屏)。输入法 fcitx4 由 systemd 用户单元 fcitx-ime.service 常驻，勿在网关内启动(网关重启即丢)
§
本机 GB10 统一内存 121GiB(CPU/GPU 共用)，nvidia-smi 报 N/A。内存耗尽时加载 30GB 模型 → NVRM NV_ERR_NO_MEMORY → 整机硬挂(无 systemd 关机流程)。本地推理：llama-server.service(user) 127.0.0.1:1234，qwen3.8-27b@q8_0，~/models/qwen3.8-27b，llama-run.sh 预检(<55G拒载)。2026-11-03已加--mmproj，主服务直接支持图片/vision_analyze，不用起临时1235实例。mem-guard.timer：WARN<55G只日志、CRIT<30G停llama+飞书（用户设的极限值，未达不反馈）、DANGER<10G杀进程兜底；脚本~/.local/bin/mem-guard.sh。桌面App后端曾膨胀86-90GB被OOM连杀。详见 skill lm-studio
§
记忆规范：更新时精化而非覆盖，变更留旧值→新值+原因+日期；stale条目主动标记。周度consolidation cron周六17:30。任务结束须明说结论
§
华中路街道社区卫生服务中心（金医生单位，公文落款/资金拨付申请用）：全称『安庆市迎江区华中路街道社区卫生服务中心』，账号34001685808053007634，开户行建行安庆华中路支行
§
知识库入库工作流偏好：先出待入库清单→用户确认→批量执行，不自动入库（2026-11-03 用户纠正）