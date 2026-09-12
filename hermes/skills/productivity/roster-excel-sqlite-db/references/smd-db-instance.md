# 实例：重型精神障碍患者库（华中）

金医生（社区卫生服务中心）的在册患者管理库，2026-08-25 建立。

## 位置与文件
```
/home/bobobears/smd_db/
├── smd.db            # SQLite 数据库（备份只需拷这一个；含 PII，勿进公开仓库）
├── schema.sql        # patients + change_log + import_log
├── import_excel.py   # Excel 导入：python3 import_excel.py <文件> [--dry-run]
├── smd.py            # CLI: stats / list / show / update / export / log
└── README.md         # 完整使用说明（中文）
```

## 数据源格式
"在册基本信息（华中）*.xls"：Sheet1，第1行标题、第2行表头（20列）、第3行选项说明、第4行起数据。
列序：序号/姓名/身份证号码/监护人姓名/联系电话/户籍地/现住址/疾病诊断/危险评估等级(0-5)/分色定级情况/监护情况(正常|弱|无)/分色定级类型(红|黄)/是否落实双监管/弱监护四方责任书/档案所属乡镇街道/基层医疗机构名称/辖区外实际居住地/国家平台流转/是否有诊断证明/备注。

## 常用命令
```bash
cd /home/bobobears/smd_db
python3 smd.py stats                          # 分色/危险等级/监护情况统计 + 重点关注人数
python3 smd.py list --color 红色               # 或 --risk N / --diag 关键词 / --name 关键词
python3 smd.py show <姓名|身份证>              # 单人详情 + 变更历史
python3 smd.py update <key> --field phone --value ...   # 修改留痕；字段名见 README
python3 smd.py export [out.xlsx]              # 导出（默认按日期命名）
python3 smd.py log [--patient 姓名]           # 变更日志

# 新一期 Excel 到达时：
python3 import_excel.py <新文件> --dry-run    # 预览校验结果
python3 import_excel.py <新文件>              # upsert（按身份证），重复执行安全
```

## 基线数据（2026-08-25，105人）
黄色79/红色26；危险等级0级101、1级4；监护正常86/弱监护19；男58/女47。
重点关注：红色且弱/无监护 19 人，公安列管 5 人。精神分裂症 81 人为主要诊断。

## 备注
- 电话字段保留原文（含座机前缀、空格分隔多号码），未做清洗。
- 性别/出生日期由身份证推导存储（gender, birth_date 两列）。
- 源文件在 ~/.hermes/attachments/，新文件到达后按上面流程更新即可。
