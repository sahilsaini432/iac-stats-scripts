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

GITHUB_TOKEN = None


class FileData:
    def __init__(self, fileinfo):
        self.filename = fileinfo["filename"]
        self.additions = fileinfo["additions"]
        self.deletions = fileinfo["deletions"]
        self.category = None

    def to_dict(self, GitHubFileClassifier):
        total_lines_changed = self.additions + self.deletions
        return {
            "filename": self.filename,
            "lines_changed": total_lines_changed,
            "category": GitHubFileClassifier.classify_file(self.filename),
        }


class GitHubFileClassifier:
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

        # Default to development if no other category matches
        return "Development"

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


def find_null_files_entries(json_file_path):
    """Find all SHA entries with null or empty Files."""
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

    null_files_entries = []

    # Check each commit entry
    for sha, commit_data in data.items():
        files = commit_data.get("Files")

        # Check if Files is null, empty list, or missing
        if files is None or not files:
            null_files_entries.append({"sha": sha})

    return null_files_entries


def parse_github_url(url):
    """Parse GitHub URL to extract owner and repo."""
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+)/?",
        r"git@github\.com:([^/]+)/([^/]+)\.git",
        r"([^/]+)/([^/]+)",  # Simple format: owner/repo
    ]

    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            owner, repo = match.groups()
            if repo.endswith(".git"):
                repo = repo.rstrip(".git")

            return owner, repo

    raise ValueError(f"Invalid GitHub URL format: {url}")


def classify_file(self, filepath):
    print(filepath)
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

    # Default to development if no other category matches
    return "Development"


def get_commit_changed_files(owner, repo, sha):
    global GITHUB_TOKEN
    """Get files changed in a specific commit."""
    headers = {}
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    githubClassifier = GitHubFileClassifier()
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            commit_data = resp.json()
            files_info = commit_data.get("files", [])
            if len(files_info) == 0:
                return None
            files_changed = [FileData(fileinfo).to_dict(githubClassifier) for fileinfo in files_info]
            return files_changed
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Find SHA entries with null or empty Files in JSON commit data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("json_file", help="JSON file to analyze")
    parser.add_argument("repository", help="GitHub repository in format 'owner/repo' or full GitHub URL")

    args = parser.parse_args()

    # Find entries with null files
    null_entries = find_null_files_entries(args.json_file)
    # Display results
    print(f"📊 Analysis of {args.json_file}")
    print(f"Found {len(null_entries)} SHA entries with null/empty Files")

    if null_entries is None:
        return 1

    env_path = Path(".env")
    load_dotenv(dotenv_path=env_path)
    global GITHUB_TOKEN
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    owner, repo = parse_github_url(args.repository)

    try:
        with open(args.json_file, "r+", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {args.json_file}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Error reading file: {e}", file=sys.stderr)
        return None

    total_updated = 0
    for entry in tqdm(null_entries):
        sha = entry["sha"]
        files_changed = get_commit_changed_files(owner, repo, sha)
        if files_changed is not None:
            data[sha]["Files"] = files_changed
            total_updated += 1

    # Add this after your processing loop, before the display results
    try:
        # Seek to beginning and truncate file
        with open(args.json_file, "r+", encoding="utf-8") as f:
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
            print(f"✅ Updated {total_updated} entries in {args.json_file}")
    except Exception as e:
        print(f"❌ Error writing back to file: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
