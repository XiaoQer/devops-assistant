export interface AuthenticatedUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
}

export interface AuthResponse {
  user: AuthenticatedUser
  csrf_token: string
}

export interface Execution {
  id: number
  build_version_id?: number
  pipeline_run_name: string
  status: string
  started_at?: string
  finished_at?: string
  error_message?: string
  created_at: string
}

export interface BuildVersion {
  id: number
  application_id: number
  project_id: number
  version: string
  git_repo: string
  git_branch: string
  git_commit?: string
  build_type?: string
  commit_message?: string
  commit_author?: string
  image_name: string
  image_tag: string
  image_digest?: string
  image: string
  pipeline_run_name?: string
  status: string
  created_by: string
  created_at: string
  finished_at?: string
  error_message?: string
}

export interface GitBranch { name: string; sha: string }
export interface GitCommit { sha: string; message: string; author: string; authored_at: string }
export interface ReleaseTarget {
  id: number; batch_id: number; environment_id: number; environment?: string; display_name?: string
  namespace?: string; build_version_id?: number; pipeline_run_name?: string; status: string
  approval_id?: number; error_message?: string; created_at: string; updated_at: string
}
export interface ReleaseBatch {
  id: number; application_id: number; project_id: number; build_version_id?: number
  branch: string; git_commit: string; commit_message?: string; commit_author?: string
  status: string; created_by: string; created_at: string; updated_at: string; targets: ReleaseTarget[]
}

export interface Release {
  id: number
  application_id?: number
  application_name?: string
  release_type: 'deploy' | 'rollback'
  environment: string
  git_branch: string
  git_commit?: string
  image: string
  image_tag: string
  pipeline_run_name?: string
  deploy_namespace: string
  deploy_status: string
  deploy_user: string
  source_release_id?: number
  build_version_id?: number
  created_at: string
  finished_at?: string
  error_message?: string
}

export interface RuntimeStatus {
  status: 'Healthy' | 'Progressing' | 'Degraded' | 'Failed' | 'Unknown'
  environment: string
  namespace: string
  deployment: {
    name: string
    replicas: number
    ready_replicas: number
    updated_replicas: number
    available_replicas: number
    images: string[]
  }
  pods: Array<{
    name: string
    status: string
    ready: boolean
    restart_count: number
    node: string
  }>
  service?: { name: string; type: string; cluster_ip: string; ports: number[] }
  ingress?: { host?: string; address?: string }
  events: Array<{ type: string; reason: string; message: string; count: number }>
  replica_sets?: Array<Record<string, unknown>>
  persistent_volume_claims?: Array<Record<string, unknown>>
  config_maps?: Array<Record<string, unknown>>
  secrets?: Array<Record<string, unknown>>
}

export interface ApplicationEnvironment {
  id: number
  application_id: number
  kubernetes_cluster_id?: number | null
  environment_name: string
  display_name?: string
  cluster_name: string
  kube_context?: string
  namespace: string
  replicas: number
  image_registry?: string
  ingress_domain?: string
  cpu_request: string
  cpu_limit: string
  memory_request: string
  memory_limit: string
  storage_size?: string
  deploy_strategy: string
  max_unavailable: string
  max_surge: string
  approval_required: boolean
  status: string
  updated_at: string
}

export interface Project {
  id: number
  key: string
  name: string
  description?: string
  status?: string
  business_owner?: string
  billing_owner?: string
  github_group?: string
  github_default_visibility?: 'private' | 'internal' | 'public' | string
  aliyun_account_id?: string
  aliyun_resource_group_id?: string
  aliyun_region?: string
  aliyun_vpc_id?: string
  aliyun_binding_status?: 'unbound' | 'pending' | 'linked' | 'failed' | string
  my_role?: string
  last_release?: string
  application_count?: number
  member_count?: number
  applications_count?: number
  members_count?: number
  clusters_count?: number
  registries_count?: number
  members?: ProjectMember[]
  environments?: ProjectEnvironment[]
  clusters?: KubernetesCluster[]
  registries?: ContainerRegistry[]
  created_at: string
  updated_at: string
}

export interface ProjectEnvironment {
  id?: number
  environment_name: string
  display_name?: string
  namespace?: string
  cluster_name?: string
  registry_name?: string
  approval_required?: boolean
}

export interface ProjectMember {
  id: number
  project_id: number
  name: string
  email: string
  role: 'owner' | 'admin' | 'developer' | 'viewer'
  title?: string
  status: 'active' | 'invited' | string
  created_at: string
  updated_at: string
}

export interface KubernetesCluster {
  id: number
  project_id: number
  name: string
  description?: string
  kube_context: string
  environment_label?: string
  has_kubeconfig: boolean
  namespace_prefix?: string
  api_server?: string
  connection_status: ClusterConnectionStatus
  last_checked_at?: string
  kubernetes_version?: string
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ClusterConnectionStatus = 'untested' | 'connected' | 'failed'

export interface ClusterConnectionResult {
  connected: boolean
  message: string
  api_server?: string
  kubernetes_version?: string
}

export interface ClusterPayload {
  name: string
  environment_label: string
  kube_context: string
  kubeconfig?: string
  namespace_prefix?: string
  description?: string
  is_default?: boolean
  is_active?: boolean
}

export interface ApplicationConfig {
  id: number
  config_group_id: string
  environment_id: number
  config_type: string
  config_key: string
  value: string
  value_format: string
  version: number
  is_secret: boolean
  changed_by: string
  created_at: string
}

export interface Approval {
  id: number
  application_id: number
  application_name?: string
  environment: string
  namespace: string
  image: string
  image_tag: string
  git_branch?: string
  git_commit?: string
  applicant: string
  approver?: string
  status: 'Pending' | 'Approved' | 'Rejected'
  comment?: string
  pipeline_run_name?: string
  created_at: string
  approved_at?: string
  rejected_at?: string
}

export interface DeploymentCheck {
  name: string
  status: 'pass' | 'warn' | 'blocked'
  summary: string
  detail: string
}

export interface DeploymentPlan {
  can_deploy: boolean
  risk_level: 'low' | 'medium' | 'high'
  summary: string
  target: {
    application_id: number
    application_name: string
    environment: string
    namespace: string
    image_name: string
    image_tag: string
    pipeline_name?: string
    approval_required: boolean
  }
  checks: DeploymentCheck[]
  blocked_checks: string[]
  warning_checks: string[]
}

export interface Application {
  id: number
  project_id?: number
  project_name?: string
  name: string
  repo_url: string
  branch: string
  language: string
  framework: string
  build_type: string
  namespace: string
  image_name: string
  image_tag: string
  port: number
  status: string
  application_spec?: Record<string, unknown>
  latest_execution?: Execution
}

export interface ContainerRegistry {
  id: number
  project_id?: number | null
  project_name?: string | null
  name: string
  provider: 'acr' | 'harbor' | 'dockerhub' | 'ecr' | 'gcr' | 'generic' | 'ghcr'
  server: string
  namespace: string
  image_prefix: string
  username: string
  email: string
  pull_secret_name: string
  has_credentials: boolean
  skip_tls_verify: boolean
  connection_status: RegistryConnectionStatus
  last_checked_at?: string | null
  last_connection_message?: string | null
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type RegistryConnectionStatus = 'untested' | 'connected' | 'failed'

export interface RegistryPayload {
  name: string
  provider: ContainerRegistry['provider']
  server: string
  namespace?: string
  username: string
  password?: string
  email?: string
  pull_secret_name?: string
  skip_tls_verify: boolean
  is_active: boolean
}

export interface RegistryConnectionResult {
  connected: boolean
  message: string
  tls_verified: boolean
  auth_method?: 'basic' | 'bearer'
  failure_reason?:
    | 'authentication_failed'
    | 'tls_failed'
    | 'timeout'
    | 'unreachable'
    | 'protocol_error'
}

export interface PipelineRunSummary {
  name: string
  namespace: string
  application?: string
  pipeline?: string
  status: string
  reason: string
  repo_url?: string
  branch?: string
  image?: string
  started_at?: string
  finished_at?: string
  created_at: string
}
