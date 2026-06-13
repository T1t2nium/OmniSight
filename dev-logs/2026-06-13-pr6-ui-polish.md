# 2026-06-13: PR 6 — 前端 UI 美化：设计系统 + 呼吸灯光环境

**分支**: phase/6-ui-polish
**PR**: #5 (GitHub)
**提交**: 5 commits (e3b3064 → 1489d7f)
**文件变更**: 14 files, ~5200 lines

## 完成事项

### Wave 1 — 设计系统基础
- [x] 安装 SKILL：Frontend Design Toolkit + Refactoring UI Plugin
- [x] 创建 CSS 设计 token 体系 (`tokens.css`)：颜色/间距/字体/圆角/阴影/过渡
- [x] App.css 全面迁移到 CSS 变量：零硬编码 hex 值
- [x] 字体统一：六级字号 scale，JetBrains Mono 等宽字体
- [x] 响应式布局：3 断点（768px 平板 / 480px 手机 / 600px 高度）
- [x] 无障碍基础：aria-label、role、aria-live、prefers-reduced-motion
- [x] 新建 docs/design-system.md — 完整设计系统文档

### Wave 2 — 视觉升级
- [x] 全新暖色暗调配色（柔化黑色 + 青蓝 accent + 渐变 token）
- [x] 头部渐变 ◈ Logo + 渐变色标题 + accent 底部发光线
- [x] 聊天气泡头像行布局（👤 用户 / ◈ AI）+ 柔和边框
- [x] 流式气泡蓝光边框
- [x] 视频面板圆角 18px + 阴影深度 + inner highlight
- [x] 空状态：💬 emoji + 标题 + 快捷键提示 chips
- [x] 胶囊形 UI：状态标签、按钮全 pill 形状
- [x] 按钮 hover 上浮效果 + 开始按钮绿色光晕
- [x] 延迟徽章带颜色编码背景（绿<50ms / 黄<200ms / 红>200ms）
- [x] 悬停时间戳（分隔线 + 淡入）

### Wave 3 — 背景呼吸灯光环境
- [x] 新建 `BackgroundAmbiance.tsx` 组件：状态感知呼吸灯光源
- [x] 大型柔光球体（120vw），置于页面中心顶部，blur 30px
- [x] 次级散射光（160vw），blur 50px，反相位呼吸
- [x] SVG fractalNoise 噪声纹理 3% 透明度（毛玻璃颗粒感）
- [x] 三种光色跟随对话状态切换：
  - 待机/聆听 → 柔和青蓝 (#7eb8ff)
  - 用户说话 → 温暖琥珀金 (#fbbf24)
  - AI 回答 → 柔和薰衣草紫 (#a78bfa)
- [x] 状态切换时 1.2s 平滑颜色过渡 + 短暂增亮脉冲
- [x] 双动画：主光 4s 呼吸 + 散射光 5s 反相位呼吸

### Wave 4 — 视频面板边框呼吸光
- [x] 视频面板 box-shadow 四层呼吸光晕（深度阴影 + 3 层发光）
- [x] 发光颜色跟随 `--ambiance-rgb` CSS 变量
- [x] 3.5s 呼吸周期：20/55/95px → 38/85/130px
- [x] 增强背景光强度：主光 opacity 0.18→0.28，散射光 0.06→0.12

### Wave 5 — 透明度修复
- [x] 状态栏背景透明度 0.8→0.25，呼吸光可穿透
- [x] 控制栏背景透明度 0.8→0.25
- [x] 移除状态栏/控制栏硬边框线，光线连续流动
- [x] 保留 backdrop-filter: blur(12px) 文字清晰可读

## 技术决策
- **CSS 变量而非 Tailwind**：已有 CSS 增量迁移，零新增依赖
- **暖色暗调**：从冷峻 GitHub Dark → 温暖蓝紫底调，适合长时间使用
- **box-shadow 直接发光而非 ::pseudo**：伪元素被 opaque 背景遮挡，box-shadow 渲染在元素外
- **CSS 变量驱动光色**：BackgroundAmbiance 组件通过 `document.documentElement.style.setProperty` 设置 `--ambiance-rgb`
- **SVG 噪声纹理**：比图片加载快，零网络请求，3% 透明度不会干扰内容

## 关键文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `frontend/src/styles/tokens.css` | 新建 | 完整 CSS 变量体系 + 渐变 token + 新颜色 |
| `frontend/src/App.css` | 重写 | 全部 var() 引用 + 呼吸光 + 气泡头像 + 响应式 |
| `frontend/src/components/BackgroundAmbiance.tsx` | 新建 | 状态感知呼吸灯光源组件 |
| `frontend/src/components/ChatLog.tsx` | 重写 | 头像气泡行布局 + 新空状态 |
| `frontend/src/components/VideoPanel.tsx` | 修改 | 摄像头图标 + 提示文字 + aria-label |
| `frontend/src/components/ConnectionStatus.tsx` | 修改 | ✓ + 延迟颜色梯度 + aria-live |
| `frontend/src/components/ControlBar.tsx` | 修改 | aria-label |
| `frontend/src/components/AudioIndicator.tsx` | 修改 | role="status" + aria-label |
| `frontend/src/App.tsx` | 修改 | Logo + 背景组件集成 + 氛围状态计算 |
| `frontend/src/main.tsx` | 修改 | 导入 tokens.css |
| `docs/design-system.md` | 新建 | 完整设计系统文档 |
| `.claude/skills/frontend-design-toolkit/` | 新增 | 前端设计工具集 SKILL |
| `.claude/skills/refactoring-ui-plugin/` | 新增 | UI 优化技能 |

## 视觉特性

| 特性 | 说明 |
|------|------|
| 背景呼吸光 | 大柔光球体 + 散射光，对话状态变色 |
| 视频边框光 | 四层 box-shadow 呼吸，与背景光同色 |
| 毛玻璃面板 | backdrop-filter blur + 25% 透明度 |
| 头像气泡 | 用户/AI 消息各带圆形头像 |
| 渐变标题 | 青蓝→紫渐变文字 |
| 胶囊 UI | 状态标签、按钮全 pill 形状 |
| 光晕按钮 | hover 上浮，开始按钮绿色发光 |

## 验证结果
- ✅ `npx tsc --noEmit` 零错误
- ✅ `npm run build` 构建成功
- ✅ `uv run python -c "from app.main import app"` 导入成功
- ✅ `uv run pytest tests/ -v` 31/31 全绿
- ✅ 无功能回归（纯 CSS + 视觉组件变更）

## 提交历史

```
1489d7f fix: Make status bar and control bar translucent
8cb92b4 fix: Move video border glow from hidden ::before to visible box-shadow
4eefb8e feat: PR 6 wave 4 — Stronger ambient light + video panel breathing border
7949bc2 feat: PR 6 wave 3 — Ambient breathing light background
fe6e211 feat: PR 6 wave 2 — Visible UI upgrade with warmer design
e3b3064 feat: PR 6 — Frontend UI beautification with design system foundation
```

## 下一步
- 如有需要可继续微调光强/颜色
- 长期按 docs/design-system.md 规范迭代
