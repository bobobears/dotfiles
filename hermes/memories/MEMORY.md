LAN subnet: 192.168.31.0/24, router: 192.168.31.1 (Xiaomi/XiaoQiang), Dell machine: 192.168.31.113, this machine: 192.168.31.149。本机局域网应用端口：HRMS 8000、会议通知发布台 8077（~/meeting_notice，systemd --user meeting-notice）
§
新技能安全审计规则：创建或安装任何新技能后，必须用 security-audit 的 audit_skills.py 审计该技能，确认无 HIGH/MEDIUM 安全问题后才算完成。发现问题的必须先修复再交付。
§
三者DM策略均pairing。WeCom自建应用回调需公网HTTPS; 日志查 logs/gateway.log。iLink微信限流(errcode -2)不可根治→cron通知统一走飞书；weixin.extra 已调 send_chunk_delay_seconds=4s、circuit 60s（改后须用户外部重启 gateway）
§
通达信盘后数据路径: /home/bobobears/thinclient_drives/E:/zd_hazq_gm/vipdoc/{sz,sh}/lday/。深交所 sz{code}.day，上交所 sh{code}.day。struct格式 <iiiiifii，价格缩放100。每日分析 cron job (c1da698090bf) 已配置为外网搜索失败时的 fallback 数据源。
§
salary_basics 参数页面现状：8分类41条（基本工资、行政/岗位/技能/工龄补助等级、社保、公积金、考勤）。考勤含一般加班50/天、节日加班100/天、春节加班160/天。事假/病假扣款自动计算：(基本工资+四项补助)/21.75。公积金按行政等级分5档（正职7500~无级别2500）。无"其他"分类
§
HRMS 后端验证规范：端到端验证脚本写入 `/tmp/hermes-verify-*.py`，完成后清理。创建测试员工用 `TEST{timestamp}` 前缀，验证后 DELETE 清理
§
HRMS 员工部门字段回填：16人 department=NULL 但 admin_dept 也未填，考勤/工资页面已加 COALESCE(department, admin_dept, '未分配') SQL 回退模式
§
HRMS admin 账号密码: admin / admin123（SHA256 哈希存于 db/hrms.db users 表）。数据库路径: /home/bobobears/hrms/db/hrms.db（非 backend/employees.db，后者为空文件）。systemd user service 位于 ~/.config/systemd/user/hrms.service，已修复 User= 指令问题。
§
本地Qwen长上下文可卡死~57分钟(流中断自动切回deepseek)；vision/标题等辅助任务走lmstudio会被拖垮全超时；股票cron(c1da698090bf)固定deepseek-v4-flash
§
HRMS 薪酬参数计算公式：病/事假扣款日工资基数 = (基本工资+岗位补助+技能补助+工龄补助+行政补助+特殊补助)/21.75。deduct_absent_day=0 表示按日工资基数全额扣，deduct_sick_day=0 表示按日工资基数×30%扣。参数>0 则为固定金额。行政级别公积金映射：主管→supervisor(3750)，主办→chargeman(3125)。
§
HRMS 薪酬手动修改优先规则：基本工资、四项补助（行政/岗位/技能/工龄）、社保、公积金一旦手动修改，新建工资表时优先沿用上月手动值，不从薪酬参数重新计算。结算考勤时不覆盖 deduct_social、deduct_housing、deduct_other 手动值。
§
HRMS 返聘人员不计工龄：calc_employee_allowances 中 employment_type='返聘' 时 allow_seniority 强制为 0。
§
HRMS 考勤结算小数问题：api_batch_settle_attendance 中所有考勤数量用 round(float()*rate, 2) 而非 int()，避免 0.5 次外勤被截断为 0。
§
HRMS 工资表人员固定排序（27人）：金驰、蔡旭凯、陈东升、陈胜、朱静涛、檀小平、朱精灵、雷童童、刘炜、占梦莹、叶圣婷、韩维娜、张雪玲、娄蓉、方珍华、董春霞、白川、马燕妮、姚万利、张昌义、陈实庆、王柳青、江爱军、潘功寅、王丰荣、张晶、江浩。通过 employees.display_order 字段实现。
§
x-terminal-emulator 指向 gnome-terminal
§
用户偏好：先看效果再决定下一步。TTS：默认 provider=edge，voice=zh-CN-XiaoxiaoNeural；Piper 本地引擎已装（piper-tts 1.6.0 in hermes venv），中文语音 zh_CN-huayan-medium 手动从 hf-mirror 下到 ~/.hermes/cache/piper-voices/（piper 下载器硬编码 huggingface.co，国内不可用）
§
大模型/GGUF 下载优先 ModelScope：列表 https://www.modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true；直链 .../models/{repo}/resolve/master/{文件}（302 cdn-lfs-cn-1）。aria2c --user-agent="Mozilla/5.0"；预分配大小中途看似完成，须 sha256 验证。LM Studio 接入：外部 GGUF 不显示（三层：文件+hub注册+download-jobs/single-downloads）；官方代理 0.3MB/s，用 ModelScope 同字节文件替换；pkill "LM-Studio.AppImage" 匹配不到运行时进程 /tmp/.mount_LM-Stu.../lm-studio；lms import --hard-link -y --user-repo {user}/{repo} 注册本地文件
§
GitHub Releases 镜像：ghproxy.com 超时不可用，ghfast.top 可用且快
§
重型精神障碍患者库:~/smd_db/(smd.db+smd.py),新增INSERT patients(seq_no=max+1)+change_log留痕。seq_no管理序号,花名册呈现号导出重编勿混;.bak在~/下载/精神障碍管理/。只用本地模型。导出新增行须格式统一纳入外边框(make_table base_row回退)。国标14表已建库(forms_schema.py);每新增对象必填四表:5知情同意/6基本信息/7补充表/8随访记录,smd.py forms核查
§
医学知识库：~/private_db/knowledge/（db/knowledge.db + medical目录 + source原文），流程见 skill: medical-guideline-kb。四库：指南规范、医保监管规则(insurance_rules/codes)、2025药品目录(yb_drugs 4853)、安徽服务价格(皖医保发〔2025〕18/22号,yb_price_items 4313含单价)。
§
/etc/hosts: open.feishu.cn 固定IP已注释改用真实DNS（CDN IP轮换勿pin飞书）；weixin/deepseek仍固定。推送失败先查hosts；改文件用 pkexec sed -i。网关重启会中断运行中cron任务，修完手动补跑
§
Hermes web 后端=tavily(密钥在.env)，firecrawl 作 keyless 兜底；排障见 skill: hermes-web-search-backend
§
企微机器人显示名『小卫』（改名只在企微管理后台，Hermes 侧无名称配置；仅改显示名不动 Bot ID/Secret）。企微群已接管: chatid=wr7Gw1CwAAEFxK5lWVLCSXk6NC-rnVKg（华中路街道社区卫生服务中心）—— 单位办公群，仅办公事务，禁提股票/投资/私人话题；群级规矩写在 platforms.wecom.channel_overrides.<群id>.system_prompt（网关层，非适配器 channel_prompts；替换临时提示层不动 SOUL.md）。group_policy=allowlist 仅放行 bobobears; 群内只收@、只能被动回复，主动推送需另建群机器人 webhook
§
本机桌面是 xrdp 远程会话(DISPLAY :10,2560x1440)；已设 allow_multimon=false 单屏，根治窗口跑出屏幕；改 xrdp.ini 需 pkexec+重启，会使旧会话失联(须先杀旧会话)；详见 skill x11-window-recovery