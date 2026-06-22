# Moodtips

Moodtips 是一个已经部署并投入使用的情绪饮品推荐系统。用户选择当下状态、口味、冷热、价格和咖啡因偏好后，系统会从饮品库中筛选候选 SKU，并给出推荐理由、图片来源可信度和后续操作入口。

线上演示地址：[https://moodtips.oppenchow.online/app/](https://moodtips.oppenchow.online/app/)

欢迎大家直接使用 Moodtips，也欢迎共同维护饮品库：补充缺失的饮品图片、上传新饮品、协助校对品牌、价格、口味标签和图片来源，让推荐结果越来越完整、准确、好用。

## 功能亮点

- 情绪入口：开心、躺平、烦躁、难受四类状态，对应后端四个情绪标签池。
- 规则推荐：综合情绪标签、口味标签、价格、冷热、咖啡因和历史避让规则生成推荐。
- 结构化解释：推荐理由区分情绪匹配、口味匹配、约束匹配和图片可信度。
- 商品库治理：使用 SQLite 保存饮品、品牌、标签、推荐记录和图片审核记录。
- 图片审核：用户可上传缺失或更准确的饮品图片，进入待审核队列；审核通过后可同步到前台展示。
- 共创维护：支持围绕新饮品、季节限定 SKU、图片核验和口味标签持续补充数据。
- 本地可运行：不依赖云服务即可启动完整前后端 Demo。

## 技术栈

- 前端：HTML、CSS、JavaScript
- 后端：FastAPI、Uvicorn
- 数据库：SQLite
- 推荐方式：规则引擎为主；AI 文案增强为可选能力，不影响基础推荐运行

## 快速启动

Windows 用户可直接双击：

```bat
start_moodtips.bat
```

脚本会自动安装依赖、寻找 `8000-8020` 之间的空端口，并打印访问地址，例如：

```text
http://127.0.0.1:8000/app/
```

请以脚本窗口显示的地址为准。不要直接双击 `frontend/index.html`，否则前端可能无法连接推荐接口。

也可以用命令行启动：

```bash
python -m pip install -r requirements.txt
python serve_moodsips.py
```

启动后常用入口：

- 用户端：`http://127.0.0.1:8000/app/`
- 后台接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- 数据与图片治理页：`http://127.0.0.1:8000/app/ops.html`

## 项目结构

```text
Moodtips_GitHub_OpenSource_20260622/
├─ serve_moodsips.py                         # 本地统一启动入口
├─ start_moodtips.bat                        # Windows 一键启动脚本
├─ start_moodtips_safe.ps1                   # 自动找端口和安装依赖
├─ requirements.txt                          # 根依赖入口
├─ 04_code/05_product_demo/
│  ├─ moodsips_fastapi_service_20260404.py   # FastAPI 服务与 API
│  ├─ moodsips_storage_20260404.py           # SQLite 数据读写和治理逻辑
│  ├─ moodsips_recommendation_demo_20260404.py
│  ├─ data/moodsips_local_demo_20260404.db   # 演示数据库
│  └─ frontend/                              # 前端页面、情绪图、商品图
├─ 07_prototype/                             # 早期推荐原型数据
└─ docs/                                     # 发布与维护说明
```

## 数据与图片治理

核心数据库位于：

```text
04_code/05_product_demo/data/moodsips_local_demo_20260404.db
```

商品图主要位于：

```text
04_code/05_product_demo/frontend/generated/
```

图片审核流程：

1. 用户在前台或治理页上传缺失饮品图、替换图或新饮品候选图。
2. 后端将图片写入 `frontend/generated/review_uploads/`，并在数据库中生成待审核记录。
3. 管理者在 `/app/ops.html` 或 `/docs` 中查看待审核记录。
4. 审核通过后，数据库中的商品图片地址更新，前台推荐结果同步展示新图。

共创建议：

- 上传图片时尽量选择品牌官方图、门店菜单图或清晰实拍图。
- 新饮品建议补充品牌、饮品名、价格、冷热属性、咖啡因水平、口味标签和是否季节限定。
- 对不确定的数据请保留备注，方便后续审核。

## 开源说明

本仓库包含运行 Moodtips 所需的代码、演示数据库和前台素材。课程报告、课堂展示页、历史压缩包、缓存文件和旧版本操作文件没有放入此开源目录。

商品信息与图片素材用于课程学习、系统设计展示和本地功能演示。若用于商业发布，请自行核验品牌、商品、价格、图片与数据来源的授权和时效性。

## GitHub Desktop 发布

详细步骤见：[docs/GITHUB_DESKTOP_GUIDE.md](docs/GITHUB_DESKTOP_GUIDE.md)

建议在 GitHub 仓库的 About / Website 中填写：

```text
https://moodtips.oppenchow.online/app/
```

## License

MIT License. See [LICENSE](LICENSE).
