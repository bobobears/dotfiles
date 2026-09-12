# 执业范围级联多选选择器（前端的实现）

## 场景

需要在表单中实现「大类 → 子项」二级多选，且支持多选大类（勾选大类后显示其子项）、子项多选、标签删除回退等交互。

适用于医疗系统内的执业范围、职称分类、专业技能等多级多选场景。

## 数据结构（Jinja2 模板侧）

存储在数据库中为逗号分隔的文本值，如：`"全科, 内科, 药学专业"`。

**隐藏字段承载最终值：**

```html
<input type="hidden" id="practice_scope"
       value="{{ employee.practice_scope if employee else '' }}">
```

## 数据定义（JS 侧）

```javascript
const SCOPE_DATA = {
    '医学': ['全科', '内科', '外科', '妇产科', '儿科', '骨科', '儿童保健', '妇女保健', '精神科', '影像专业', '中医专业', '中西医结合', '中医康复'],
    '药学': ['药学专业', '中药学专业'],
    '护理': [],
    '辅助': ['化验'],
    '其他': [],
};
```

## HTML 结构

```html
<div class="practice-scope-selector">
    <!-- 大类 checkbox -->
    <div class="scope-category-select">
        <label class="sub-label">选择分类（可多选）</label>
        <div class="checkbox-group">
            <label class="checkbox-item">
                <input type="checkbox" class="scope-cat" value="医学"> 医学
            </label>
            <!-- 重复其他大类... -->
        </div>
    </div>
    <!-- 子选项容器（动态渲染） -->
    <div id="scopeSubOptions" class="scope-sub-options"></div>
    <!-- 已选标签 -->
    <div class="scope-selected-tags" id="scopeSelectedTags"></div>
    <!-- 隐藏字段提交用 -->
    <input type="hidden" id="practice_scope" value="">
</div>
```

## 核心逻辑（4 个函数）

### 1. `renderSubOptions()` — 大类勾选时渲染子项

- 清空 `#scopeSubOptions` 容器
- 遍历所有已勾选大类，对有子项的大类生成 `<div class="scope-sub-group active">`
- 内嵌子项 checkbox，类名 `.scope-sub-cb`
- 每次渲染后重新绑定 `change` 事件到子项
- 每次渲染后调用 `updateSelectedTags()`

### 2. `updateSelectedTags()` — 汇总已选项到隐藏字段 + 渲染标签

- 遍历已勾选大类：
  - 无子项的大类（护理、其他）→ 大类名作为选中值
  - 有子项的大类 → 只取勾选的子项值
- 写入 `#practice_scope.value`（逗号分隔）
- 渲染蓝色标签（可点击 × 删除）
- **标签删除逻辑**：识别点击的值属于子项还是大类，分别取消勾选对应的 checkbox

### 3. `initScopeSelector()` — 编辑模式回显

- 从隐藏字段 `value`（由 Jinja2 回填 `{{ employee.practice_scope }}`）解析已有值
- 对每个大类：检查是否有子项在已有值中 → 勾选大类 → `dispatchEvent(new Event('change'))` 触发子选项渲染
- 延迟 50ms 后勾选对应的子项 checkbox
- 调用 `updateSelectedTags()` 更新标签

### 4. 样式联动

- 大类/子项 checkbox 的 `change` 事件中，切换父级 `.checkbox-item` 的 `checked` 类名（用于视觉反馈）
- 子项使用事件委托（监听 `#scopeSubOptions` 的 change），因为子选项是动态渲染的

## CSS 要点

```css
.checkbox-item { display: inline-flex; padding: 4px 10px; border-radius: 6px; border: 1px solid #e2e8f0; cursor: pointer; }
.checkbox-item:hover { border-color: var(--primary); }
.checkbox-item.checked { background: #dbeafe; border-color: var(--primary); color: var(--primary); }
.scope-sub-group { display: none; }
.scope-sub-group.active { display: block; }
.scope-selected-tags { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; }
.scope-tag { display: inline-flex; padding: 3px 10px; background: #2563eb; color: #fff; border-radius: 12px; font-size: 12px; }
.scope-tag-remove { cursor: pointer; opacity: 0.7; }
.scope-tag-remove:hover { opacity: 1; }
```

## 非层级独立多选组（行政/技术双轨模式）

与级联选择不同，还有一种常见场景：**多个独立的平铺多选组**，组间无层级关系，每组选项固定且独立。

适用场景：组织归属多选（行政部门、行政职务、行政级别等），每组选项互不干扰。

### HTML 结构

```html
<!-- 区块标题 -->
<div class="org-section-title">行政归属</div>

<!-- 每个字段为一组 checkbox 标签 -->
<div class="org-sub-section">
    <label class="sub-label">行政部门</label>
    <div class="org-checkbox-group" data-target="admin_dept_input">
        <label class="checkbox-item org-cb" data-value="主任室"><input type="checkbox" value="主任室" style="display:none;"> 主任室</label>
        <label class="checkbox-item org-cb" data-value="财务"><input type="checkbox" value="财务" style="display:none;"> 财务</label>
        <!-- ... 更多选项 -->
    </div>
    <input type="hidden" id="admin_dept_input" value="{{ employee.admin_dept if employee else '' }}">
</div>

<!-- 重复同结构：行政职务、行政级别、技术部门、技术职务 -->
```

### JS 逻辑（以 5 组独立多选为例）

```javascript
// 初始化：遍历所有 hidden input，解析逗号分隔值，勾选对应标签
function initOrgCheckboxes() {
    const targets = ['admin_dept_input', 'admin_position_input', 'admin_level_input', 'tech_dept_input', 'tech_position_input'];
    targets.forEach(id => {
        const hidden = document.getElementById(id);
        if (!hidden) return;
        const values = hidden.value ? hidden.value.split(',') : [];
        const group = hidden.closest('.org-sub-section').querySelector('.org-checkbox-group');
        group.querySelectorAll('.org-cb').forEach(el => {
            const cb = el.querySelector('input[type="checkbox"]');
            if (values.includes(el.dataset.value)) {
                cb.checked = true;
                el.classList.add('checked');
            }
        });
    });
}

// 点击标签切换：切换 class + checkbox 状态 + 更新 hidden input
document.querySelectorAll('.org-checkbox-group').forEach(group => {
    group.addEventListener('click', function(e) {
        const label = e.target.closest('.org-cb');
        if (!label) return;
        const cb = label.querySelector('input[type="checkbox"]');
        cb.checked = !cb.checked;
        label.classList.toggle('checked');
        // 更新对应的 hidden input
        const targetId = this.dataset.target;
        const hidden = document.getElementById(targetId);
        if (hidden) {
            const checked = this.querySelectorAll('.org-cb input:checked');
            hidden.value = Array.from(checked).map(c => c.value).join(',');
        }
    });
});
```

### 与级联模式的对比

| 特征 | 级联多选（执业范围） | 独立多选组（组织归属） |
|------|-------------------|---------------------|
| 层级 | 大类→子项，2级 | 无层级，平铺 |
| 组间关系 | 子项属于特定大类 | 各组独立无关 |
| 交互 | 勾选大类才显示子项 | 所有选项始终可见 |
| 回显 | 解析值后勾选大类→触发子项渲染→再勾选子项 | 直接遍历匹配 |
| 标签样式 | 蓝色标签可删除 | 同 label 级样式（点击切换 class） |

### 提交时序列化

```javascript
// 提交前从 hidden input 读值
const data = {
    // 其他字段...
    admin_dept: document.getElementById('admin_dept_input').value.trim() || null,
    admin_position: document.getElementById('admin_position_input').value.trim() || null,
    admin_level: document.getElementById('admin_level_input').value.trim() || null,
    tech_dept: document.getElementById('tech_dept_input').value.trim() || null,
    tech_position: document.getElementById('tech_position_input').value.trim() || null,
};
```

## 注意事项

1. **Jinja2 回填时机**：`initScopeSelector()` 依赖隐藏字段 `value` 在 HTML 中已经由 Jinja2 填好（编辑模式），所以脚本必须在 DOM 加载完后执行（放在 `</body>` 前自然就是）
2. **`dispatchEvent` 触发渲染**：编辑模式初始化时不能直接调用 `renderSubOptions()`，而应该模拟用户点击——`cb.checked = true` + `cb.dispatchEvent(new Event('change'))`，这样保持逻辑路径一致
3. **子项用事件委托**：子选项是动态生成的，直接绑定 `addEventListener` 需要在每次 `renderSubOptions()` 后重新绑定。或者可以用事件委托（监听 `#scopeSubOptions` 的 change 事件，通过 `e.target.classList.contains('scope-sub-cb')` 过滤）
4. **无子项的大类直接显示自身**：护理和执业范围的无子项大类，勾选后标签显示大类名本身（如「护理」）。不要在它们下面显示空的子选项区域
