import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo

from app.utils.errors import ApiError


class GitMetadataService:
    MAX_COMMITS = 20

    def _validate_repo(self, repo_url):
        if not isinstance(repo_url, str) or not repo_url.startswith(("https://", "git@")):
            raise ApiError("仅支持公共 Git HTTPS/SSH 仓库", 422, "GIT_REPOSITORY_UNAVAILABLE")

    def list_branches(self, repo_url):
        self._validate_repo(repo_url)
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", repo_url],
                check=True, capture_output=True, text=True, timeout=30,
            )
        except Exception as exc:
            raise ApiError("无法读取 Git 仓库分支", 422, "GIT_REPOSITORY_UNAVAILABLE") from exc
        branches = []
        for line in result.stdout.splitlines():
            sha, ref = (line.split("\t", 1) + [""])[:2]
            if ref.startswith("refs/heads/"):
                branches.append({"name": ref.removeprefix("refs/heads/"), "sha": sha})
        return sorted(branches, key=lambda item: item["name"])

    def list_commits(self, repo_url, branch, limit=20):
        self._validate_repo(repo_url)
        if not branch or limit < 1 or limit > self.MAX_COMMITS:
            raise ApiError("提交记录最多查询 20 条", 400, "GIT_COMMIT_LIMIT_INVALID")
        workdir = tempfile.mkdtemp(prefix="aegis-git-")
        try:
            Repo.clone_from(repo_url, workdir, branch=branch, depth=limit)
            commits = []
            for commit in Repo(workdir).iter_commits(branch, max_count=limit):
                commits.append({
                    "sha": commit.hexsha,
                    "message": commit.message.strip().splitlines()[0][:240],
                    "author": str(commit.author),
                    "authored_at": commit.authored_datetime.isoformat(),
                })
            return commits
        except Exception as exc:
            message = "指定分支不存在" if "branch" in str(exc).lower() else "无法读取分支提交记录"
            code = "GIT_BRANCH_NOT_FOUND" if message == "指定分支不存在" else "GIT_COMMITS_UNAVAILABLE"
            raise ApiError(message, 422, code) from exc
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
