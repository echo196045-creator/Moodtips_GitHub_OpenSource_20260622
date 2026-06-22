# Moodtips GitHub Desktop 发布指南

本指南用于把桌面上的开源整理版发布到 GitHub。

## 1. 本地文件夹

请选择这个文件夹作为 GitHub 仓库：

```text
C:\Users\Echo2\Desktop\Moodtips_GitHub_OpenSource_20260622
```

不要选择旧版恢复目录、课程报告目录或压缩包目录。

## 2. 当前状态说明

这个文件夹已经保留 `.git` 和远程地址：

```text
https://github.com/echo196045-creator/Moodtips_GitHub_OpenSource_20260622.git
```

如果 GitHub Desktop 左侧显示很多 changed files，这是正常的：说明刚恢复的文件还没有提交。

## 3. 首次提交

1. 打开 GitHub Desktop。
2. 选中 `Moodtips_GitHub_OpenSource_20260622`。
3. 左下角 Summary 填写：

```text
Initial open-source release
```

4. Description 可填写：

```text
Add Moodtips FastAPI app, SQLite demo database, frontend assets, and local run guide.
```

5. 点击 `Commit to main`。

## 4. 推送到 GitHub

提交后，右上角一般会变成 `Publish repository` 或 `Push origin`：

- 如果是 `Publish repository`：点击它，取消勾选 `Keep this code private`，再发布。
- 如果是 `Push origin`：点击它，把刚才的提交推送到已有 GitHub 仓库。

## 5. 改成公开仓库

如果仓库旁边有锁，说明它还是私有仓库。进入 GitHub 网页端仓库：

1. 打开 `Settings`。
2. 进入 `General`。
3. 拉到最下面 `Danger Zone`。
4. 点击 `Change repository visibility`。
5. 改成 `Public`。

## 6. 添加线上演示链接

发布后进入 GitHub 网页版仓库，在右侧 About 区域点击设置图标，把 Website 填为：

```text
https://moodtips.oppenchow.online/app/
```

Description 可填写：

```text
Mood-based drink recommendation system built with FastAPI, SQLite, and a lightweight web frontend.
```

## 7. 同学下载后如何运行

同学下载 ZIP 或 clone 仓库后：

1. 进入项目根目录。
2. 双击 `start_moodtips.bat`。
3. 等待依赖安装完成。
4. 打开脚本显示的 `/app/` 地址。

如果页面能打开但没有推荐，通常是没有连到后端，请让同学访问同端口 `/health`，能看到 `{"status":"ok"}` 才说明服务正常。

## 8. 发布前检查

发布前建议确认：

- 本地能打开 `/app/`。
- `/health` 返回正常。
- 至少做一次推荐，确认不是空结果。
- GitHub Desktop 文件列表中没有 `__pycache__`、`.pyc`、旧压缩包、课程报告或临时文件。
- 没有单个文件超过 GitHub 的 100MB 限制。
