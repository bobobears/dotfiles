# Cron Fallback Prompt 示例

Hermes cron 在处理每日股票分析时，如果 DeepSeek API 短暂不可用（Broken pipe），需要执行降级策略。

下面是在 `stock-analysis-automation` 任务的 cron prompt 中实际使用的 fallback 逻辑：

## 完整的 cron prompt 结构

```
执行每日股票分析，仅在交易日运行。工作目录已在 /home/bobobears/dsa。

## 交易日前置检查
先执行：python3 /home/bobobears/private_db/is_trading_day.py
- 如果输出包含"是"或"true"或"交易日" → 继续
- 否则 → 输出"今日非交易日，跳过分析"并结束

## 主流程（首选途径：DeepSeek 分析）
步骤 1 — 获取数据：python3 main.py --dry-run
步骤 2 — 读取数据报告，确认数据完整性
步骤 3 — LLM 分析（使用当前对话模型）
步骤 4 — 生成报告，推送飞书

## 🛡️ Fallback 流程
如果在步骤 3 遇到 DeepSeek API 调用失败：

### Fallback A — 本地模型
curl http://127.0.0.1:1234/v1/chat/completions
使用 qwen3.5-35b-a3b 模型，temperature=0.3

### Fallback B — 纯脚本基础报告
执行 python3 main.py --dry-run，然后读取最新数据生成：
- 每只股票最新价、5日均价、涨跌幅
- 无 AI 分析，纯数据摘要

### Fallback C — 推送错误通知
"股票分析今日因API不可用未能完成，请手动在Hermes中运行分析"
```

## 为什么不用 Hermes 内置 fallback_providers

1. `hermes config set fallback_providers` 写入 config.yaml 时被存为字符串而非列表，且 Hermes 不消费该字段
2. Hermes 框架不提供 cron 级别的 provider fallback 链
3. 最务实的方案：在 prompt 中通过 curl 手动调用备用 API

## 锁定 cron 的任务 provider

在创建/更新 cron 任务时务必传入 `model` 参数锁定 provider：

```python
cronjob(
    action='update',
    job_id='c1da698090bf',
    model={"provider": "deepseek", "model": "deepseek-chat"}
)
```

这样即使全局配置通过 `hermes config set model.provider` 切换到了 LM Studio，该 cron 任务仍然使用 DeepSeek 稳定执行。
