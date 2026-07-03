import json
import shutil
import tempfile
from pathlib import Path

from git import Repo

from app.utils.errors import ApiError


class RepoAnalyzerService:
    def analyze(self, repo_url, branch="main"):
        workdir = tempfile.mkdtemp(prefix="devops-repo-")
        try:
            Repo.clone_from(repo_url, workdir, branch=branch, depth=1)
            return self.analyze_path(Path(workdir))
        except Exception as exc:
            raise ApiError(
                f"无法克隆或分析仓库: {exc}", 422, "REPOSITORY_ANALYSIS_FAILED"
            ) from exc
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def analyze_path(self, root):
        has_dockerfile = (root / "Dockerfile").is_file()
        pom = root / "pom.xml"
        package_file = root / "package.json"

        if pom.is_file() and (root / "src/main/java").is_dir():
            content = pom.read_text(errors="ignore")
            spring = "spring-boot" in content
            return {
                "language": "java",
                "framework": "spring-boot" if spring else "unknown",
                "build_type": "maven",
                "port": 8080,
            }
        if package_file.is_file():
            package = json.loads(package_file.read_text(errors="ignore"))
            deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
            if (root / "vite.config.ts").exists() or (root / "vite.config.js").exists():
                framework = "vite"
            elif (root / "next.config.ts").exists() or (root / "next.config.js").exists():
                framework = "nextjs"
            elif "express" in deps:
                framework = "express"
            else:
                framework = "unknown"
            if (root / "pnpm-lock.yaml").exists():
                build_type = "pnpm"
            elif (root / "yarn.lock").exists():
                build_type = "yarn"
            else:
                build_type = "npm"
            return {
                "language": "nodejs",
                "framework": framework,
                "build_type": build_type,
                "port": 3000,
            }
        if has_dockerfile:
            return {
                "language": "dockerfile",
                "framework": "unknown",
                "build_type": "dockerfile",
                "port": 8080,
            }
        return {
            "language": "unknown",
            "framework": "unknown",
            "build_type": "unknown",
            "port": 8080,
        }

