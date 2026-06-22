# Moodtips 数据与图片治理流水线

## 目标

把“新品更新、核图、改图、备注、批量导入”收敛为一条稳定流程，保证：

- 近两个月新品持续刷新
- 图片来源可追踪、可替换、可备注
- 手工核图后的修改可以批量回写数据库
- 前台推荐和后台图片治理使用同一套主数据

## 标准流程

### 1. 刷新近两个月新品

```powershell
py -3 .\moodsips_recent_launch_refresh_20260509.py
```

作用：

- 拉取最近 60 天窗口内的新品整理结果
- 更新 `launch_date`、`lifecycle_code`、`lifecycle_label`
- 重建 `simple_drink_catalog`

### 2. 生成核图 Excel

```powershell
node .\tools\build_brand_image_review_workbook.mjs
```

输出：

- `data\exports\manual_review\moodtips_brand_image_review_20260510.xlsx`

### 3. 人工核图与改图

在 Excel 中优先处理 `SKU核图清单`：

- `review_status`：标记为 `approved / 通过 / 已确认`
- `batch_import_ready`：填 `yes / true / 1 / 是`
- `replacement_file_or_url`：填本地图片绝对路径、`file:///...`、`/generated/...` 或可访问的图片 URL
- `override_note`：补充替换原因、来源说明、人工判断备注

建议规则：

- 图不确定时，先保留原图，并写明原因
- 图实在不稳时，优先用品牌 Logo 或官方合拍图
- 只有确认可替换时再写 `approved`

### 4. 批量导入

```powershell
py -3 .\moodsips_import_brand_review_workbook_20260511.py --workbook .\data\exports\manual_review\moodtips_brand_image_review_20260510.xlsx
```

导入后会同时：

- 更新 `menu_item_master.image_url`
- 回写 `raw_json.official_snapshot.image_meta`
- 写入 `sku_visual_overrides`
- 重建 `simple_drink_catalog`
- 生成导入报告：
  - `data\exports\manual_review\moodtips_brand_review_import_report_20260511.csv`
  - `data\exports\manual_review\moodtips_brand_review_import_report_20260511.json`

## 判定规则

### 图片来源

- `source`：原始官方图
- `user_uploaded`：用户上传替图
- `brand_logo`：品牌 Logo
- `brand_collage`：官方合拍图
- `brand_fallback`：品牌兜底图
- `ai_illustration`：AI 示意图

### 核图状态

- `approved`：可以导入
- `pending`：继续核图
- `skip`：跳过

## 常见问题

### 1. 新品被标成常驻

先检查：

- 是否有明确 `launch_date`
- 是否存在 `lifecycle_code`
- 来源是否落在最近 60 天窗口内

### 2. 图片和饮品不匹配

优先排查：

- `brand_code` 和 `item_name` 是否匹配
- 是否误命中兜底图 `brand_fallback`
- 是否是旧图还没替换
- 是否该条记录本来就只有 Logo 或合拍图可用

### 3. 批量导入没有生效

先检查：

- `review_status` 是否是可导入状态
- `batch_import_ready` 是否为真值
- `replacement_file_or_url` 是否可解析
- 图片文件是否真实存在

## 建议节奏

- 每次新品刷新后，先重建 Excel
- 每轮人工核图完成后，再跑一次批量导入
- 每次导入后，检查报告 CSV 与首页结果页

