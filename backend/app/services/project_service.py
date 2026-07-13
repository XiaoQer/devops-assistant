from app.extensions import db
from app.models import Project, ProjectMember
from app.utils.errors import ApiError


class ProjectService:
    MEMBER_ROLES = {"owner", "admin", "developer", "viewer"}
    PROJECT_STATUSES = {"active", "inactive", "archived"}
    GITHUB_VISIBILITIES = {"private", "internal", "public"}
    ALIYUN_BINDING_STATUSES = {"unbound", "pending", "linked", "failed"}
    SENSITIVE_KEY_PARTS = ("secret", "token", "password", "access_key", "kubeconfig")
    METADATA_FIELDS = {
        "status",
        "business_owner",
        "billing_owner",
        "github_group",
        "github_default_visibility",
        "aliyun_account_id",
        "aliyun_resource_group_id",
        "aliyun_region",
        "aliyun_vpc_id",
        "aliyun_binding_status",
    }
    TEXT_LIMITS = {
        "business_owner": 120,
        "billing_owner": 120,
        "github_group": 255,
        "aliyun_account_id": 64,
        "aliyun_resource_group_id": 120,
        "aliyun_region": 64,
        "aliyun_vpc_id": 120,
    }

    def list(self):
        return Project.query.order_by(Project.created_at.desc()).all()

    def get(self, project_id):
        project = Project.query.get(project_id)
        if not project:
            raise ApiError("项目不存在", 404, "PROJECT_NOT_FOUND")
        return project

    def create(self, payload):
        self._reject_sensitive_fields(payload)
        key = str(payload.get("key", "")).strip().lower()
        name = str(payload.get("name", "")).strip()
        if not key or not name:
            raise ApiError("key 和 name 为必填字段")
        if Project.query.filter_by(key=key).first():
            raise ApiError("项目标识已存在", 409, "PROJECT_KEY_EXISTS")
        project = Project(
            key=key,
            name=name,
            description=payload.get("description"),
            **self._metadata_values(payload),
        )
        db.session.add(project)
        db.session.flush()
        owner_name = str(payload.get("owner_name", "")).strip()
        owner_email = str(payload.get("owner_email", "")).strip().lower()
        if owner_name and owner_email:
            db.session.add(ProjectMember(
                project_id=project.id,
                name=owner_name,
                email=owner_email,
                role="owner",
                title=payload.get("owner_title") or "Project owner",
            ))
        db.session.commit()
        return project

    def update(self, project, payload):
        self._reject_sensitive_fields(payload)
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ApiError("name 不能为空")
            project.name = name
        if "description" in payload:
            project.description = payload.get("description")
        for key, value in self._metadata_values(payload).items():
            setattr(project, key, value)
        db.session.commit()
        return project

    def delete(self, project):
        if project.applications or project.members or project.kubernetes_clusters or project.registries:
            raise ApiError("仅空 Project 可以删除", 409, "PROJECT_NOT_EMPTY")
        db.session.delete(project)
        db.session.commit()

    def list_members(self, project):
        return ProjectMember.query.filter_by(project_id=project.id).order_by(ProjectMember.id).all()

    def add_member(self, project, payload):
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        role = str(payload.get("role", "developer")).strip().lower()
        if not name or not email:
            raise ApiError("name 和 email 为必填字段")
        if role not in self.MEMBER_ROLES:
            raise ApiError("不支持的成员角色")
        if ProjectMember.query.filter_by(project_id=project.id, email=email).first():
            raise ApiError("该成员已存在于项目中", 409, "PROJECT_MEMBER_EXISTS")
        member = ProjectMember(
            project_id=project.id,
            name=name,
            email=email,
            role=role,
            title=payload.get("title"),
            status=str(payload.get("status", "active")).strip().lower() or "active",
        )
        db.session.add(member)
        db.session.commit()
        return member

    def update_member(self, member, payload):
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ApiError("name 不能为空")
            member.name = name
        if "email" in payload:
            email = str(payload.get("email") or "").strip().lower()
            if not email:
                raise ApiError("email 不能为空")
            duplicate = ProjectMember.query.filter_by(
                project_id=member.project_id,
                email=email,
            ).filter(ProjectMember.id != member.id).first()
            if duplicate:
                raise ApiError("该邮箱已存在于项目中", 409, "PROJECT_MEMBER_EXISTS")
            member.email = email
        if "role" in payload:
            role = str(payload.get("role") or "").strip().lower()
            if role not in self.MEMBER_ROLES:
                raise ApiError("不支持的成员角色")
            member.role = role
        if "title" in payload:
            member.title = payload.get("title")
        if "status" in payload:
            member.status = str(payload.get("status") or "active").strip().lower()
        db.session.commit()
        return member

    def delete_member(self, member):
        db.session.delete(member)
        db.session.commit()

    def get_member(self, project, member_id):
        member = ProjectMember.query.filter_by(project_id=project.id, id=member_id).first()
        if not member:
            raise ApiError("项目成员不存在", 404, "PROJECT_MEMBER_NOT_FOUND")
        return member

    def ensure_default_project(self):
        project = Project.query.filter_by(key="default").first()
        if project:
            return project
        project = Project(key="default", name="Default Project", description="系统默认项目")
        db.session.add(project)
        db.session.commit()
        return project

    @classmethod
    def _metadata_values(cls, payload):
        values = {}
        if "status" in payload:
            status = cls._choice(payload.get("status"), cls.PROJECT_STATUSES)
            if status not in cls.PROJECT_STATUSES:
                raise ApiError("不支持的项目状态", 400, "PROJECT_INVALID_STATUS")
            values["status"] = status
        if "github_default_visibility" in payload:
            visibility = cls._choice(
                payload.get("github_default_visibility"),
                cls.GITHUB_VISIBILITIES,
            )
            if visibility not in cls.GITHUB_VISIBILITIES:
                raise ApiError(
                    "不支持的 GitHub 默认可见性",
                    400,
                    "PROJECT_INVALID_GITHUB_VISIBILITY",
                )
            values["github_default_visibility"] = visibility
        if "aliyun_binding_status" in payload:
            binding_status = cls._choice(
                payload.get("aliyun_binding_status"),
                cls.ALIYUN_BINDING_STATUSES,
            )
            if binding_status not in cls.ALIYUN_BINDING_STATUSES:
                raise ApiError(
                    "不支持的 Aliyun 绑定状态",
                    400,
                    "PROJECT_INVALID_ALIYUN_BINDING_STATUS",
                )
            values["aliyun_binding_status"] = binding_status
        for field, limit in cls.TEXT_LIMITS.items():
            if field in payload:
                values[field] = cls._limited_text(payload.get(field), limit, field)
        return values

    @staticmethod
    def _choice(value, allowed):
        normalized = str(value or "").strip().lower()
        return normalized if normalized in allowed else normalized

    @staticmethod
    def _limited_text(value, limit, field):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > limit:
            raise ApiError("Project 字段过长", 400, "PROJECT_FIELD_TOO_LONG", field)
        return text

    @classmethod
    def _reject_sensitive_fields(cls, payload):
        for key in payload:
            normalized = str(key).lower()
            if any(part in normalized for part in cls.SENSITIVE_KEY_PARTS):
                raise ApiError(
                    "Project 元信息不能包含敏感凭据字段",
                    400,
                    "PROJECT_SENSITIVE_FIELD",
                    key,
                )
