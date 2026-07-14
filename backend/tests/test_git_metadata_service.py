import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.git_metadata_service import GitMetadataService
from app.utils.errors import ApiError


class GitMetadataServiceTest(unittest.TestCase):
    def test_lists_and_sorts_remote_branches(self):
        result = SimpleNamespace(stdout="b\trefs/heads/zeta\na\trefs/heads/main\n", returncode=0)
        with patch("app.services.git_metadata_service.subprocess.run", return_value=result):
            branches = GitMetadataService().list_branches("https://github.com/example/repo.git")
        self.assertEqual([item["name"] for item in branches], ["main", "zeta"])

    def test_rejects_more_than_twenty_commits(self):
        with self.assertRaises(ApiError) as context:
            GitMetadataService().list_commits("https://github.com/example/repo.git", "main", 21)
        self.assertEqual(context.exception.code, "GIT_COMMIT_LIMIT_INVALID")


if __name__ == "__main__":
    unittest.main()
