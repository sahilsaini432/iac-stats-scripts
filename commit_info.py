import requests
import time
import argparse
import re
import os

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

def get_contributors_stats(owner, repo, github_token=None):
    """Get contributor statistics for a GitHub repository."""
    headers = {} 
    
    # for getting total number of contributors
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/contributors"
    
    
    while True:
        resp = requests.get(url, headers=headers)
        print(resp)
        if resp.status_code == 202:
            print("GitHub is generating statistics, retrying in 3 seconds...")
            time.sleep(3)
            continue
        elif resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            print(f"Repository {owner}/{repo} not found.")
            return None
        else:
            print(f"Failed with status code {resp.status_code}: {resp.text}")
            return None

def main():
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
        
        # Get contributor statistics
        stats = get_contributors_stats(owner, repo)
        
        if stats is None:
            print("Failed to fetch contributor stats.")
            return 1
        
        if not stats:
            print("No contributor statistics available for this repository.")
            return 0
        
        # Calculate and display results
        total_commits = sum(contributor["total"] for contributor in stats)
        total_contributors = len(stats)
        
        print(f"\n📊 Contributor Statistics")
        print("=" * 50)
        print(f"Repository: {owner}/{repo}")
        print(f"Total contributors: {total_contributors}")
        print(f"Total commits: {total_commits:,}")
        print()
        
        # Sort contributors by commit count
        stats.sort(key=lambda x: x["total"], reverse=True)
        
        print("🏆 Top Contributors:")
        for i, contributor in enumerate(stats, 1):
            author = contributor["author"]
            username = author["login"]
            commits = contributor["total"]
            percentage = (commits / total_commits) * 100
            
            print(f"{i:2d}. {username:<20} {commits:>6,} commits ({percentage:5.1f}%)")
        
        if len(stats) > 10:
            remaining_commits = sum(c["total"] for c in stats[10:])
            remaining_percentage = (remaining_commits / total_commits) * 100
            print(f"    {'Others':<20} {remaining_commits:>6,} commits ({remaining_percentage:5.1f}%)")
        
        return 0
        
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