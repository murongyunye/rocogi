# rocogi UI v2 设计规范 — RocoFluent

> 骨架参考 [Microsoft Fluent UI](https://github.com/microsoft/fluentui) 2 的布局/密度/层级/焦点体系，
> 皮肤参考 [rocokingdom-ui](https://github.com/rookie-orange/rocokingdom-ui)（[文档站](https://rocokingdom-ui.vercel.app)）的《洛克王国：世界》视觉令牌。
> 本规范为 rocogi（洛克工坊）的前端 `frontend/`（Vue 3 + Vite）重新设计 UI。
> 交付物：`roco-fluent.css`（可直接 import 的设计系统）+ `demo.html`（免构建交互演示）。

## 0. 快速预览

```
下载本目录后直接双击 demo.html（无需 node / npm），即可浏览：
总览仪表盘 → 工作流 → 运行记录 → 运行详情 → 设置弹窗（左侧导航「设置」）。
```

## 1. 设计原则

1. **Fluent 骨架，洛克皮肤**：布局、间距（4px 网格）、控件密度、焦点环、层级采用 Fluent 2 习惯；色彩、圆角气质、阴影手感来自 rocokingdom-ui 的「纸面/石材/金色」材料体系。工具是生产力工具，但壳子要有游戏味。
2. **可读性优先于装饰**：奶油纸底 `#f4f0e8` 上正文一律 `#222`；金色只做强调（主按钮/选中态/进度），不大面积铺。金色上文字用深色 `#242628`（对比度 ≈ 8.2:1）。
3. **深浅分区**：侧栏与遮罩用「石材」深色系，内容区用「纸面」浅色系——一块石板配一张羊皮纸，天然分区，不需要额外分割线。
4. **游戏感只允许两种形式**：① 主按钮的硬阴影（`0 2px 0`，按下位移 2px，像真的按钮）；② 页面标题区的符文水印（5% 透明度大字，纯装饰）。动画克制（≤180ms），不干扰自动化观测。
5. **安全状态可视化**：`allow_injection=false`、`本地优先 · 不读内存`、热键 F9/F10/F11 等安全语义在 UI 上常驻可见。

## 2. 色彩令牌（对照 rocokingdom-ui `packages/tokens/src/index.ts` 实测值）

| 令牌 | 值 | rocokingdom 对应 | 用途 |
| --- | --- | --- | --- |
| `--rf-paper` | `#f4f0e8` | paper | 应用画布底色 |
| `--rf-paper-soft` | `#fffaf2` | paperSoft | 卡片 / 输入框表面 |
| `--rf-paper-muted` | `#e5dccd` | paperMuted | 分隔、进度槽、时间线点 |
| `--rf-paper-strong` | `#cdbcaa` | paperStrong | 强分隔 |
| `--rf-stone` | `#242628` | stone | 侧栏 / toast / 深色按钮 |
| `--rf-stone-soft` | `#393d40` | stoneSoft | 侧栏 hover |
| `--rf-stone-muted` | `#4d5358` | stoneMuted | 侧栏选中、开关未开 |
| `--rf-stone-strong` | `#141719` | stoneStrong | 遮罩 |
| `--rf-primary` | `#ffc65f` | primary | 主按钮、logo、金色强调 |
| `--rf-primary-muted` | `#f7d56f` | primaryMuted | 主按钮 hover |
| `--rf-primary-strong` | `#d89522` | primaryStrong | 主按钮按下、焦点环、tab 选中线 |
| `--rf-primary-soft` | `#fff1cf` | primarySoft | 金色标签底 |
| `--rf-success` | `#2f9e66` | success | 运行中 / 成功 |
| `--rf-danger` | `#d94b4b` | danger | 失败 / 危险操作 |
| `--rf-warning` | `#e8a13a` | （自定，与金同族） | 警告、待标定 |
| `--rf-on-paper / --rf-on-stone / --rf-on-primary` | `#222 / #f4f0e8 / #242628` | onPaper / onStone / onPrimary | 各自材料上的前景色 |

**与 Fluent 的对应**：Fluent 的 `colorBrandPrimary` 在本设计中由金色顶替；Fluent 中性灰描边 `colorNeutralStroke1(≈rgba(0,0,0,.1))` 映射为 `--rf-stroke`（暖黑 10%），保持纸面质感不发灰。

## 3. 形状 / 密度 / 排版 / 阴影

- **圆角**：控件 8px（rocokingdom `--rk-radius: 8px`，即 Fluent large）；小元素 4–6px；标签/进度条用胶囊。
- **控件高度**：24 / 32 / 40px 三档——rocokingdom 与 Fluent 密度体系在此完全重合，直接沿用。
- **字号阶梯**（Fluent 2 type ramp 裁剪）：caption 12 / body 13 / body-lg 14 / subtitle 16 / title 20 / display 28。中文栈 `"Segoe UI", system-ui, "Microsoft YaHei UI", "PingFang SC"`；坐标/ID/时间用等宽 `"Cascadia Code", Consolas`。
- **阴影**：三层环境光（Fluent 式柔影 soft/card/flyout）+ 一层游戏硬阴影 `0 2px 0 rgb(36 38 40 / .32)`（rocokingdom RocoShape 的 `drop-shadow` 手法，仅主按钮）。焦点环是 Fluent 双层 ring，颜色金色：`0 0 0 2px paper, 0 0 0 4px primary-strong`。
- **符文装饰字**：rocokingdom 有 RuneText + 自带 rune 字体（license 未明，**不随本设计分发**）。装饰效果降级实现为 `--rf-rune-bg`：5% 透明度大写字母水印（见 demo 总览页），不引入任何字体文件。

## 4. 布局

```
┌──────────┬────────────────────────────────────────────┐
│ 侧栏 232px│ 顶栏 52px：页名 │ 后端状态胶囊 │ F9/F10/F11 │ ▶运行 ■停止 │
│ (石材)    ├────────────────────────────────────────────┤
│ 洛 洛克工坊│ 内容区 max-width 1400px 居中                │
│ ─ 自动化  │   页标题 + 符文水印                          │
│  总览     │   KPI 4 卡 → 引擎状态 / 快速开始 2 卡        │
│  工作流   │   最近运行表格                               │
│  运行记录 │                                             │
│  运行详情 │                                             │
│  一条龙   │                                             │
│ ─ 知识    │                                             │
│  图鉴/对战/地图│                                        │
│ ─ 系统    │                                             │
│  组件/资源/引擎/设置│                                   │
│ ───────── │                                             │
│ 本地优先·不读内存│                                       │
└──────────┴────────────────────────────────────────────┘
```

- 侧栏项：高 32px、6px 圆角，选中态 = `stone-muted` 底 + 左缘 3px 金线（代替 Fluent 的指示条，更有「徽章栏」感）。
- 顶栏是全局命令条：后端连接状态胶囊（绿点+端口）、三个热键提示、全局 ▶/■。
- 页面组件在 `demo.html` 里给出了：总览（KPI/引擎状态/快速开始/最近运行）、工作流（搜索+表格）、运行记录、运行详情（时间线+截图卡+事件流）、设置弹窗（热键/开关/深色占位）。

## 5. 组件规范速查（`roco-fluent.css` 内类名）

| 组件 | 类 | 规格 |
| --- | --- | --- |
| 按钮 | `.rf-btn` `--primary/--stone/--danger/--outline/--subtle` `.sm/.lg` | 24/32/40px 高，8px 圆角；primary 带硬阴影，按下位移 2px |
| 卡片 | `.rf-card` `.rf-card-head` `.rf-card-body` | 8px 圆角、1px 描边、card 柔影 |
| KPI | `.rf-stat`（`.is-gold`） | display 28px 数字，caption 灰标签 |
| 表格 | `.rf-table` | 12px 表头 caption、行 hover paper-soft、ID/时间等宽 |
| 标签 | `.rf-tag` `.is-success/.is-danger/.is-warning/.is-gold/.is-stone` | 22px 胶囊；状态点 `.rf-dot` 带 3px 光环 |
| 输入 | `.rf-input/.rf-select/.rf-textarea` | Fluent 下边加粗（2px），焦点金色下边线 |
| 开关 | `.rf-switch`（`.is-on`） | 44×24，金色为开 |
| 标签页 | `.rf-tabs/.rf-tab` | Fluent 下划线式，金色选中线 |
| 弹窗 | `.rf-scrim/.rf-modal*` | 石材 45% 遮罩、paper 表面、flyout 柔影 |
| 通知 | `.rf-toast`（`.is-success/.is-gold`） | 石材底 + 左缘 3px 语义色，≤3.2s 自消失 |
| 时间线 | `.rf-timeline`（`.is-success/.is-danger/.is-running`） | 步骤竖线 + 24px 圆点，meta 用等宽 |
| 进度 | `.rf-progress` | 金色渐变 8px 胶囊条 |
| 空状态 | `.rf-empty` | 🥚 图标 + 双行文案 |
| 符文水印 | `.rf-rune-bg[data-rune]` | 5% 透明度 64px 装饰字 |

## 6. 现有页面映射（frontend/ 25 个文件）

| 现有视图 | v2 处理 |
| --- | --- |
| WorkflowsView | 表格 + 搜索工具条；「需标定」等状态改语义 tag；编辑仍进 WorkflowEditorView |
| RunDetailView | 时间线组件 + 截图卡 + 事件流（等宽 12px），WS 状态用 `.rf-tag` |
| RealtimeView | 顶栏胶囊式实时状态 + 捕获帧预览（demo 的 `.demo-cap` 占位） |
| DexView / PetView / PvpView | 同一卡片网格 + 表格组件；竞态守卫保留（DexView 的 seq 模式推广到 PetView） |
| ComponentsView / EnginesView | 引擎状态列表（demo 左卡）推广为全量版 |
| SettingsView | 表单分区 + 开关 + 危险区（demo 弹窗展开为整页） |
| 全局 | main.ts `import './design/roco-fluent.css'`；路由/状态/API 层零改动 |

## 7. Vue 落地路线（三步，全部向后兼容）

1. **令牌先行（半天）**：把 `roco-fluent.css` 放进 `frontend/src/design/`，在 `main.ts` import。此时不加任何 class，先核对视觉变量与暗色预留。
2. **外壳替换（1 天）**：App.vue 换成 `rf-shell / rf-rail / rf-topbar / rf-content` 骨架，路由视图不动。
3. **逐页迁移（2–3 天）**：按上表逐视图替换 class（`.el-*`/现自定义类 → `rf-*`）；每页迁移后跑一遍 8787 后端人工冒烟。深色主题（石材全深）在 v2.1，只需覆盖 `:root` 令牌块。

## 8. 许可与依赖说明

- 本设计**只引用** rocokingdom-ui 公开令牌中的设计常量（色值/圆角/控件高度）与公开示例中的装饰手法，全部 CSS 为原创实现，未复制其代码、字体或图片资源。
- rocokingdom-ui 是 **React 19** 组件库，而 rocogi 前端是 Vue 3，**不引入其运行时依赖**；其仓库顶层当前未见 LICENSE 文件，在作者明确授权前不应直接打包其代码/字体（`roco-kingdom-rune.ttf` 未随本设计分发）。
- 如未来需要完整的 RocoShape SVG 轮廓系统，建议联系作者（rookie-orange）确认许可后再引入。
