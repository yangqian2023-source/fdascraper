# FDA Drug Approval Reports 采集

使用 GitHub Actions 自动采集 FDA 药物审批数据。

## 文件结构

```
.
├── .github/
│   └── workflows/
│       └── scrape.yml      # GitHub Actions 配置
├── data/                   # 采集数据（自动生成）
├── scraper.py              # 采集脚本
├── requirements.txt        # Python 依赖
└── README.md              # 说明文档
```

## 使用方法

### 1. 创建 GitHub 仓库

1. 登录 GitHub：https://github.com
2. 点击 "New repository"
3. 仓库名：`fda-scraper`（或其他）
4. 设为 **Private**（私有）
5. 点击 "Create repository"

### 2. 上传文件

**方法 A：网页上传**
1. 在仓库页面点击 "uploading an existing file"
2. 上传以下文件：
   - `scraper.py`
   - `requirements.txt`
   - `.github/workflows/scrape.yml`
3. 点击 "Commit changes"

**方法 B：Git 命令行**
```bash
# 初始化仓库
git init
git add .
git commit -m "Initial commit"

# 关联远程仓库
git remote add origin https://github.com/你的用户名/fda-scraper.git
git branch -M main
git push -u origin main
```

### 3. 手动测试运行

1. 进入仓库页面
2. 点击 "Actions" 标签
3. 左侧选择 "FDA Scraper"
4. 点击 "Run workflow" → "Run workflow"
5. 等待 2-3 分钟，查看运行结果

### 4. 查看采集数据

**方法 A：网页查看**
1. 进入 "Actions" → 点击某次运行
2. 在 "Artifacts" 区域下载数据文件

**方法 B：仓库文件**
1. 进入仓库的 `data/` 目录
2. 查看 `fda_YYYY-MM-DD.json` 和 `fda_YYYY-MM-DD.tsv`

### 5. 同步数据到你的服务器

采集完成后，需要手动或自动将数据同步到你的服务器。

**手动下载：**
```bash
# 在你的服务器上
cd /root/regulatoryInspection/data/fda/
# 从 GitHub 下载数据文件
```

**自动同步（后续实现）：**
- 修改 `scraper.py`，采集后 POST 到你的服务器 API
- 或设置服务器定时从 GitHub 拉取

## 定时运行

GitHub Actions 配置已设置每天北京时间 06:00 自动运行。

如需修改时间，编辑 `.github/workflows/scrape.yml`：
```yaml
on:
  schedule:
    # UTC 时间，北京时间 = UTC + 8
    - cron: '0 22 * * *'  # 北京时间 06:00
```

## 免费额度

- GitHub Actions 免费额度：每月 2000 分钟
- 每次运行约 2-3 分钟
- 每月可运行约 600-1000 次，足够每天运行

## 故障排查

### 采集失败
1. 进入 "Actions" → 点击失败的运行
2. 查看日志，找到错误信息
3. 常见问题：
   - FDA 网站结构变化 → 需要更新 `scraper.py`
   - 网络超时 → 重试即可

### 没有数据
- 可能是当月没有新审批药物
- 查看 `data/fda_YYYY-MM-DD.json` 中的 `total` 字段

## 后续优化

- [ ] 添加数据推送到服务器 API
- [ ] 添加钉钉通知
- [ ] 添加历史数据对比
- [ ] 添加 Excel 导出功能
