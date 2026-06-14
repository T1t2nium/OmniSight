# 2026-06-14: PR 9 — 前端背景与按钮 UI 终极优化

**分支**: phase/9-frontend-ui-final
**PR**: #9
**文件变更**: 9 files changed (+549 / -273)

## 完成事项
- [x] **Canvas 流场粒子背景**：替换 CSS 呼吸灯光环为全屏 Canvas 粒子系统
  - 600 个粒子沿流场（cos/sin 角度场）运动
  - 鼠标 150px 半径排斥交互
  - 拖尾效果（半透明背景色覆层替代 clearRect）
  - Retina 高清屏支持（devicePixelRatio 适配）
  - `prefers-reduced-motion` 回退为静态散点
  - 颜色随对话状态切换（idle=indigo, 用户说话=amber, AI 回复=purple）
- [x] **玻璃态按钮 GlassButton**：替换原有 3 个扁平按钮
  - 磨砂玻璃基底（`backdrop-filter: blur(14px)` + 半透明背景）
  - 渐变边缘光环（`::before` mask-composite 技巧）
  - 3 种 Variant：primary（绿）/ danger（红）/ default（中性）
  - Active 切换态：绿色边框高亮
  - 悬停上浮、按压缩放、禁用灰显
- [x] 删除 `BackgroundAmbiance.tsx`（旧呼吸灯组件）
- [x] 新增 11 个 `--color-glass-*` 设计令牌
- [x] 响应式断点适配玻璃按钮（768px / 480px）
- [x] 视觉关键词过滤修复：新增动作动词（做/干/举/挥/指/动）
- [x] 禁用视觉过滤，改由用户提示词控制
- [x] TTS 括号表情过滤：移除（微笑）（笑）（点头）等文本

## 技术决策
- **零新增依赖**：纯 Canvas API + CSS，不引入 Three.js / cva / Tailwind
- **CSS 变量驱动拖尾颜色**：Canvas 读取 `--color-bg-primary` 适配主题色
- **mask-composite 渐变边框**：wrapper `::before` 画 1px 顶部亮光边缘，`@supports` 回退
- **视觉过滤交由用户控制**：移除 `_is_visual_question()` 调用，始终传递摄像头帧

## 遇到的问题
- **"我在做什么动作" 被误判为非视觉问题**：正则动词列表缺少动作动词 → 新增 做/干/举/挥/指/动
- **AI 回复带 (微笑) 表情标记导致 TTS 别扭**：`_TTS_REPLACEMENTS` 新增中文括号内短内容过滤

## 下一步
- 版本号升级至 v0.6.0
- Demo 视频录制完成
