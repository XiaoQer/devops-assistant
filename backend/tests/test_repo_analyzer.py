import json

from app.services.repo_analyzer_service import RepoAnalyzerService


def test_detects_spring_boot(tmp_path):
    (tmp_path / "src/main/java").mkdir(parents=True)
    (tmp_path / "pom.xml").write_text("<artifactId>spring-boot</artifactId>")
    assert RepoAnalyzerService().analyze_path(tmp_path) == {
        "language": "java",
        "framework": "spring-boot",
        "build_type": "maven",
        "port": 8080,
    }


def test_detects_vite(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}))
    (tmp_path / "vite.config.ts").touch()
    assert RepoAnalyzerService().analyze_path(tmp_path)["framework"] == "vite"


def test_dockerfile_fallback(tmp_path):
    (tmp_path / "Dockerfile").touch()
    assert RepoAnalyzerService().analyze_path(tmp_path)["build_type"] == "dockerfile"

