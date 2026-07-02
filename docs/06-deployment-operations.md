# 06. Deployment & Operations

## 1. Purpose

本文件说明 Aegis 平台如何在本地和 Kubernetes 集群��运行，以及在运行前需要满足哪些依赖条件。

它的目标是让读者快速回答：

- 平台怎么启动？
- 平台依赖哪些组件？
- 部署前要配置什么？
- 运行时如何诊断问题？

---

## 2. Runtime Topology

Aegis 当前的运行形态可以分为两类：

### 2.1 Local Development Mode
- MySQL 通过 Docker Compose 运行
- Backend 直接运行在宿主机
- Frontend 直接运行在宿主机
- Kubernetes / Tekton 通过本机 `~/.kube/config` 访问

### 2.2 Cluster Deployment Mode
- Backend 运行在 Kubernetes 中
- Frontend 可容器化部署
- MySQL 可以是外部托管库或集群内服务
- Backend 使用 In-Cluster Config 访问 Kubernetes API

---

## 3. Local Development Setup

## 3.1 Prerequisites

需要：
- Python 3.11+
- Node.js 20+
- Docker
- 可用的 Kubernetes 集群访问权限
- 有效的 `~/.kube/config`

## 3.2 Start MySQL

```bash
cd /Users/shaoqian.li/Documents/devops-assistant

docker compose up -d --remove-orphans
docker compose ps
```

默认：
- host: `localhost`
- port: `3307`
- user: `devops`
- password: `devops`
- db: `devops_platform`

## 3.3 Start Backend

```bash
cd /Users/shaoqian.li/Documents/devops-assistant/backend

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='mysql+pymysql://devops:devops@localhost:3307/devops_platform?charset=utf8mb4'
export AUTO_CREATE_SCHEMA=true
python run.py
```

说明：
- `AUTO_CREATE_SCHEMA=true` 仅建议本地开发使用
- 生产环境应使用 Alembic migration 而不是运行时自动建表

## 3.4 Check Kubernetes Connectivity

```bash
curl http://localhost:5001/api/health/kubernetes
```

如果返回连接正常，再继续触发部署操作。

## 3.5 Start Frontend

```bash
cd /Users/shaoqian.li/Documents/devops-assistant/frontend
npm install
npm run dev
```

默认访问：
- `http://localhost:5173`

如果端口被占用，Vite 会自动切到其它端口。

---

## 4. Cluster Deployment

核心部署清单位于：
- `deploy/backend/`
- `deploy/tekton/pipelines/`

## 4.1 Backend RBAC

`deploy/backend/rbac.yaml` 定义：
- ServiceAccount
- ClusterRole
- ClusterRoleBinding

它们用于允许平台：
- 跨 namespace 读取与操作应用相关资源
- 访问 Tekton PipelineRun
- 查询 Pod / Deployment / Service / Ingress / Secret / ConfigMap

## 4.2 Install Tekton Pipelines

需要确保集群已安装 Tekton Pipelines。

然后应用平台提供的流水线模板：

```bash
kubectl apply -f deploy/tekton/pipelines/
```

## 4.3 Deploy Backend

```bash
kubectl apply -f deploy/backend/rbac.yaml
kubectl apply -f deploy/backend/deployment.yaml
kubectl apply -f deploy/backend/service.yaml
```

---

## 5. Required Runtime Dependencies

平台运行依赖以下基础能力：

### 5.1 MySQL
用于保存平台状态：
- applications
- environments
- configs
- releases
- approvals
- registries

### 5.2 Kubernetes API Access
Backend 必须能访问 Kubernetes API，方式包括：
- 本地开发：`load_kube_config()`
- 集群内运行：`load_incluster_config()`

### 5.3 Tekton Pipelines
用于：
- 组织构建与部署工作流
- 创建 PipelineRun
- 追踪执行状态

### 5.4 StorageClass
因为流水线工作区依赖 PVC，因此集群需要：
- 默认 StorageClass
- 支持动态 PVC 分配

### 5.5 Container Registry
平台必须能访问至少一个镜像仓库：
- ACR
- Harbor
- DockerHub
- ECR
- GCR
- Generic OCI Registry

---

## 6. Supported Pipeline Types

当前内置三类流水线模板：

### 6.1 Java + Maven
适用于：
- `pom.xml`
- Java / Spring Boot 服务

模板：
- `java-maven-kaniko-deploy.yaml`

### 6.2 Node.js + npm
适用于：
- `package.json`
- Node / Web / API 项目

模板：
- `node-npm-kaniko-deploy.yaml`

### 6.3 Dockerfile-based
适用于：
- 仓库直接提供 Dockerfile

模板：
- `dockerfile-kaniko-deploy.yaml`

---

## 7. Registry Setup Requirements

在真正部署前，平台级镜像仓库应先配置完成。

建议操作顺序：
1. 打开 `Platform → Registries`
2. 配置默认 Registry
3. 填写 Namespace / Project
4. 填写用户名 / Token
5. 设为默认仓库

平台随后会自动：
- 生成镜像地址前缀
- 生成 Tekton 所需 Docker config Secret
- 生成 Deployment 所需 `imagePullSecrets`

---

## 8. Environment Setup Requirements

每个应用应至少具备一个环境配置，推荐初始化：
- `dev`
- `test`
- `staging`
- `prod`

每个环境应确认：
- namespace
- replicas
- cpu request / limit
- memory request / limit
- ingress domain
- deploy strategy
- approval policy

---

## 9. Configuration Deployment Mapping

平台中的配置最终会落到 Kubernetes：

| 平台配置类型 | K8s 落点 |
|-------------|---------|
| env / configmap | `<app>-config` ConfigMap |
| secret | `<app>-secret` Secret |
| resource | Deployment resources / replicas |
| ingress | Ingress |
| environment strategy | Deployment strategy |

---

## 10. Operations Checklist

在“发布可用”之前，建议检查：

- [ ] MySQL 连接正常
- [ ] Backend 服务健康
- [ ] Frontend 可访问
- [ ] Kubernetes API 连通
- [ ] Tekton 已安装
- [ ] Pipeline 模板已应用
- [ ] 默认 Registry 已配置
- [ ] StorageClass 可动态分配 PVC
- [ ] Pipeline ServiceAccount 权限正常
- [ ] 应用至少存在一个环境配置

---

## 11. Troubleshooting Guide

### 11.1 Backend 无法连接 Kubernetes
检查：
- `~/.kube/config` 是否可用
- 集群证书是否过期
- 集群网络是否可达
- 集群内运行时 RBAC 是否正确

### 11.2 Pipeline 无法启动
检查：
- Tekton 是否已安装
- Pipeline 模板是否存在
- ServiceAccount 是否有权限
- 参数是否完整

### 11.3 Kaniko 推镜像失败
检查：
- Registry 凭据是否正确
- 默认 Registry 是否已配置
- Secret 是否生成成功
- 目标仓库是否允许 push

### 11.4 Deployment 成功但应用不可用
检查：
- namespace 是否正确
- service / ingress 是否存在
- pod logs
- events
- configmap / secret 内容是否正确

### 11.5 Secret 无法正确读取或更新
检查：
- `SECRET_KEY` 是否稳定
- 旧 Secret 是否由不同密钥加密

---

## 12. Sync and Maintenance

平台支持手动同步交付状态：

```bash
cd /Users/shaoqian.li/Documents/devops-assistant/backend
source .venv/bin/activate
flask --app run:app sync-deliveries
```

适合：
- 本地测试
- cron 周期任务
- 故障恢复后的手动修复

---

## 13. Security Notes

当前平台应特别关注：

1. **SECRET_KEY**
   - 生产环境必须稳定、保密

2. **Registry Credentials**
   - 平台已加密保存，但仍需安全管理环境变量和 Secret

3. **RBAC Scope**
   - 当前默认较宽，生产建议尽量收敛到目标命名空间

4. **Database Access**
   - 生产不应暴露弱口令本地配置

---

## 14. Suggested Production Hardening

未来进入更正式部署时，建议：
- 引入 HTTPS / Ingress Gateway
- 拆分 backend / frontend 镜像版本管理
- 增加日志聚合与告警
- 增加备份与恢复策略
- 收敛集群权限
- 增加审计追踪
- 引入更完整的 Secret 管理方案

---

## 15. Summary

Aegis 当前运行方式清晰、依赖明确，已经具备：
- 本地开发闭环
- 集群部署闭环
- 流水线执行闭环
- 运行态排障闭环

这使它足以作为一个真实可运行的平台原型，而不只是静态架构演示项目。

