---
name: x11-window-recovery
description: Use when a GUI window is lost, off-screen, or hidden.
---

# X11 窗口找回（跑出屏幕 / 跑到其他工作区）

## 触发场景
- 用户说"表格打开看不到""窗口不见了""界面偏到屏幕外""只看到右下一部分""怎么打开都看不到"
- LibreOffice 等 GUI 窗口被误移到其他工作区，或坐标变成负数

## 第一步：诊断（不要猜，先看真实状态）
用 python-xlib **递归**遍历窗口树——LibreOffice 文档窗口是 root 的孙窗口（在 `VCL ImplGetDefaultWindow` 之下），只看 root 直接子窗口会漏掉：

```python
from Xlib import display, X
d = display.Display(":10")          # 本机桌面在 :10（xrdp），:0 是空的
d0 = d.screen().root
def get_prop(win, name):
    p = win.get_full_property(d.intern_atom(name), X.AnyPropertyType)
    return p.value if p else None
def walk(win, depth=0):
    for c in win.query_tree().children:
        g = c.get_geometry(); st = c.get_attributes().map_state
        nm = c.get_wm_name() or ""
        wc = c.get_wm_class(); cls = "/".join(wc) if wc else ""
        desk = get_prop(c, "_NET_WM_DESKTOP")
        if "soffice" in cls.lower() or desk is not None:
            print(hex(c.id), g.x, g.y, g.width, g.height, "map=", st, "desk=", desk, nm[:40], cls)
        walk(c, depth+1)
walk(d0)
print("当前工作区:", get_prop(d0, "_NET_CURRENT_DESKTOP"), "共", get_prop(d0, "_NET_NUMBER_OF_DESKTOPS"))
```

判读：
- `map_state`: **0=Unmapped(不可见)、2=Viewable(可见)**
- `_NET_WM_DESKTOP` ≠ `_NET_CURRENT_DESKTOP` → 窗口在别的工作区
- `_NET_WM_STATE_HIDDEN` → 被最小化/隐藏
- **负坐标 + 窗口尺寸大于屏幕** → 跑到屏幕外（xrdp 多屏模式常见）

## 第二步：修复（EWMH ClientMessage）
```python
from Xlib import protocol, X
def send(win_id, msg, data):
    data = (list(data) + [0]*5)[:5]     # 必须 5 个 32 位整数，否则 BadDataError
    ev = protocol.event.ClientMessage(window=win_id,
         client_type=d.intern_atom(msg), data=(32, data))
    d0.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    d.sync()
CUR = get_prop(d0, "_NET_CURRENT_DESKTOP")[0]
send(WIN, "_NET_WM_DESKTOP", [CUR, 2])                  # 移到当前工作区
send(WIN, "_NET_ACTIVE_WINDOW", [2, X.CurrentTime, 0])   # 激活，消除 HIDDEN
```
窗口坐标是负数时，再用 `w.configure(x=..., y=...)` 或 `_NET_MOVERESIZE_WINDOW` 挪回屏幕内。

## 验证
重新读属性：`map=2` 且 `desk` == 当前工作区即成功；再截图目视确认内容。

## 坑（都踩过）
- **ClientMessage 的 data 必须是 5 个整数**，少一个直接抛 `BadDataError: Wrong data length`。
- **必须递归找窗口**，别只看 root 子窗口。
- **必须指定 DISPLAY=:10**（本机 xrdp 桌面），默认 :0 上什么都没有。
- **xdotool / wmctrl 未安装**；用 `uv run --with python-xlib python3` 即可，不要装系统包。
- **不要先改文件**：用户误拖窗口/切工作区不会动数据。先确认窗口，再（如需）用 xlrd 抽查文件行数。
- 截屏：`uv run --with python-xlib --with pillow`，`root.get_image(...)` → `Image.frombytes("RGB", size, raw.data, "raw", "BGRX")`；XFCE 会话下更简单的是 `DISPLAY=:10 gnome-screenshot -f out.png`。大图先 `ffmpeg -vf scale=1400:-1` 缩小再交给视觉模型，否则容易超时。
- **本机系统解释器没有 python-xlib**，别用 `/usr/bin/python3` 直接 `import Xlib`（会 ModuleNotFoundError）；用 `uv run --with python-xlib python3`，或改用免依赖的 `xwininfo -root -tree`（列窗口）、`xwininfo -id 0x…`（看 Map State/几何）、`xprop -id 0x… _NET_WM_DESKTOP _NET_WM_STATE WM_NAME`。
- **LibreOffice 崩溃恢复会卡死启动**：会话被强杀后 LO 启动时弹"文档恢复"，该对话框可能 `UnMapped` → 屏幕只见 splash、主窗口迟迟不出。解法：`pkill -x soffice.bin` 后用 `soffice --norestore --calc <文件>` 启动。移走 `~/.config/libreoffice/4/user/backup/*.bak` **挡不住**这个对话框（恢复标记不在那里），但可当备份留档。
- **LO 窗口负坐标还存在用户配置里**：`~/.config/libreoffice/4/user/registrymodifications.xcu` 中 `Factory['com.sun.star.text.TextDocument']` 的 `ooSetupFactoryWindowAttributes` 若为 `-1540,-625,2563,1392;1;,,,;`（负值=屏外），改成正常值如 `84,56,2476,1371;1;,,,;`。**必须在 LO 未运行时改**——LO 退出会整体重写该文件，运行中改会被覆盖。
- 启动 GUI 程序脱离 Hermes 终端：`systemd-run --user --unit=<名> --setenv=DISPLAY=:10 --setenv=XDG_RUNTIME_DIR=/run/user/1000 --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus <程序>`，比后台 shell 稳（不会随会话结束被杀）。
- **`pkill -f <模式>` 会自杀**：模式若出现在你自己的命令行里（如 `pkill -f "lo-w-profile"` 而同一行前面有 `cp ... /tmp/lo-w-profile`），pkill 会连你的 shell 一起 TERM → 命令中途死（exit -15），后面的步骤全没跑。改用 `systemctl --user stop <unit>`（按 cgroup 收干净），或让模式不出现在本命令行。同理 `pgrep -c -f soffice.bin` 会把自己算进去，得到虚高计数。
- **窗口标题匹配不能带前导引号**：`grep '"LibreOffice Writer"'` 匹配不到——真实标题是 `"未命名 1 — LibreOffice Writer"`。用 `grep -i writer` 再用正则筛 `^0x[0-9a-f]+ ` 开头的行。
- **LO 工厂窗口坐标不止一处**：抓取用 `grep -o 'ooSetupFactoryWindowAttributes.\{0,140\}' <xcu>`（该名字出现在 `oor:name="…"` 属性值里，不是标签，别写成 `…">`）。本机现有三处：`0,0,800,600`（另一个 factory）、`84,56,2476,1371`×2（Calc/Writer，均已正常）。
- **`.bak` 不等于未保存改动**：`~/.config/libreoffice/4/user/backup/*.bak` 是保存瞬间写入的**上一版**副本，不是崩溃时的未存草稿。判读：比 mtime（磁盘文件只晚 0.07~0.6 秒）+ 逐行比内容；磁盘文件更新更全 → 没丢东西，可直接删。切勿拿 .bak 去覆盖磁盘文件，那会把用户后续的编辑退回去。

## 根因与根治：xrdp 多屏模式
xrdp `allow_multimon=true` 时，客户端分辨率/多屏布局变化会让窗口保留旧绝对坐标 → 跑到屏幕外。

根治：`/etc/xrdp/xrdp.ini` 改 `allow_multimon=false` → 重启 xrdp。验证方式看 Xorg 日志：`rdpRRSetRdpOutputs: add output 0 left 0 top 0 width 2560 height 1440`（单输出、从 0,0 起）即生效。

本机无免密 sudo（`sudo -n` 报需要密码），改用 pkexec（polkit 弹窗由用户在桌面输密码），一次完成改配置+重启：
```bash
DISPLAY=:10 timeout 240 pkexec bash -c 'sed -i "s/^allow_multimon=.*/allow_multimon=false/" /etc/xrdp/xrdp.ini; systemctl restart xrdp; systemctl is-active xrdp'
```
⚠️ pkexec 的命令文本会被 polkit 当 Pango 标记渲染：**命令里不要出现 `&`**（否则 `Gtk-WARNING ... not a valid name`，认证仍成功但提示残缺），串联用 `;` 而非 `&&`。

### ⚠️ 重启 xrdp 的隐藏代价（务必先读再动手）
`systemctl restart xrdp` 会**连带重启 xrdp-sesman**，而 sesman.ini 默认 `KillDisconnected=false`：
- 旧会话的 Xorg 与全部应用**仍在运行**（`ps -eo pid,ppid,args | grep "Xorg :"`、`ls /tmp/.X11-unix/` 可见），但新 sesman **不认识它** → 用户重连时新建会话（换 display 号，旧 socket 占着 :10 就用 :11）。
- 新会话**立即退出**：旧 `xfce4-session` 仍占着会话管理器，`/var/log/xrdp-sesman.log` 出现 `Window manager (pid N, display M) exited quickly (0 secs)`，用户表现为"连不上"。

**正确顺序**：改配置+重启服务后，**先结束旧会话再让用户重连**：
```bash
pkill -TERM -x soffice.bin                 # 先关 LO，减少未保存风险
DISPLAY=:10 xfce4-session-logout --fast --logout   # 优雅注销旧会话
# 兜底：kill 旧 Xorg 进程（其 X 客户端随之退出），确认 /tmp/.X11-unix/X10 消失
```
注意：注销的正是承载 Hermes 桌面应用的会话 → UI 会短时断开，但 gateway 是 systemd 用户服务（`hermes-gateway.service`）不受影响、对话记录不丢；用户重连后需自行重开桌面应用。
重连后按第一步复查窗口几何：全部落在 `0..屏幕宽/高` 内才算成功。

## 验证技巧：不动用户正在运行的实例
要验证"改了配置后新窗口会不会落在屏内"，用**配置克隆的独立实例**，测完停掉，全程不碰用户开着的文档：
```bash
rm -rf /tmp/lo-w-profile && mkdir -p /tmp/lo-w-profile
cp -a ~/.config/libreoffice/4/user /tmp/lo-w-profile/user      # 克隆含 fix 的配置
systemctl --user reset-failed lo-writer-test 2>/dev/null
systemd-run --user --unit=lo-writer-test \
  --setenv=DISPLAY=:10 --setenv=XDG_RUNTIME_DIR=/run/user/1000 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  soffice -env:UserInstallation=file:///tmp/lo-w-profile --norestore --writer
# 再轮询 xwininfo 直到窗口出现，量 x/y/w/h，判 0<=x,y 且 x+w<=屏宽, y+h<=屏高
systemctl --user stop lo-writer-test        # 干净收尾（别用 pkill）
```
判据：窗口 `Map State=IsViewable` 且几何完全落在屏内。克隆 profile 保证测的是本次改的规则，独立实例保证失败也不影响用户数据（本机实测 Writer 窗口落在 `(83,56) 2476x1371`）。
