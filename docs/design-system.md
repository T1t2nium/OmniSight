# OmniSight 设计系统

> PR 6 建立的设计 token 体系和 UI 规范。后续 UI 开发和迭代必须遵循本文档。

---

## 设计原则

1. **暗色优先**：基于 GitHub Dark 主题，深色背景减轻长时间使用的眼疲劳
2. **分层清晰**：背景三层（primary/secondary/tertiary），文本三级（primary/secondary/muted）
3. **统一间距**：4px 基准 scale，所有组件遵守同一间距体系
4. **动画克制**：微交互 ≤300ms，尊重 reduced-motion 偏好
5. **渐进增强**：CSS 变量 → 组件样式 → 响应式 → 无障碍

---

## 颜色体系

所有颜色通过 CSS 变量引用，位于 `frontend/src/styles/tokens.css`。

### 背景色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-bg-primary` | `#0f1117` | 页面底色 |
| `--color-bg-secondary` | `#161b22` | 面板/卡片背景 |
| `--color-bg-tertiary` | `#21262d` | 按钮/输入框背景 |
| `--color-bg-hover` | `#30363d` | 悬停态背景 |

### 文字色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-text-primary` | `#e1e4e8` | 正文/标题 |
| `--color-text-secondary` | `#8b949e` | 副文本/标签 |
| `--color-text-muted` | `#484f58` | 禁用/占位 |

### 语义色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-accent` | `#58a6ff` | 强调/链接/蓝色 |
| `--color-success` | `#2ea043` | 成功/就绪/绿色 |
| `--color-error` | `#da3633` | 错误/录音中/红色 |
| `--color-error-fg` | `#ffa198` | 错误消息前景色 |
| `--color-warning` | `#d29922` | 警告/重连中/黄色 |

### 组件专用色

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-btn-start-bg` | `#238636` | 开始按钮背景 |
| `--color-btn-start-border` | `#2ea043` | 开始按钮边框 |
| `--color-btn-stop-bg` | `#da3633` | 停止按钮背景 |
| `--color-btn-stop-border` | `#f85149` | 停止按钮边框 |
| `--color-bubble-user-bg` | `#1e6b3e` | 用户气泡背景 |
| `--color-bubble-ai-bg` | `#1c2333` | AI 气泡背景 |
| `--color-bubble-error-bg` | `#3d1a1a` | 错误气泡背景 |

---

## 间距体系

基于 4px 基准的 6 级 scale。

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `--space-1` | `4px` | 紧凑内边距、标签间距 |
| `--space-2` | `8px` | 内边距、图标间距 |
| `--space-3` | `12px` | 标准内边距、组件间 gap |
| `--space-4` | `16px` | 宽松内边距、区块间距 |
| `--space-6` | `24px` | 大间距 |
| `--space-8` | `32px` | 最大间距 |

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
| `--text-lg` | `0.9rem` | 聊天气泡正文 |
| `--text-xl` | `1.1rem` | 中等标题 |
| `--text-2xl` | `1.25rem` | 应用标题 |

---

## 圆角体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--radius-sm` | `4px` | 气泡方向角、标签 |
| `--radius-md` | `6px` | 按钮、输入框、消息卡片 |
| `--radius-lg` | `8px` | 错误框 |
| `--radius-xl` | `12px` | 聊天气泡 |
| `--radius-full` | `9999px` | 圆形元素（指示灯） |

---

## 阴影体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | 轻微浮起 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | 明显浮起 |
| `--shadow-glow-green` | `0 0 8px var(--color-success)` | 绿色呼吸灯 |
| `--shadow-glow-red` | `0 0 8px var(--color-error)` | 红色呼吸灯 |
| `--shadow-glow-blue` | `0 0 8px var(--color-accent)` | 蓝色呼吸灯 |
| `--shadow-inner` | `inset 0 2px 4px rgba(0,0,0,0.3)` | 内凹深度（视频面板） |

---

## 过渡体系

| Token | 值 | 用途 |
|-------|-----|---------|
| `--transition-fast` | `0.15s ease` | hover、切换 |
| `--transition-normal` | `0.2s ease` | 连接状态变化 |
| `--transition-slow` | `0.3s ease` | 消息入场动画 |

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
| 头部 | `.app-header` | 标题 + 副标题 |
| 主区域 | `.app-main` | flex column, flex:1 |
| 顶部区域 | `.layout-top` | 视频面板 |
| 状态栏 | `.layout-status` | VAD + 统计 + 连接状态 |
| 聊天区域 | `.layout-chat` | 消息列表，可滚动 |
| 底部栏 | `.layout-bottom` | 控制按钮 |

### 功能组件

| 组件 | 状态 | 视觉效果 |
|------|------|---------|
| VideoPanel | 开启/关闭 | 16:9 实时镜像预览 / 摄像头图标 + "Camera Off" |
| AudioIndicator | 收听/说话/AI说话/VAD加载 | 绿圈呼吸/红圈快速脉冲/蓝圈脉冲/绿圈静态 |
| ConnectionStatus | 已连接/连接中/断开 | 绿点✓ + 延迟 / 黄点旋转 / 红点 + 重连计数 |
| ChatLog | 空/有消息 | 居中提示 / 自动滚动消息列表 |
| ChatBubble(User) | 转录完成 | 绿色渐变右对齐，hover 显示时间 |
| ChatBubble(AI) | 流式/完成 | 暗色左对齐 + 呼吸光标 / 完成态光标消失 |
| DocumentUpload | idle/uploading/parsed/error | 双区玻璃面板，虚线边框拖拽区，绿色勾/红色叉状态 |
| QuestionBank | 关闭/展开菜单/分类折叠 | 胶囊触发器 → 弹窗菜单，分类手风琴折叠，难度彩色标签 |
| RadarChart | Canvas 5 边形 | 五层同心网格，半透明填充，数据点圆点，维度标签 |
| ReportViewer | 加载中/折叠/展开 | 骨架屏（旋转等待 + 脉冲条）→ 折叠卡片 → 展开雷达图 + 评分条 |
| AgentSelector | 展开/收起/disabled | 下拉菜单弹窗，Agent 名称 + 描述，选中高亮，对话中禁用 |

### 交互元素

| 元素 | 正常 | hover | active | focus-visible | disabled |
|------|------|-------|--------|---------------|----------|
| .btn-start | 绿底白字 + 光晕 | 亮绿底 + 强光晕 | scale(0.97) | 蓝色 2px outline | - |
| .btn-stop | 红底白字 | 亮红底 | scale(0.97) | 蓝色 2px outline | - |
| .btn-active | 绿边绿字 | 绿底 | scale(0.97) | 蓝色 2px outline | - |
| .btn-inactive | 灰边灰字 | 灰底 | scale(0.97) | 蓝色 2px outline | opacity 0.4 |
| .btn (default) | 暗底白字 | 亮底 | scale(0.97) | 蓝色 2px outline | opacity 0.4 |

---

## 无障碍清单

- [x] 所有交互元素有 `aria-label`
- [x] 动态内容区域有 `aria-live` 或 `role="log"`
- [x] `:focus-visible` 样式在所有按钮上可见
- [x] `prefers-reduced-motion: reduce` 关闭所有动画和过渡
- [x] Tab 键盘导航可遍历所有控件
- [x] 颜色不是传达信息的唯一方式（配合文本标签）
- [x] 语义化 HTML（button 而非 div+onClick）

---

## 文件结构

```
frontend/src/
├── styles/
│   └── tokens.css              # 设计 token 定义（所有 CSS 变量）
├── App.css                     # 全局样式（引用 tokens.css 变量）
├── App.tsx                     # 根组件
├── main.tsx                    # 入口（导入 tokens.css → App.css）
├── types/
│   └── index.ts                # TypeScript 共享类型定义
├── hooks/
│   ├── useWebSocket.ts         # WS 连接 + 消息收发
│   ├── useMediaStream.ts       # 摄像头/麦克风采集
│   ├── useVAD.ts               # 浏览器端 VAD
│   ├── useAudioPlayer.ts       # PCM16 播放
│   ├── useFrameCapture.ts      # 视频帧捕获
│   └── useAgent.ts             # Agent 列表 + 选中状态
└── components/
    ├── AgentSelector.tsx       # Agent 选择器（下拉菜单）
    ├── VideoPanel.tsx          # 视频面板
    ├── AudioIndicator.tsx      # 语音活动指示器
    ├── ConnectionStatus.tsx    # WebSocket 连接状态
    ├── ControlBar.tsx          # 控制按钮栏
    ├── ChatLog.tsx             # 对话日志
    ├── GlassButton.tsx         # 玻璃态按钮
    ├── NeuralBackground.tsx    # Canvas 流场粒子背景
    ├── DocumentUpload.tsx      # 双区拖拽文档上传
    ├── QuestionBank.tsx        # 下拉分类题库
    ├── RadarChart.tsx          # Canvas 五维雷达图
    ├── ReportViewer.tsx        # 折叠面试报告卡片
    └── ErrorBoundary.tsx       # 全局错误边界
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
5. 交互状态：hover/active/focus-visible/disabled 必须全部定义
6. 动画须包裹在 `@media (prefers-reduced-motion: no-preference)` 中
