import requests
import time
from pathlib import Path
import argparse
from dotenv import load_dotenv
import re
import os
from pprint import pprint as _print

class GitHubFileClassifier:
    def __init__(self):
        self.file_patterns = {
            'Development': {
                'extensions': ['.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.cpp', '.c', '.h', '.cs', 
                             '.php', '.rb', '.go', '.rs', '.kt', '.swift', '.scala', '.clj', '.hs', '.ml', 
                             '.r', '.m', '.sql', '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte'],
                'paths': ['src/', 'lib/', 'app/', 'components/', 'pages/', 'views/', 'controllers/', 
                         'models/', 'services/', 'utils/', 'helpers/', 'core/', 'common/', 'shared/'],
                'filenames': ['index.js', 'main.js', 'app.js', 'server.js', 'client.js', 'index.ts', 
                            'main.ts', 'app.py', 'main.py', '__init__.py']
            },
            
            'Test': {
                'extensions': ['.test.js', '.test.ts', '.spec.js', '.spec.ts', '.test.py', '.spec.py'],
                'paths': ['test/', 'tests/', '__tests__/', 'spec/', 'specs/', '.pytest_cache/', 
                         'cypress/', 'e2e/', 'testing/'],
                'filenames': ['jest.config.js', 'jest.config.json', 'pytest.ini', 'conftest.py', 
                            'karma.conf.js', 'protractor.conf.js', 'cypress.json'],
                'keywords': ['test', 'spec', 'mock', 'fixture', 'coverage']
            },
            
            'Build': {
                'extensions': ['.json', '.xml', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf'],
                'paths': ['build/', 'dist/', 'out/', 'target/', 'bin/', 'release/', 'scripts/', 
                         'tools/', 'config/', 'configs/'],
                'filenames': [
                    'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                    'Makefile', 'makefile', 'CMakeLists.txt', 'build.gradle', 'pom.xml',
                    'setup.py', 'setup.cfg', 'pyproject.toml', 'requirements.txt', 'Pipfile', 'poetry.lock',
                    'Cargo.toml', 'Cargo.lock', 'go.mod', 'go.sum',
                    'webpack.config.js', 'rollup.config.js', 'vite.config.js', 'tsconfig.json',
                    'babel.config.js', '.babelrc', '.eslintrc.js', '.eslintrc.json', 'prettier.config.js',
                    'gulpfile.js', 'gruntfile.js', 'build.xml', 'build.yml', 'build.yaml'
                ]
            },
            
            'Infrastructure': {
                'extensions': ['.dockerfile', '.tf', '.hcl', '.sh', '.bat', '.ps1', '.cmd'],
                'paths': ['docker/', 'k8s/', 'kubernetes/', 'terraform/', 'ansible/', 'puppet/', 
                         'chef/', 'vagrant/', 'helm/', 'deploy/', 'deployment/', 'infra/', 
                         'infrastructure/', 'ops/', 'devops/', '.github/', '.gitlab/', 'ci/', '.circleci/'],
                'filenames': [
                    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
                    'Vagrantfile', 'Jenkinsfile', 'Procfile', 'Heroku.yml',
                    '.travis.yml', '.gitlab-ci.yml', 'azure-pipelines.yml',
                    'terraform.tf', 'main.tf', 'variables.tf', 'outputs.tf',
                    'ansible.yml', 'playbook.yml', 'inventory.ini',
                    'nginx.conf', 'httpd.conf', 'apache.conf',
                    'kubernetes.yml', 'k8s.yml', 'deployment.yml', 'service.yml',
                    'helm-chart.yml', 'values.yml'
                ]
            }
        }

    def classify_file(self, filepath):
        """Classify a single file into one of the four categories"""
        filename = filepath.split('/')[-1]
        path_lower = filepath.lower()
        filename_lower = filename.lower()
        
        for category, patterns in self.file_patterns.items():
            # Check file extensions
            if 'extensions' in patterns:
                for ext in patterns['extensions']:
                    if filepath.endswith(ext):
                        return category
            
            # Check path patterns
            if 'paths' in patterns:
                for path_pattern in patterns['paths']:
                    if path_pattern in path_lower:
                        return category
            
            # Check specific filenames
            if 'filenames' in patterns:
                for pattern in patterns['filenames']:
                    if '*' in pattern:
                        # Handle wildcard patterns
                        import fnmatch
                        if fnmatch.fnmatch(filename_lower, pattern.lower()):
                            return category
                    elif filename_lower == pattern.lower():
                        return category
            
            # Check keywords
            if 'keywords' in patterns:
                for keyword in patterns['keywords']:
                    if keyword in filename_lower or keyword in path_lower:
                        return category
        
        # Default to development if no other category matches
        return 'development'

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
            "category": GitHubFileClassifier.classify_file(self.filename)
        }

class CommitData:
    def __init__(self, commit):
        self.sha = commit["sha"]
        self.Author = commit["commit"]["author"]["name"]
        self.Date = commit["commit"]["author"]["date"]
        self.Files = []  # To be populated later with FileData objects
    
    def to_dict(self):
        return {
            "sha": self.sha,
            "Author": self.Author,
            "Date": self.Date,
            "Files": self.Files
        }

def write_data_to_json(data, filename):
    """Write data to a JSON file with proper formatting."""
    import json
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Data successfully written to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error writing to JSON file {filename}: {str(e)}")
        return False

GITHUB_TOKEN = None

def parse_github_url(url):
    """Parse GitHub URL to extract owner and repo."""
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+)/?",
        r"git@github\.com:([^/]+)/([^/]+)\.git",
        r"([^/]+)/([^/]+)"  # Simple format: owner/repo
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            owner, repo = match.groups()
            return owner, repo.rstrip(".git")
    
    raise ValueError(f"Invalid GitHub URL format: {url}")

def get_all_commits(owner, repo):
    global GITHUB_TOKEN
    """Get all commits for a GitHub repository with pagination."""
    headers = {}
    headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    base_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    all_commits = []
    page = 1
    per_page = 100  # Maximum allowed by GitHub API
    
    print(f"🔍 Fetching commits from {owner}/{repo}...")
    
    while True:
        # Add pagination parameters
        url = f"{base_url}?page={page}&per_page={per_page}"
        
        try:
            resp = requests.get(url, headers=headers)
            
            if resp.status_code == 200:
                commits = resp.json()
                
                # If no commits returned, we've reached the end
                if not commits:
                    print("no commits found")
                    break
                
                all_commits.extend(commits)
                print(f"📄 Fetched page {page} - {len(commits)} commits (Total: {len(all_commits)})")
                
                # If we got fewer commits than per_page, we're on the last page
                if len(commits) < per_page:
                    break
                
                page += 1
                # Small delay to be respectful to the API
                time.sleep(0.1)
            else:
                print(f"❌ Failed to fetch commits: {resp.status_code} - {resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
    
    print(f"✅ Successfully fetched {len(all_commits)} total commits")
    
    print("Processing commit data...")
    # all commits are fetched
    data_we_need = {}
    for commit in all_commits:
        commit_obj = CommitData(commit)
        
        # get all the files changed in this commit
        files_changed = get_commit_changed_files(owner, repo, commit_obj.sha)
        commit_obj.Files = files_changed
        data_we_need[commit_obj.sha] = commit_obj.to_dict()

    # Write the processed data to a JSON file
    write_data_to_json(data_we_need, f"{repo}.json")

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
            files_changed = [FileData(fileinfo).to_dict(githubClassifier) for fileinfo in files_info]
            return files_changed
        else:
            print(f"❌ Failed to fetch commit {sha}: {resp.status_code} - {resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None

def main():
    env_path = Path(".env")
    load_dotenv(dotenv_path=env_path)

    global GITHUB_TOKEN
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    parser = argparse.ArgumentParser(
        description="Get contributor statistics for a GitHub repository",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "repository",
        help="GitHub repository in format 'owner/repo' or full GitHub URL"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse the repository URL
        owner, repo = parse_github_url(args.repository)
        get_all_commits(owner, repo)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())