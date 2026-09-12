# Popover 弹窗在表格中被 overflow 裁剪问题

## 症状

在 salary_edit.html 中点击可编辑数值单元格（补助/考勤/绩效/扣发），预期出现 popover 弹窗，但实际看不到。

## 根因

```css
/* 表格容器 → overflow:auto 裁剪了 position:absolute 的子元素 */
.table-wrap { overflow: auto; ... }
.popover { position: absolute; top: 100%; left: 50%; ... }  /* ❌ 被裁剪 */
```

## 修复

### CSS

```css
.popover {
    display: none;
    position: fixed;     /* ✅ 脱离文档流 */
    z-index: 1000;       /* ✅ 确保在最上层 */
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: 0 10px 25px rgba(0,0,0,.12);
    padding: 16px;
    min-width: 260px;
}
.popover.open { display: block; }
```

### JS（当前生效版本 — 智能方向 + 防溢出）

当表格有多行，底部行的单元格点击时下方空间不足，应该自动向上弹。增强版检测上下可用空间，选择空间较大的一方弹出：

```javascript
function openPopover(e, id) {
    e.stopPropagation();
    document.querySelectorAll('.popover.open').forEach(p => {
        if (p.id !== id) p.classList.remove('open');
    });
    const el = document.getElementById(id);
    if (el) {
        if (el.classList.contains('open')) { el.classList.remove('open'); return; }

        // 先显示一次以测量实际高度
        el.classList.add('open');
        el.style.top = '0px';
        el.style.left = '0px';

        const rect = e.currentTarget.getBoundingClientRect();
        const popH = el.offsetHeight;
        const spaceBelow = window.innerHeight - rect.bottom - 10;
        const spaceAbove = rect.top - 10;

        let top;
        if (spaceBelow >= popH || spaceBelow >= spaceAbove) {
            top = rect.bottom + 6;       // 向下弹出（优先）
        } else {
            top = rect.top - popH - 6;   // 向上弹出（下方不够）
        }

        el.style.top = Math.max(6, top) + 'px';
        el.style.left = Math.max(10, Math.min(
            rect.left + rect.width/2 - 130, window.innerWidth - 280
        )) + 'px';

        // 最终防溢出：如果底部还是溢出了，强制拉回
        const finalBottom = parseInt(el.style.top) + popH + 10;
        if (finalBottom > window.innerHeight) {
            el.style.top = Math.max(6, window.innerHeight - popH - 10) + 'px';
        }
    }
}
```

**重要**：必须先将 `el.classList.add('open')` + reset 到 `0px`，才能测到 `offsetHeight`。测完后根据 `spaceBelow` vs `spaceAbove` 选择方向，最后强制防溢出钳位。

## 验证

- 点击最右列单元格，弹窗左边界不超出窗口
- 点击最左列表格，弹窗左边界 ≥ 10px
- 多次点击切换正确关闭/打开
- 点击页面空白处关闭所有弹窗（`document.addEventListener('click', ...)`）
- **点击表格底部行**，弹窗自动向上弹出而非被裁剪
- **极端底部**（弹窗上方空间也不足），强制钳位到屏幕底部留 10px 余量
