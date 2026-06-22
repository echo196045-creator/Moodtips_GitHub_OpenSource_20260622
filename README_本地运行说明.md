# Moodtips 本地运行文件夹

## 运行入口

1. 双击或在 PowerShell 中运行 `start_moodtips.bat`。
2. 启动脚本会自动寻找 `8000-8020` 之间的空端口，并在窗口里打印实际访问链接。
3. 浏览器打开脚本显示的地址，例如：`http://127.0.0.1:8000/app/` 或 `http://127.0.0.1:8001/app/`。
4. 后端接口文档地址同端口，例如：`http://127.0.0.1:8001/docs`。

## 主要文件

- `serve_moodsips.py`：统一启动入口。
- `04_code/05_product_demo/moodsips_fastapi_service_20260404.py`：FastAPI 后端服务。
- `04_code/05_product_demo/frontend/`：前端网页和图片资源。
- `04_code/05_product_demo/data/moodsips_local_demo_20260404.db`：SQLite 数据库。
- `07_prototype/`：早期推荐引擎所需的种子 SKU 和权重矩阵。

## 注意

- 首次运行会自动安装 Python 依赖，需要联网。
- 不要直接双击 `frontend/index.html`。必须先运行 `start_moodtips.bat`，再打开脚本显示的 `/app/` 链接，否则前端可能连不到推荐接口。
- 如果 `8000` 端口被其他程序占用，脚本会自动改用 `8001`、`8002` 等端口。不要手动固定打开旧的 `http://127.0.0.1:8000/app/`，以脚本显示的地址为准。
- 人工上传/审核后的图片会写入 `frontend/generated/review_uploads/`，数据库仍是 `data/moodsips_local_demo_20260404.db`。

## 常见问题

### 页面能打开，但怎么选都显示没有推荐？

通常不是数据库为空，而是没有连到 Moodtips 后端。请按下面顺序检查：

1. `start_moodtips.bat` 窗口必须保持打开。
2. 打开脚本窗口里显示的 `/app/` 地址，不要自己猜端口。
3. 在浏览器访问同端口的 `/health`，例如 `http://127.0.0.1:8001/health`，如果看到 `{"status":"ok"}` 才说明后端正常。
4. 如果打开的是别的项目页面，说明端口被其他程序占用，请重新运行 `start_moodtips.bat` 并使用它显示的新端口。
