# HidenCloud Auto Renew (Python版)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

基于 Python 编写的 HidenCloud (海敦云) 自动续期与支付脚本，专为 GitHub Actions 设计。

✨ **核心亮点：使用 Infinicloud (WebDAV) 同步 Cookie，无需 Git 提交权限，支持将仓库设置为 Public (公开)，保障账号安全。**

## 🚀 功能特性

- **自动续期**：自动检测服务并延长 10 天有效期。
- **自动支付**：续期后自动识别账单并完成 0 元支付（或余额支付）。
- **Cookie 持久化**：
  - 自动将最新 Cookie 上传至 Infinicloud (WebDAV)。
  - 脚本运行时优先读取云端缓存，防止 Cookie 过期。
  - **安全优势**：敏感数据不存储在 GitHub 仓库文件中，仓库可公开。
- **消息推送**：集成 WxPusher，任务完成后通过微信即时通知。
- **多账号支持**：支持配置多个账号，批量管理。
- **失败重试**：网络波动或 Cookie 失效时自动回退重试。

## 🛠️ 部署指南

### 1. 准备工作

*   **GitHub 账号**：用于 Fork 本项目。
*   **HidenCloud 账号**：获取初始 Cookie。
*   **Infinicloud 账号**：[注册地址](https://infinicloud.com/)，用于存储 Cookie JSON 文件。
*   **WxPusher**：[注册地址](https://wxpusher.zjiecode.com/admin/)，用于接收通知。

### 2. 获取配置信息

#### A. 获取 HidenCloud Cookie
1. 浏览器打开 HidenCloud 控制台并登录。
2. 按 `F12` 打开开发者工具，点击 **网络(Network)** 标签。
3. 刷新页面，点击第一个请求（通常是 dashboard），在 **请求头(Request Headers)** 中找到 `Cookie`。
4. 复制整个 Cookie 字符串。

#### B. 获取 Infinicloud WebDAV 信息
1. 登录 Infinicloud，进入 **My Page**。
2. 开启 **Apps Connection**。
3. 记录以下信息：
   - **WebDAV URL**: (例如 `https://sv10.infinicloud.com/dav/`)
   - **Connection ID**: (作为用户名)
   - **Apps Password**: (作为密码)

#### C. 获取 WxPusher 信息
1. 创建一个新的应用，获取 `APP_TOKEN`。
2. 扫码关注应用，在“我的”->“用户UID”中获取 `UID`。

### 3. 配置 GitHub Secrets

在你的 GitHub 仓库中，点击 **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**，添加以下变量：

| 变量名 (Name) | 是否必填 | 说明 |
| :--- | :---: | :--- |
| **HIDEN_COOKIE** | ✅ | 初始 Cookie。多账号请用换行或 `&` 分隔 |
| **WP_APP_TOKEN_ONE** | ✅ | WxPusher 应用 Token |
| **WP_UIDs** | ✅ | WxPusher 用户 UID (多人用分号分隔) |
| **WEBDAV_URL** | ✅ | Infinicloud WebDAV 地址 (末尾带 `/`) |
| **WEBDAV_USER** | ✅ | Infinicloud Connection ID |
| **WEBDAV_PASS** | ✅ | Infinicloud Apps Password |

### 4. 启动运行

1. 点击仓库上方的 **Actions** 标签。
2. 在左侧选择 **HidenCloud Auto Renew (Python)**。
3. 点击右侧的 **Run workflow** 手动触发一次测试。
4. 检查 Infinicloud 中是否生成了 `hiden_cookies.json` 文件，并查收微信推送。

之后脚本将按照配置的时间（默认为北京时间每天上午 10:00）自动运行。

## 📂 文件结构

```text
.
├── .github/workflows/
│   └── main.yml        # GitHub Actions 配置文件
├── main.py             # Python 核心运行脚本
├── requirements.txt    # Python 依赖库
└── README.md           # 说明文档
```

## ⚠️ 免责声明

1. 本项目仅供学习交流使用，请勿用于非法用途。
2. 脚本涉及账号操作，作者不对因使用本脚本造成的账号封禁、资金损失等后果负责。
3. 请妥善保管你的 Secrets 配置，不要分享给他人。
4. 虽然使用了 WebDAV 分离敏感数据，但建议定期修改密码和检查 Cookie 状态。

---
**如果这个项目对你有帮助，请给一个 Star ⭐️**
```
