# Find Client（客户组织架构与人脉管理）

Python 栈实现：以公司为入口的组织架构树（可展开/合并、懒加载）、人员信息卡、人员相关新闻采集与摘要入库、以及基于公开资料的“亲密指数”预计算骨架。

## 本地启动（开发）

### 1) 安装依赖

建议使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 运行后端（含简易 UI）

```bash
uvicorn backend.app.main:app --reload --port 8000
```

打开：

- UI：`http://127.0.0.1:8000/ui`
- OpenAPI：`http://127.0.0.1:8000/docs`

默认使用 SQLite（文件在 `backend/data/app.db`）。如需 Postgres，设置环境变量 `DATABASE_URL`。

## 数据采集（新闻）——骨架

当前提供一个基于 GDELT 的“人员相关新闻”拉取与入库脚本骨架（你后续也可以替换为 RSS/媒体站点/企业官网等来源）。

```bash
python -m crawler.news_ingest --api http://127.0.0.1:8000 --person "张三" --company "某某公司" --days 30 --max 20
```

## 组织架构数据导入（可选）

你可以先通过 API 手工创建公司/节点/人员，之后我可以再补一套 CSV 导入器。

