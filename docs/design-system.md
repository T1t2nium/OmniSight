# OmniSight 设计系统

> Warm Dark 主题 + 设计 token 体系。所有视觉属性通过 CSS 变量统一管理，组件零硬编码值。

---

## 设计原则

1. **暖暗优先**：基于 Warm Dark 调色板（紫灰底 + 暖色强调），比纯 GitHub Dark 更柔和
2. **分层清晰**：背景四层（primary/secondary/tertiary/hover），文本三级（primary/secondary/muted）
3. **统一间距**：4px 基准 8 级 scale，所有组件遵守同一间距体系
4. **玻璃态交互**：磨砂玻璃按钮 + 背光光晕，hover/active/disabled 五态齐全
5. **动画克制**：微交互 ≤350ms，尊重 reduced-motion 偏好
6. **渐进增强**：CSS 变量 → 组件样式 → 响应式 → 无障碍

---

## 颜色体系

所有颜色通过 CSS 变量引用，位于 `frontend/src/styles/tokens.css`。

### 背景色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-bg-primary` | `#0f0f14` | 页面底色（紫黑） |
| `--color-bg-secondary` | `#1a1a24` | 面板/卡片背景（靛灰） |
| `--color-bg-tertiary` | `#252534` | 按钮/输入框背景 |
| `--color-bg-hover` | `#32324a` | 悬停态背景 |

### 文字色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-text-primary` | `#e8e6f0` | 正文/标题 |
| `--color-text-secondary` | `#9895a8` | 副文本/标签 |
| `--color-text-muted` | `#55526b` | 禁用/占位 |

### 语义色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-accent` | `#7eb8ff` | 强调/链接/蓝色 |
| `--color-accent-soft` | `rgba(126,184,255,0.12)` | 蓝色柔和底 |
| `--color-success` | `#4ade80` | 成功/就绪/绿色 |
| `--color-success-soft` | `rgba(74,222,128,0.12)` | 绿色柔和底 |
| `--color-error` | `#f87171` | 错误/录音中/红色 |
| `--color-error-fg` | `#fca5a5` | 错误消息前景色 |
| `--color-warning` | `#fbbf24` | 警告/重连中/黄色 |

### 边框色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-border` | `#252534` | 默认边框 |
| `--color-border-hover` | `#3a3a55` | 悬停边框 |

### 渐变

| Token | 值 | 用途 |
|-------|-----|------|
| `--gradient-accent` | `linear-gradient(135deg, #7eb8ff, #a78bfa)` | 强调渐变（蓝→紫） |
| `--gradient-success` | `linear-gradient(135deg, #4ade80, #34d399)` | 成功渐变 |
| `--gradient-welcome` | `linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)` | 欢迎页渐变 |

### 按钮专用

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-btn-start-bg` | `#22c55e` | 开始按钮背景 |
| `--color-btn-start-border` | `#4ade80` | 开始按钮边框 |
| `--color-btn-start-glow` | `rgba(34,197,94,0.35)` | 开始按钮光晕 |
| `--color-btn-stop-bg` | `#ef4444` | 停止按钮背景 |
| `--color-btn-stop-border` | `#f87171` | 停止按钮边框 |

### 玻璃态按钮

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-glass-bg` | `rgba(255,255,255,0.06)` | 玻璃按钮底色 |
| `--color-glass-bg-hover` | `rgba(255,255,255,0.12)` | 玻璃按钮悬停 |
| `--color-glass-border` | `rgba(255,255,255,0.15)` | 玻璃按钮边框 |
| `--color-glass-border-hover` | `rgba(255,255,255,0.25)` | 玻璃按钮悬停边框 |
| `--color-glass-primary-tint` | `rgba(74,222,128,0.15)` | 主色调玻璃底色 |
| `--color-glass-primary-glow` | `rgba(74,222,128,0.25)` | 主色调光晕 |
| `--color-glass-danger-tint` | `rgba(248,113,113,0.15)` | 危险色玻璃底色 |
| `--color-glass-danger-glow` | `rgba(248,113,113,0.25)` | 危险色光晕 |
| `--color-glass-active-tint` | `rgba(74,222,128,0.10)` | 已激活玻璃底色 |
| `--color-glass-active-border` | `rgba(74,222,128,0.50)` | 已激活玻璃边框 |
| `--glass-blur` | `14px` | 玻璃模糊半径 |

### 聊天气泡

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-bubble-user-bg` | `#1a3a2a` | 用户气泡背景 |
| `--color-bubble-user-border` | `#2d5a3d` | 用户气泡边框 |
| `--color-bubble-ai-bg` | `#1e1e30` | AI 气泡背景 |
| `--color-bubble-ai-border` | `#2e2e48` | AI 气泡边框 |
| `--color-bubble-error-bg` | `#3d1515` | 错误气泡背景 |

---

## 间距体系

基于 4px 基准的 8 级 scale。

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `--space-1` | `4px` | 紧凑内边距、标签间距 |
| `--space-2` | `8px` | 内边距、图标间距 |
| `--space-3` | `12px` | 标准内边距、组件间 gap |
| `--space-4` | `16px` | 宽松内边距、区块间距 |
| `--space-5` | `20px` | 中等区块间距 |
| `--space-6` | `24px` | 大间距 |
| `--space-8` | `32px` | 最大间距 |
| `--space-10` | `40px` | 超大间距 |

---

## 字体体系

### 字体系列

| Token | 值 | 用途 |
|-------|-----|------|
| `--font-sans` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` | 正文/UI |
| `--font-mono` | `'JetBrains Mono', 'SF Mono', 'Fira Code', ui-monospace, monospace` | 代码/统计/时间戳 |

### 字号 Scale

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `--text-xs` | `0.65rem` | 消息元数据、标签 |
| `--text-sm` | `0.75rem` | 状态文本、统计数据 |
| `--text-base` | `0.85rem` | 按钮文本、错误消息 |
| `--text-lg` | `0.95rem` | 聊天气泡正文 |
| `--text-xl` | `1.15rem` | 中等标题 |
| `--text-2xl` | `1.35rem` | 应用标题 |

### 字重

| Token | 值 | 用途 |
|-------|-----|------|
| `--font-weight-normal` | `400` | 正文 |
| `--font-weight-medium` | `500` | 副标题 |
| `--font-weight-semibold` | `600` | 标题 |
| `--font-weight-bold` | `700` | 强调 |

### 行高

| Token | 值 | 用途 |
|-------|-----|------|
| `--line-height-tight` | `1.25` | 标题 |
| `--line-height-normal` | `1.55` | 正文 |
| `--line-height-relaxed` | `1.65` | 长文本/气泡 |

---

## 圆角体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--radius-sm` | `6px` | 标签 |
| `--radius-md` | `10px` | 按钮、输入框、消息卡片 |
| `--radius-lg` | `14px` | 面板/弹窗 |
| `--radius-xl` | `18px` | 聊天气泡 |
| `--radius-2xl` | `24px` | 大面板 |
| `--radius-full` | `9999px` | 圆形元素（指示灯） |

---

## 阴影体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.25)` | 轻微浮起 |
| `--shadow-md` | `0 4px 16px rgba(0,0,0,0.35)` | 明显浮起 |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.45)` | 大幅浮起（弹窗） |
| `--shadow-glow-green` | `0 0 14px rgba(74,222,128,0.4)` | 绿色呼吸灯 |
| `--shadow-glow-red` | `0 0 14px rgba(248,113,113,0.4)` | 红色呼吸灯 |
| `--shadow-glow-blue` | `0 0 14px rgba(126,184,255,0.4)` | 蓝色呼吸灯 |
| `--shadow-inner` | `inset 0 2px 4px rgba(0,0,0,0.2)` | 内凹深度（视频面板） |

---

## 过渡体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--transition-fast` | `0.15s ease` | hover、切换 |
| `--transition-normal` | `0.25s ease` | 连接状态变化 |
| `--transition-slow` | `0.35s ease` | 消息入场动画、面板展开 |

---

## Z-Index 体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--z-base` | `0` | 默认层 |
| `--z-status` | `10` | 状态指示器 |
| `--z-control` | `20` | 控制栏 |
| `--z-overlay` | `100` | 弹窗/下拉菜单/遮罩 |

---

## 响应式断点

| 断点 | 宽度 | 设备 | 行为 |
|------|------|------|------|
| 桌面 | > 768px | 显示器 | 960px 居中，全布局 |
| 平板 | ≤ 768px | iPad | 视频 4:3，气泡 90%，隐藏帧统计 |
| 手机 | ≤ 480px | iPhone | 视频 1:1，气泡 95%，隐藏副标题 |
| 矮屏 | ≤ 600px 高度 | 小型窗口 | 视频压缩，隐藏统计 |

---

## 组件编目

### 布局组件

| 组件 | CSS 类 | 说明 |
|------|--------|------|
| App 容器 | `.app` | flex column, 100% 高度 |
| 头部 | `.app-header` | 标题 + 副标题 + Agent 选择器 |
| 头部（面试模式） | `.app-header--interview` | 绿色标题栏 |
| 面试阶段 | `.interview-phase` | 面试进行中指示器 |
| 主区域 | `.app-main` | flex column, flex:1, overflow-y: auto |
| 顶部区域 | `.layout-top` | 视频 + 文档上传侧栏 |
| 顶部行 | `.layout-top-row` | flex row 容器 |
| 视频区 | `.layout-top__video` | 视频面板位置 |
| 侧栏 | `.layout-top__side` | 文档上传 / 题库位置 |
| 状态栏 | `.layout-status` | VAD + 统计 + 连接状态 |
| 聊天区域 | `.layout-chat` | 消息列表，可滚动（min-height: 120px） |
| 底部栏 | `.layout-bottom` | 控制按钮 |

### 核心组件

| 组件 | CSS 类 | 状态 | 说明 |
|------|--------|------|------|
| VideoPanel | `.video-panel` | 开启/关闭 | 16:9 实时镜像预览 / 摄像头图标 + "Camera Off" |
| VideoPreview | `.video-preview` | — | 视频 `<video>` 元素 |
| VideoPlaceholder | `.video-placeholder` | — | 摄像头关闭时的占位 UI |
| PlaceholderIcon | `.placeholder-icon` | — | 占位图标 |
| PlaceholderText | `.placeholder-text` | — | 占位文字 |
| PlaceholderHint | `.placeholder-hint` | — | 占位提示 |
| AudioIndicator | `.audio-indicator` | listening/speaking/thinking/loading | 呼吸灯 + 文字标签 |
| IndicatorRing | `.indicator-ring` | — | 彩色脉冲环 |
| IndicatorLabel | `.indicator-label` | — | 状态文字 |
| ConnectionStatus | `.connection-status` | connected/connecting/disconnected | 绿点✓ + 延迟 / 黄点旋转 / 红点 + 重连计数 |
| StatusDot | `.status-dot` | — | 彩色圆点 |
| StatusLabel | `.status-label` | — | 连接状态文字 |
| Latency | `.latency-indicator` | good/ok/bad | 延迟毫秒数（绿/黄/红色） |
| Stats | `.stats` | — | 帧数/音频统计 |
| StatusSeparator | `.status-separator` | — | 状态栏分隔符 |

### 对话组件

| 组件 | CSS 类 | 状态 | 说明 |
|------|--------|------|------|
| ChatLog | `.chat-log` | 空/有消息 | 居中提示 / 自动滚动消息列表 |
| ChatEmpty | `.chat-empty` | — | 空状态提示 |
| ChatMessage | `.chat-message` | user/assistant | 单条消息容器 |
| ChatBubble (User) | `.chat-bubble--user` | 转录完成 | 绿色气泡右对齐，hover 显示时间 |
| ChatBubble (AI) | `.chat-bubble--ai` | 流式/完成 | 暗色气泡左对齐 + 呼吸光标 |
| AI Status | `.chat-ai-status` | — | AI 状态指示文字 |
| Error Msg | `.chat-error-msg` | — | 错误消息提示 |

### 面试组件

| 组件 | CSS 类 | 状态 | 说明 |
|------|--------|------|------|
| DocumentUpload | `.document-upload` | — | 双区玻璃面板容器 |
| Upload Zone | `.document-upload__zone` | idle/uploading/parsing/done/error | 单区上传面板（JD/简历各一） |
| Zone Header | `.document-upload__zone-header` | — | 区标题（📄 上传JD / 👤 上传简历） |
| Zone Status | `.document-upload__zone-status` | `--done` / `--error` / `--uploading` / `--parsing` | 上传状态标识 |
| Drop Area | `.document-upload__drop-area` | — | 拖拽区（虚线边框） |
| Hint | `.document-upload__hint` | — | 拖拽提示文字 |
| Filename | `.document-upload__filename` | — | 已上传文件名 |
| Error | `.document-upload__error` | — | 上传错误提示 |
| QuestionBank | `.qbank` | — | 下拉题库容器 |
| Trigger | `.qbank__trigger` | — | 胶囊触发按钮 "📋 面试题库 · N 题 ▾" |
| Stats | `.qbank__trigger-stats` | — | 题目数量徽章 |
| Arrow | `.qbank__arrow` | `--open` | 展开箭头 |
| Menu | `.qbank__menu` | — | 下拉弹窗（340px, max-height 360px, z-overlay） |
| Category | `.qbank__cat` | — | 分类容器 |
| Cat Header | `.qbank__cat-header` | — | 分类标题按钮（手风琴） |
| Cat Label | `.qbank__cat-label` | — | 分类名 + icon |
| Cat Count | `.qbank__cat-count` | — | 分类题目数 |
| Chevron | `.qbank__chevron` | `--open` | 分类折叠箭头 |
| Questions | `.qbank__questions` | — | 题目列表 |
| Card | `.qbank__card` | — | 单题卡片 |
| Text | `.qbank__text` | — | 题目文本 |
| Meta | `.qbank__meta` | — | 难度 + 参考技能 |
| Difficulty | `.qbank__diff` | `--easy` / `--medium` / `--hard` | 难度标签（绿/黄/红） |
| Reference | `.qbank__ref` | — | 参考技能标签 |
| RadarChart | `.radar-chart` | — | Canvas 五维雷达图（display: block） |
| ReportViewer | `.report-viewer` | `--loading` / `--expanded` | 面试报告卡片 |
| Header | `.report-viewer__header` | — | 折叠状态标题栏 |
| Title | `.report-viewer__title` | — | "📊 面试评估报告 · 75 分" |
| Badge | `.report-viewer__badge` | — | 录用建议徽章（绿/黄/红色） |
| Chevron | `.report-viewer__chevron` | `--open` | 展开折叠箭头 |
| Body | `.report-viewer__body` | — | 展开详情区 |
| Radar | `.report-viewer__radar` | — | 雷达图容器 |
| Details | `.report-viewer__details` | — | 评分详情区 |
| Score Item | `.report-viewer__score-item` | — | 单条评分行 |
| Score Bar | `.report-viewer__score-bar-track` / `--fill` | — | 评分条形图 |
| Lists | `.report-viewer__lists` | — | 强弱项双栏容器 |
| List | `.report-viewer__list` | `--strength` / `--weakness` | 优势 / 待改进列表 |
| Skeleton | `.report-viewer__skeleton` | — | 加载骨架屏脉冲条 |
| Spinner | `.report-viewer__spinner` | — | 加载旋转等待 |

### 控制组件

| 组件 | CSS 类 | 状态 | 说明 |
|------|--------|------|------|
| ControlBar | `.control-bar` | — | 底部控制栏 |
| Start Group | `.control-bar__start-group` | — | Start 按钮 + 提示包装 |
| Hint | `.control-bar__hint` | — | Contextual hint（琥珀色文字） |
| AgentSelector | `.agent-selector` | — | Agent 选择下拉容器 |
| Trigger | `.agent-selector__trigger` | — | 当前选中 Agent 显示 |
| Current | `.agent-selector__current` | — | Agent 名称 + 描述 |
| Arrow | `.agent-selector__arrow` | `--open` | 展开箭头 |
| Menu | `.agent-selector__menu` | — | 下拉选项菜单 |
| Option | `.agent-selector__option` | `--active` | Agent 选项行 |
| Option Name | `.agent-selector__option-name` | — | Agent 名称 |
| Option Desc | `.agent-selector__option-desc` | — | Agent 描述 |

### 玻璃态按钮（GlassButton）

| 变体 | CSS 类 | 用途 |
|------|--------|------|
| 默认 | `.glass-btn` | 通用玻璃按钮 |
| 主色调 | `.glass-btn--primary` | 绿色强调（Start） |
| 危险色调 | `.glass-btn--danger` | 红色强调（Stop） |
| 已激活 | `.glass-btn--active` | 绿色边框（toggled on） |
| 包装 | `.glass-btn-wrapper` | 按钮外围霜边效果容器 |

| 状态 | 效果 |
|------|------|
| normal | 半透明底 + 细边框 + 微光晕 |
| hover | 增亮底 + 加粗边框 + 强光晕 |
| active | scale(0.97) |
| focus-visible | 蓝色 2px outline |
| disabled | opacity 0.4 |

### 其他组件

| 组件 | CSS 类 | 说明 |
|------|--------|------|
| NeuralBackground | — | Canvas 流场粒子背景（全屏） |
| ErrorBoundary | `.error-boundary` | 全局错误边界 |
| ErrorDetail | `.error-boundary-detail` | 错误详情面板 |
| MediaError | `.media-error` | 摄像头/麦克风权限错误 |
| VADError | `.vad-error` | VAD 加载失败错误 |

---

## 文件结构

```
frontend/src/
├── styles/
│   └── tokens.css                 # 设计 token 定义（所有 CSS 变量）
├── App.css                        # 全局样式（引用 tokens.css 变量）
├── App.tsx                        # 根组件
├── main.tsx                       # 入口（导入 tokens.css → App.css）
├── types/
│   ├── index.ts                   # TypeScript 共享类型定义
│   └── __tests__/
│       └── messages.test.ts       # WS 消息协议测试
├── hooks/
│   ├── useWebSocket.ts            # WS 连接 + 消息收发
│   ├── useMediaStream.ts          # 摄像头/麦克风采集
│   ├── useVAD.ts                  # 浏览器端 VAD
│   ├── useAudioPlayer.ts          # PCM16 播放
│   ├── useFrameCapture.ts         # 视频帧捕获 + 清帧信号
│   └── useAgent.ts                # Agent 列表 + 选中状态
└── components/
    ├── AgentSelector.tsx          # Agent 选择器（下拉菜单）
    ├── VideoPanel.tsx             # 视频面板
    ├── AudioIndicator.tsx         # 语音活动指示器
    ├── ConnectionStatus.tsx       # WebSocket 连接状态
    ├── ControlBar.tsx             # 控制按钮栏 + contextual hint
    ├── ChatLog.tsx                # 对话日志
    ├── GlassButton.tsx            # 玻璃态按钮（5 态齐全）
    ├── NeuralBackground.tsx       # Canvas 流场粒子背景
    ├── DocumentUpload.tsx         # 双区拖拽文档上传
    ├── QuestionBank.tsx           # 下拉分类题库
    ├── RadarChart.tsx             # Canvas 五维雷达图
    ├── ReportViewer.tsx           # 折叠面试报告卡片 + 骨架屏
    └── ErrorBoundary.tsx          # 全局错误边界
```

---

## 如何修改主题

1. 修改 `frontend/src/styles/tokens.css` 中的 `--color-*` 变量
2. 所有组件自动继承新颜色，无需逐个修改
3. 如需添加新颜色 token，先确认是否可归类到现有语义色
4. 新增 token 命名遵循 `--color-{category}-{variant}` 模式

## 如何添加新组件

1. 组件的所有视觉属性必须使用 `var(--*)` 引用
2. 使用 `--space-*` token 定义间距
3. 使用 `--text-*` token 定义字号
4. 使用 `--radius-*` token 定义圆角
5. 交互状态：hover / active / focus-visible / disabled 必须全部定义
6. 动画须包裹在 `@media (prefers-reduced-motion: no-preference)` 中
7. CSS 类命名：BEM 风格（`block__element--modifier`），与现有组件保持一致

---

## 无障碍清单

- [x] 所有交互元素有 `aria-label`
- [x] 动态内容区域有 `aria-live` 或 `role="log"`
- [x] `:focus-visible` 样式在所有按钮上可见
- [x] `prefers-reduced-motion: reduce` 关闭所有动画和过渡
- [x] Tab 键盘导航可遍历所有控件
- [x] 颜色不是传达信息的唯一方式（配合文本标签）
- [x] 语义化 HTML（button 而非 div+onClick）
