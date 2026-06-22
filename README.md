# 📦 到期提醒工具

> 基于 Tkinter 的跨平台桌面应用，用于分析 Excel 订单数据、追踪产品到期状态、管理送货记录，支持钉钉/企业微信机器人定时推送。

## ✨ 功能

- 📊 **到期分析** — 加载 Excel，自动识别日期列，按客户/产品聚合分析到期状态（已过期 / 今天 / 3天内 / 7天内）
- 🚚 **送货记录** — 一键送货，追踪历史送货记录，导出送货清单
- 📋 **历史快照** — 自动保存分析快照，支持对比、恢复、清理
- 🤖 **机器人通知** — 配置钉钉/企业微信 Webhook，定时推送到期提醒
- 🔗 **机器人同步** — Webhook 配置 + 消息预览 + 定时推送（越临近越靠前）
- 🎨 **暗黑模式** — 支持浅色/深色主题切换
- 🌍 **跨平台** — 支持 Windows / macOS / Linux

## 📸 截图

<img width="1922" height="1308" alt="image" src="https://github.com/user-attachments/assets/e7d153ba-8465-477d-82dd-996faac9fbd1" />

## 🏗 项目结构

```
expiry/
├── expiry_reminder.py              # 入口
├── modules/                         # 核心模块
│   ├── config.py                    # 配置常量、色板、列映射
│   ├── utils.py                     # 日期解析、通知、调试日志
│   ├── widgets.py                   # FlatButton 圆角按钮控件
│   ├── analysis_panel.py            # 到期分析、Treeview 渲染
│   ├── history_panel.py             # 历史快照管理
│   ├── notify_panel.py              # 机器人通知配置
│   ├── robot_sync.py                # 机器人同步面板
│   └── file_ops.py                  # Excel 读写、送货、导出
├── assets/
│   └── icon.ico                     # 应用图标
├── .github/workflows/
│   └── build.yml                    # CI/CD 自动构建 + Release
├── build.bat                        # Windows 本地打包脚本
└── .gitignore
```

## 🚀 快速开始

### 运行

```bash
# 安装依赖
pip install openpyxl xlrd

# 启动
python expiry_reminder.py
```

### 打包

```bash
# Windows（运行 build.bat）
build.bat

# 手动打包
pip install pyinstaller Pillow
pyinstaller --name expiry-reminder --windowed --onefile \
  --icon=assets/icon.ico \
  --add-data "assets:assets" \
  --hidden-import modules \
  expiry_reminder.py
```

## 📥 下载

预编译版本请前往 [Releases](https://github.com/tangjin2580/expiry/releases) 页面下载对应平台版本：

| 平台 | 文件 |
|------|------|
| 🪟 Windows | `expiry-reminder-windows.exe` |
| 🍎 macOS | `expiry-reminder-macos` |
| 🐧 Linux | `expiry-reminder-linux` |

## 🔧 功能说明

### 机器人通知

1. 切换到**高级模式**（点击右上角「高级」按钮）
2. 进入「机器人通知」标签页
3. 填入钉钉 / 企业微信 Webhook 地址
4. 设置提醒间隔和提前天数 → 开启定时提醒

### 机器人同步

1. 进入「机器人同步」标签页
2. 填写 Webhook 地址，点击「🔔 测试」验证连通性
3. 配置推送间隔和提前天数
4. 点击「▶ 开启定时推送」启动自动推送

**推送格式：**
```
📦 发货提醒 (2026-06-11 14:30)
共 5 条待处理：

1. [🔴已过期] 张三公司 | 2026-06-10 | 苹果 x100
2. [🟠今天] 李四超市 | 2026-06-11 | 香蕉 x50
3. [🟡明天] 王五商店 | 2026-06-12 | 橙子 x80
```

## 🛠 技术栈

- **语言**: Python 3.9+
- **GUI**: Tkinter (ttk)
- **Excel**: openpyxl / xlrd
- **打包**: PyInstaller
- **CI/CD**: GitHub Actions（跨平台矩阵构建 + 自动 Release）

## 📄 License

MIT

---

*Built by [tangjin2580](https://github.com/tangjin2580)*

