# 将 private_db 工具脚本纳入 dotfiles 备份（仅脚本，不含 .db 业务数据）
set -e
SRC=/home/bobobears/private_db
DST=/home/bobobears/dotfiles/private_db
for f in db.py init_schema.py is_trading_day.py save_dsa_scores.py weixin_daily_digest.py weixin_init_db.py; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DST/"
done
