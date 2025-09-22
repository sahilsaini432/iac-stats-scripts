import requests
import time
from pathlib import Path
import argparse
from dotenv import load_dotenv
import re
import os
from pprint import pprint as _print

class FileData:
    def __init__(self, fileinfo):
        self.filename = fileinfo["filename"]
        self.additions = fileinfo["additions"]
        self.deletions = fileinfo["deletions"]
        self.changes = fileinfo["changes"]
        self.status = fileinfo["status"]
        
    def to_dict(self):
        return {
            "filename": self.filename,
            "additions": self.additions,
            "deletions": self.deletions,
            "changes": self.changes,
            "status": self.status
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
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            commit_data = resp.json()
            files_info = commit_data.get("files", [])
            files_changed = [FileData(fileinfo).to_dict() for fileinfo in files_info]
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
        print(f"🔍 Analyzing contributors for: {owner}/{repo}")
        
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