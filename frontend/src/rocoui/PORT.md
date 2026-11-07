# rocoui — rocokingdom-ui 的 Vue 3 移植

本目录是 [rocokingdom-ui](https://github.com/rookie-orange/rocokingdom-ui)（npm `rocokingdom-ui@0.0.1-beta.0`，MIT License，© Charles Lee）到 Vue 3 的移植版，供 rocogi frontend 使用。**rocogi 本身是 Vue 3 项目**，而上游组件库基于 React + Radix Primitives，因此采用「上游样式 1:1 保留、组件结构忠实重写为 Vue」的方式移植。

## 移植策略

### 1:1 原样保留（verbatim）

- `style.css` / `font.css` / `fonts/*.ttf`：npm 包 dist 产物**原文件**直接 vendor，未做任何修改（见 `LICENSE-roco-ui.md`）。
- 全部 CSS-module hash 类名映射（`rk.ts` 中的 `materialModule`/`shapeModule`/… 18 组）与 `rk-*` 稳定类前缀，逐条从上游 JSX 源码核对。
- 每个组件的类名拼接顺序（prefix → module[shape] → module[variant] → 状态类 → rootClassName）与上游一致，包括上游 beta 的已知怪癖（如 `oOidEa` 无 `center` 键导致 `align="center"` 不产类、`g-B19a` 无 solid/outline 键、toggle_group hash `6THeW` 因上游打包 bug 不在 dist CSS 中，映射为空串）。
- SVG 形状路径：`rocoShapeEdgePath` / `rocoShapeEdgeFillPath` / `rocoShapeFixedPaths` / `panelCurvePathBySide` / textarea 四角路径，全部照抄上游常量。
- CSS 变量契约（`--rk-material-*` / `--rk-roco-shape-*` / `--rk-space-*` / `--rk-layout-*` / `--rk-modal-width` / `--rk-drawer-*` / `--rk-textarea-resize` 等）与动画名（`rk-modal-*-in/out`、`rk-drawer-*-in/out`、`rk-tab-selected-pop`、`rk-switch-pop`…）一致。

### 忠实重写（React → Vue）

- React `Slot.Root`（asChild）→ `cloneVNode` 合并 class/style（`Material.ts`）。
- React Context → `provide/inject` + `reactive` context（`context.ts`）。
- Radix 依赖的交互原语 → 无依赖 Vue 实现：
  - `Select`：combobox + listbox 语义、键盘导航（↑↓/Enter/Esc/Home-End 语义同 Radix 默认）、点击外部关闭、Teleport 渲染下拉。
  - `Modal` / `Drawer`：Teleport 到 body + 遮罩点击关闭 + 焦点结构（Radix Dialog 的 focus trap/滚动锁定未实现，简化版）。
- `useId()` → Vue 同名 API；`useSyncExternalStore` 等 React 专属逻辑不适用。

### 自绘近似（docs 站有、beta 包没有）

`Badge` / `Tag` / `Breadcrumb` / `Slider` 在 [文档站](https://rocokingdom-ui.vercel.app/docs) 有页面，但 beta npm 包未导出（`index.d.mts` 已核对）。按文档语义用 `--rk-*` 令牌自绘（`extras.css`），类名使用 `rk-badge` / `rk-tag` / `rk-breadcrumb` / `rk-slider`（避开上游已占用的 hash 类）。`IconCheck` / `IconCross` 上游为外部 lucide 图标，这里内联自绘（stroke-width 2.5 对齐）。

## 使用

```ts
import { RocoTheme, Button, SideNav } from './rocoui'
```

`main.ts` 已按 `rocoui/index.ts → ./style.css` 顺序导入；`App.vue` 根节点包 `<RocoTheme>` 注入默认令牌。

## 许可

上游样式与设计 MIT（见 `LICENSE-roco-ui.md`）；本目录的 Vue 重写代码随 rocogi 项目同等开源。
