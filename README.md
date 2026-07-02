# Aegis — AI Native DevOps Platform MVP

从 GitHub 仓库自动识别 Java、Node.js 或 Dockerfile 项目，生成统一
Application Spec，并通过 Kubernetes API 创建 Tekton PipelineRun。

## 文档入口

项目采用 Harness Engineering 工作方式。仓库而不是聊天记录是项目事实来源：

- [`AGENTS.md`](./AGENTS.md)：Agent 工作规则、架构约束与完成定义
- [`docs/README.md`](./docs/README.md)：产品、架构、领域模型与当前状态
- [`specs/README.md`](./specs/README.md)：需求规格、验收条件与历史记录
- [`scripts/verify.sh`](./scripts/verify.sh)：本地和 CI 共用的验证入口

开始功能开发前，先从 `specs/template.md` 创建需求规格。行为发生变化后，同步更新
`docs/current-state.md`；长期架构选择记录在 `docs/decisions/`。

## 架构

```text
Vue 3 Web
   │ REST
Flask API ── MySQL
   │ Kubernetes Python Client
Kubernetes API ── Tekton ── Kaniko ── Deployment / Service
```

后端采用 Controller → Service → Infrastructure 分层。所有 Kubernetes
连接初始化都位于 `KubernetesService`，所有 Tekton 资源读写都位于
`TektonService`。

## 本地运行

前置条件：Python 3.11+、Node.js 20+、Docker，以及可用的
`~/.kube/config`。测试阶段仅 MySQL 使用 Docker，后端和前端直接运行在
宿主机。

先启动 MySQL：

```bash
docker compose up -d --remove-orphans
docker compose ps
```

MySQL 暴露在 `localhost:3307`，测试账号为 `devops` / `devops`，数据库名为
`devops_platform`。

然后启动后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='mysql+pymysql://devops:devops@localhost:3307/devops_platform?charset=utf8mb4'
export AUTO_CREATE_SCHEMA=true
python run.py
```

`AUTO_CREATE_SCHEMA=true` 只用于本地测试，首次运行时自动建表。生产环境应设置
为 `false` 并执行 Alembic migration。

确认后端能直接读取本机 kubeconfig：

```bash
curl http://localhost:5001/api/health/kubernetes
```

返回 `connected: true` 后再触发部署。最后在另一个终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

如本机 `3307` 已被占用，可覆盖 MySQL 端口，并同步修改 `DATABASE_URL`：

```bash
MYSQL_PORT=13306 docker compose up -d
```

停止 MySQL 使用 `docker compose down`，需要同时清空测试数据则使用
`docker compose down -v`。

## 集群部署

1. 构建并推送 `backend/` 与 `frontend/` 的容器镜像，并修改部署清单中的
   `registry.local`。
2. 创建名为 `devops-platform-database` 的 Secret，其中 `url` 是 MySQL
   连接串。
3. 安装权限、Pipeline 和后端：

```bash
kubectl apply -f deploy/backend/rbac.yaml
kubectl apply -f deploy/tekton/pipelines/
kubectl apply -f deploy/backend/deployment.yaml
kubectl apply -f deploy/backend/service.yaml
```

检测到 `KUBERNETES_SERVICE_HOST` 后，后端自动调用
`config.load_incluster_config()`；否则调用 `config.load_kube_config()`。

## 运行前配置

- 在 Platform → Registries 中配置平台级镜像仓库并设为默认，例如 ACR
  `company.azurecr.io` 和 Namespace `platform`。应用发布时自动生成
  `company.azurecr.io/platform/<application>:<tag>`。
- 私有仓库用户名和 Token 在 Registry 页面统一配置并加密保存。发布时平台
  自动在 Tekton 与目标 Namespace 中生成 Docker config Secret，同时挂载给
  Kaniko 并配置到目标 Deployment 的 `imagePullSecrets`。
- Pipeline 使用动态 PVC 作为源码工作区，集群需提供默认 StorageClass。
- `devops-platform-pipeline` 默认拥有跨命名空间部署 Deployment/Service 的
  权限。生产环境建议按目标 Namespace 收敛为 RoleBinding。
- Java/Node 模板假定仓库提供 Dockerfile。后续可增加自动生成 Dockerfile。

环境发布时会将以下配置真正应用到 Kubernetes：

- Environment Variables / ConfigMap → `<app>-config`
- Secret → `<app>-secret`
- Replicas、CPU、Memory → Deployment
- RollingUpdate / Recreate → Deployment Strategy
- Ingress Domain → Ingress

状态同步可手动执行，也适合由 cron 定期调用：

```bash
cd backend
source .venv/bin/activate
flask --app run:app sync-deliveries
```

## API

- `POST /api/applications`：克隆、识别并创建应用
- `GET /api/applications` / `GET /api/applications/:id`
- `POST /api/applications/:id/deploy`
- `GET /api/applications/:id/executions`
- `GET /api/applications/:id/releases`：发布历史
- `POST /api/applications/:id/rollback`：回滚到历史镜像版本
- `GET /api/applications/:id/status?environment=dev`：Kubernetes 实时状态
- `GET /api/pipelines/:name/status`
- `GET /api/pipelines/:name/logs`：Pipeline、Task 与 Step 结构化日志
- `GET /api/health/kubernetes`

### Software OS v0.2

- `GET/POST /api/applications/:id/environments`
- `PATCH/DELETE /api/applications/:id/environments/:environmentId`
- `POST /api/applications/:id/environments/:environmentId/clone`
- `GET /api/applications/:id/environments/compare`
- `GET/POST /api/applications/:id/configs`
- `PATCH/DELETE /api/configs/:configId`
- `GET /api/configs/:configGroupId/history`
- `GET /api/releases?page=1&pageSize=20`
- `GET /api/applications/:id/runtime/pods/:pod/logs`
- `GET /api/applications/:id/runtime/pods/:pod/yaml`

所有响应均包含 `success`、`message`、`data`、`timestamp` 与 `trace_id`。
Secret 使用 `SECRET_KEY` 派生的密钥加密存储；生产环境必须设置稳定且保密的
`SECRET_KEY`，否则历史 Secret 将无法解密。
