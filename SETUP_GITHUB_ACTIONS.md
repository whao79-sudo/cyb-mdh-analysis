# 🚀 GitHub Actions 配置指南

## 手动创建 Workflow

你的 GitHub Token 当前没有 `workflow` 权限，无法通过 API 自动创建。
请在 GitHub UI 中手动创建：

### 方法一：直接在 UI 创建

1. 进入仓库：https://github.com/whao79-sudo/cyb-mdh-analysis
2. 点击 **Actions** 标签
3. 点击 **"set up a workflow yourself"**
4. 将 `daily-analysis.yml.txt` 文件的内容复制进去
5. 点击 **"Start commit"** → **"Commit new file"**

### 方法二：创建有 workflow 权限的 Token

1. 访问 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 勾选 `workflow` scope
4. 生成后运行：

```bash
openclaw configure --set git.token=YOUR_NEW_TOKEN
```

然后 @我重新推送 workflow 文件即可。

## 手动触发首次运行

配置完成后，进入 **Actions** → **CYB MDH Daily Analysis** → **Run workflow**

数据将自动从 baostock 下载并分析。
