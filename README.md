# InkMill-01 · 油墨研磨台账

面向印刷油墨研磨车间的**研磨机状态、粘度取样、研磨遍次与车间能耗日报**台账系统。  
**不是**库存、电商或 CMS 场景。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11、Flask、SQLAlchemy、PyMySQL、Flask-JWT-Extended、passlib/bcrypt、gunicorn |
| 前端 | Svelte 4、Vite、TypeScript |
| 数据库 | MySQL 8 |

## 端口与数据库

| 服务 | 宿主机端口 |
|------|------------|
| 统一入口 (Nginx) | **4200** |
| 后端 API | **9200** |
| MySQL | **3312** |

MySQL 连接：`inkmill` / `inkmill` / `inkmill`（库名/用户/密码）

## 演示账号

密码均为 **123456**：

- `admin` — 管理员
- `grinder` — 研磨工

## 领域实体（JSON 驼峰）

1. **Workshop**：`name`, `site`, `notes`
2. **Mill**：`workshopId`, `millCode`（同车间唯一）, `pigmentBase`, `bowlLiters`, `status`（`grinding` \| `idle` \| `wash`）
3. **ViscositySample**：`millId`, `sampledAt`, `viscosityPaS`（须 &gt; 0，否则 HTTP 400）, `tempC`, `notes`
4. **GrindPass**：`millId`, `startedAt`, `passNo`（≥ 1）, `durationMin`（&gt; 0）, `mediaType`, `operatorName`
5. **EnergyDaily**（车间能耗日报）：`workshopId`, `workDate`（YYYY-MM-DD）, `kwh`（用电量，非负）, `peakKw`（峰值功率 kW，可空、非负）；同一车间同一日期唯一
6. **Dashboard**：`workshopTotal`, `grindingMillCount`, `samplesLast24h`, `passesLast7d`

### 能耗日报接口（`/api/energy-dailies`，均需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/energy-dailies?workshopId=&startDate=&endDate=` | 按车间与日期区间（含端点）列出日报，日期为 YYYY-MM-DD |
| GET | `/energy-dailies/summary?workshopId=&startDate=&endDate=` | 区间汇总：`totalKwh`（合计 kWh）、`maxPeakKw`、`dayCount` |
| POST | `/energy-dailies` | 新建；`kwh` 非负、`peakKw` 可空非负；同车间同日重复返回 400 |
| PUT | `/energy-dailies/{id}` | 更新（同样校验唯一与非负） |
| DELETE | `/energy-dailies/{id}` | 删除 |

前端侧栏「能耗日报」页：选择车间与日期区间后查看明细表格及区间合计 kWh。

## 快速启动（Docker）

```bash
cd InkMill-01
docker compose up --build -d
```

浏览器访问：**http://localhost:4200**  
前端 Nginx 将 `/api/` 反向代理到后端 `9200`。

后端容器启动流程：

1. 等待 MySQL 就绪（`DB_HOST=mysql`）
2. SQLAlchemy `create_all` 建表
3. `SEED_ON_START=true` 时写入演示数据
4. gunicorn 监听 `0.0.0.0:9200`

健康检查：`GET /api/health` → `{"status":"ok","service":"InkMill"}`

## 本地开发（可选）

**后端**（需本机 MySQL 或连 Docker 的 3312 端口）：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set DB_HOST=127.0.0.1
set DB_PORT=3312
set DB_USER=inkmill
set DB_PASSWORD=inkmill
set DB_NAME=inkmill
set JWT_SECRET=inkmill-jwt-secret-change-me
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
gunicorn wsgi:app --bind 127.0.0.1:9200 --reload
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 开发服务器端口 **4200**，`/api` 代理到 `127.0.0.1:9200`。

## 目录结构

```
InkMill-01/
├── docker-compose.yml
├── nginx/nginx.conf          # 4200 统一入口，/api → backend
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── wsgi.py
│   └── app/                  # Flask 路由、模型与种子数据
└── frontend/
    ├── Dockerfile
    ├── vite.config.ts
    └── src/routes/           # Login / Dashboard / CRUD 页面
```

## UI 主题

墨黑底 + 朱砂强调色，无紫色光晕风格。
