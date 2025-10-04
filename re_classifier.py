import json
import argparse
import sys
import re
import datetime
import requests
import time
from pathlib import Path
import argparse
from dotenv import load_dotenv
import re
import os
from tqdm import tqdm
from pprint import pprint as _print


class GitHubFileClassifier:
    def __init__(self):
        self.file_patterns = {
            "Development": {
                "extensions": [
                    ".js",
                    ".ts",
                    ".jsx",
                    ".tsx",
                    ".py",
                    ".java",
                    ".cpp",
                    ".c",
                    ".h",
                    ".cs",
                    ".php",
                    ".rb",
                    ".go",
                    ".rs",
                    ".kt",
                    ".swift",
                    ".scala",
                    ".clj",
                    ".hs",
                    ".ml",
                    ".r",
                    ".m",
                    ".sql",
                    ".html",
                    ".css",
                    ".scss",
                    ".sass",
                    ".less",
                    ".vue",
                    ".svelte",
                ],
                "paths": [
                    "src/",
                    "lib/",
                    "app/",
                    "components/",
                    "pages/",
                    "views/",
                    "controllers/",
                    "models/",
                    "services/",
                    "utils/",
                    "helpers/",
                    "core/",
                    "common/",
                    "shared/",
                ],
                "filenames": [
                    "index.js",
                    "main.js",
                    "app.js",
                    "server.js",
                    "client.js",
                    "index.ts",
                    "main.ts",
                    "app.py",
                    "main.py",
                    "__init__.py",
                ],
            },
            "Test": {
                "extensions": [".test.js", ".test.ts", ".spec.js", ".spec.ts", ".test.py", ".spec.py"],
                "paths": [
                    "test/",
                    "tests/",
                    "__tests__/",
                    "spec/",
                    "specs/",
                    ".pytest_cache/",
                    "cypress/",
                    "e2e/",
                    "testing/",
                ],
                "filenames": [
                    "jest.config.js",
                    "jest.config.json",
                    "pytest.ini",
                    "conftest.py",
                    "karma.conf.js",
                    "protractor.conf.js",
                    "cypress.json",
                ],
                "keywords": ["test", "spec", "mock", "fixture", "coverage"],
            },
            "Build": {
                "extensions": [".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"],
                "paths": [
                    "build/",
                    "dist/",
                    "out/",
                    "target/",
                    "bin/",
                    "release/",
                    "scripts/",
                    "tools/",
                    "config/",
                    "configs/",
                ],
                "filenames": [
                    "package.json",
                    "package-lock.json",
                    "yarn.lock",
                    "pnpm-lock.yaml",
                    "Makefile",
                    "makefile",
                    "CMakeLists.txt",
                    "build.gradle",
                    "pom.xml",
                    "setup.py",
                    "setup.cfg",
                    "pyproject.toml",
                    "requirements.txt",
                    "Pipfile",
                    "poetry.lock",
                    "Cargo.toml",
                    "Cargo.lock",
                    "go.mod",
                    "go.sum",
                    "webpack.config.js",
                    "rollup.config.js",
                    "vite.config.js",
                    "tsconfig.json",
                    "babel.config.js",
                    ".babelrc",
                    ".eslintrc.js",
                    ".eslintrc.json",
                    "prettier.config.js",
                    "gulpfile.js",
                    "gruntfile.js",
                    "build.xml",
                    "build.yml",
                    "build.yaml",
                ],
            },
            "Infrastructure": {
                "extensions": [".dockerfile", ".tf", ".hcl", ".sh", ".bat", ".ps1", ".cmd"],
                "paths": [
                    "docker/",
                    "k8s/",
                    "kubernetes/",
                    "terraform/",
                    "ansible/",
                    "puppet/",
                    "chef/",
                    "vagrant/",
                    "helm/",
                    "deploy/",
                    "deployment/",
                    "infra/",
                    "infrastructure/",
                    "ops/",
                    "devops/",
                    ".github/",
                    ".gitlab/",
                    "ci/",
                    ".circleci/",
                ],
                "filenames": [
                    "Dockerfile",
                    "docker-compose.yml",
                    "docker-compose.yaml",
                    "Vagrantfile",
                    "Jenkinsfile",
                    "Procfile",
                    "Heroku.yml",
                    ".travis.yml",
                    ".gitlab-ci.yml",
                    "azure-pipelines.yml",
                    "terraform.tf",
                    "main.tf",
                    "variables.tf",
                    "outputs.tf",
                    "ansible.yml",
                    "playbook.yml",
                    "inventory.ini",
                    "nginx.conf",
                    "httpd.conf",
                    "apache.conf",
                    "kubernetes.yml",
                    "k8s.yml",
                    "deployment.yml",
                    "service.yml",
                    "helm-chart.yml",
                    "values.yml",
                ],
            },
        }

    def classify_file(self, filepath):
        """Classify a single file into one of the four categories"""
        filename = filepath.split("/")[-1]
        path_lower = filepath.lower()
        filename_lower = filename.lower()

        for category, patterns in self.file_patterns.items():
            # Check file extensions
            if "extensions" in patterns:
                for ext in patterns["extensions"]:
                    if filepath.endswith(ext):
                        return category

            # Check path patterns
            if "paths" in patterns:
                for path_pattern in patterns["paths"]:
                    if path_pattern in path_lower:
                        return category

            # Check specific filenames
            if "filenames" in patterns:
                for pattern in patterns["filenames"]:
                    if "*" in pattern:
                        # Handle wildcard patterns
                        import fnmatch

                        if fnmatch.fnmatch(filename_lower, pattern.lower()):
                            return category
                    elif filename_lower == pattern.lower():
                        return category

            # Check keywords
            if "keywords" in patterns:
                for keyword in patterns["keywords"]:
                    if keyword in filename_lower or keyword in path_lower:
                        return category

        # Default to other if no other category matches
        return "Others"


def re_classify_files(json_file_path):
    """Re-classify files in the given JSON file."""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}", file=sys.stderr)
        return None

    classifier = GitHubFileClassifier()
    # Check each commit entry
    for sha, commit_data in tqdm(data.items()):
        files = commit_data.get("Files")

        # Check if Files is null, empty list, or missing
        if files is not None and len(files) > 0:
            for index, file in enumerate(files):
                data[sha]["Files"][index]["category"] = classifier.classify_file(file["filename"])

    try:
        # Seek to beginning and truncate file
        with open(json_file_path, "r+", encoding="utf-8") as f:
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
    except Exception as e:
        print(f"❌ Error writing back to file: {e}", file=sys.stderr)


def main():
    path = Path(__file__).parent
    files = list(Path((f"{path}/repo_data")).iterdir())

    for file in files:
        print(f"\n✅ Re-Classifying file: {file}")
        re_classify_files(file)


if __name__ == "__main__":
    sys.exit(main())
