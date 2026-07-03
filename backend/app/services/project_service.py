from app.extensions import db
from app.models import Project, ProjectMember
from app.utils.errors import ApiError


class ProjectService:
    MEMBER_ROLES = {"owner", "admin", "developer", "viewer"}

    def list(self):
        return Project.query.order_by(Project.created_at.desc()).all()

    def get(self, project_id):
        project = Project.query.get(project_id)
        if not project:
            raise ApiError("项目不存在", 404, "PROJECT_NOT_FOUND")
        return project

    def create(self, payload):
        key = str(payload.get("key", "")).strip().lower()
        name = str(payload.get("name", "")).strip()
        if not key or not name:
            raise ApiError("key 和 name 为必填字段")
        if Project.query.filter_by(key=key).first():
            raise ApiError("项目标识已存在", 409, "PROJECT_KEY_EXISTS")
        project = Project(key=key, name=name, description=payload.get("description"))
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
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ApiError("name 不能为空")
            project.name = name
        if "description" in payload:
            project.description = payload.get("description")
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
