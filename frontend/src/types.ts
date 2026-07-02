export interface Execution {
  id: number
  pipeline_run_name: string
  status: string
  started_at?: string
  finished_at?: string
  error_message?: string
  created_at: string
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
  namespace_prefix?: string
  api_server?: string
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
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
  provider: 'acr' | 'harbor' | 'dockerhub' | 'ecr' | 'gcr' | 'generic'
  server: string
  namespace: string
  image_prefix: string
  username: string
  email: string
  pull_secret_name: string
  has_credentials: boolean
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
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
