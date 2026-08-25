# story-digger-data

MongoDB 数据导出/导入工具，以及 `export/` 下的数据快照。

> ## ⚠️ 版权声明
>
> `export/` 下的**全部文本内容**来源于米哈游（miHoYo / HoYoverse）的游戏《原神》，
> **著作权与版权归米哈游所有**，本仓库作者不主张任何权利。
>
> 本仓库为**非官方**项目，与米哈游无关联，仅供个人学习研究，**不作任何商业用途**。
> 使用者请**尊重米哈游的合法权益**，勿将这些文本用于商业目的。
>
> 详见 [COPYRIGHT.md](COPYRIGHT.md)。

## 环境

```bash
uv sync
```

## 配置

连接信息通过环境变量传入，脚本内不含任何凭据：

| 变量 | 默认值 |
| --- | --- |
| `MONGO_HOST` | `localhost` |
| `MONGO_PORT` | `27017` |
| `MONGO_DATABASE` | **必填** |
| `MONGO_USERNAME` | **必填** |
| `MONGO_PASSWORD` | **必填** |
| `MONGO_AUTH_DB` | `admin` |

推荐放进 `.env`（已被 gitignore），避免密码留在 shell 历史里：

```bash
set -a && source .env && set +a
```

## 导出

每个 collection 导出为 `export/<collection>.json`，格式为 MongoDB Relaxed
Extended JSON，`ObjectId` / `datetime` 等 BSON 类型信息保留。

```bash
uv run python export_mongo.py
```

## 导入

默认**不覆盖**已有数据：目标 collection 非空时跳过并提示。

```bash
uv run python import_mongo.py --dry-run   # 只报告，不写入
uv run python import_mongo.py --drop      # 清空后导入（覆盖必需）
uv run python import_mongo.py --only kg_edges kg_entities
```

## 说明

- 导出/导入只覆盖**文档数据，不含索引**。目标库若依赖索引（如 `kg_edges` 约 9.4 万条），
  导入后需自行重建。
- `kg_build_state` / `kg_edges` / `kg_entities` 的 `_id` 是字符串而非 `ObjectId`，
  这是源数据设计，round-trip 会如实保留。
