# genshin-story-data

《原神》游戏文本的整合仓库 —— 把散落在各处的角色、任务、书籍、武器、圣遗物与地图
文本收拢成统一、可直接检索的结构化数据集，并在其上构建了一层实体关系知识图谱。

> ## ⚠️ 版权声明
>
> `export/` 下的**全部文本内容**来源于米哈游（miHoYo / HoYoverse）的游戏《原神》，
> **著作权与版权归米哈游所有**，本仓库作者不主张任何权利。
>
> 本仓库为**非官方**项目，与米哈游无关联，仅供个人学习研究，**不作任何商业用途**。
> 使用者请**尊重米哈游的合法权益**，勿将这些文本用于商业目的。
>
> 详见 [COPYRIGHT.md](COPYRIGHT.md)。

## 数据内容

数据以 JSON 形式存放在 `export/`，每个 collection 一个文件，共 **124,718 条**记录。
格式为 MongoDB Relaxed Extended JSON（`ObjectId` / `datetime` 等类型信息保留），
文件本身是合法的 JSON 数组，每行一条记录，可直接 `json.load` 或按行流式读取。

### 文本数据

同名的两个版本：无后缀的是**原始页面数据**（含大量展示层字段，如
`template_id`、`menu_style`、`modules`、图片地址等）；`_filtered` 是**精简正文版**，
只保留 `{id, name, text, mission}` 四个字段，做文本处理时用这个。

| 分类 | 原始 | 精简 | 条数 |
| --- | --- | --- | --- |
| 角色 | `character.json` | `character_filtered.json` | 134 |
| 任务 | `mission.json` | `mission_filtered.json` | 1,053 |
| 地图文本 | `map_text.json` | `map_text_filtered.json` | 706 |
| 武器 | `weapon.json` | `weapon_filtered.json` | 246 |
| 圣遗物 | `artifact.json` | `artifact_filtered.json` | 63 |
| 书籍 | `book.json` | `book_filtered.json` | 93 |

### 知识图谱

在上述文本之上抽取的实体与关系。

| 文件 | 条数 | 字段 |
| --- | --- | --- |
| `kg_entities.json` | 23,937 | `name` `type` `aliases` `summary` `source_ids` |
| `kg_edges.json` | 94,050 | `src_id` `dst_id` `relation` `relation_label` `evidence` |
| `kg_build_state.json` | 2,141 | `content_hash` `extraction` `status`（增量构建状态） |

实体 `_id` 为 UUID 字符串；边的 `src_id` / `dst_id` 既可能指向实体 UUID，也可能是
`<collection>:<id>` 形式的源文档引用（如 `artifact_filtered:501139`），
`evidence` 记录该关系的出处与原文片段。

## 工具脚本

`export_mongo.py` / `import_mongo.py` 用于在 MongoDB 与 `export/` 之间往返同步。
只使用数据的话不需要它们，直接读 JSON 即可。

### 环境

```bash
uv sync
```

### 配置

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

### 导出

```bash
uv run python export_mongo.py
```

### 导入

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
