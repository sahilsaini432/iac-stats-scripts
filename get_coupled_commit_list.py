import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv
from re_classifier import GitHubFileClassifier

NUM_COMMITS_PER_REPO = 5
CATEGORIES = ["Infrastructure", "Build"]  # "Test", "Build"
REPO_NAMES = {
    "helicone": "helicone/helicone",
    "weaviate": "weaviate/weaviate",
    "beta9": "beam-cloud/beta9",
    "trieve": "devflowinc/trieve",
    "anything-llm": "Mintplex-Labs/anything-llm",
    "n8n": "n8n-io/n8n",
    "terraform-genai-doc-summarization": "GoogleCloudPlatform/terraform-genai-doc-summarization",
    "nitric": "nitrictech/nitric",
    "Kuzco": "RoseSecurity/Kuzco",
    "tfmcp": "nwiizo/tfmcp",
    "immich": "immich-app/immich",
    "coder": "coder/coder",
    "beam": "apache/beam",
    "digger": "diggerhq/digger",
    "gritql": "honeycombio/gritql",
    "quickwit": "quickwit-oss/quickwit",
    "twenty": "twentyhq/twenty",
    "windmill": "windmill-labs/windmill",
    "sequin": "sequinstream/sequin",
    "homelab": "khuedoan/homelab",
    "steampipe": "turbot/steampipe"
}


def parse_json_files():
    json_files = os.listdir("repo_data")
    project_commit_list = []
    outstanding_commits = 0

    for json_file in json_files:
        json_file_path = os.path.join("repo_data", json_file)

        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON file {json_file_path}: {e}")
        except FileNotFoundError:
            print(f"❌ File not found: {json_file_path}")
        except Exception as e:
            print(f"❌ Error reading file {json_file_path}: {e}")

        repo_commits = 0
        for commit_sha, commit_data in data.items():
            if repo_commits >= NUM_COMMITS_PER_REPO + outstanding_commits:
                outstanding_commits = 0
                break
            has_infrastructure = False
            has_other_category = False
            if commit_data["Files"] is None:
                continue
            for file in commit_data["Files"]:
                if file["category"] == CATEGORIES[0]:
                    has_infrastructure = True
                if file["category"] == CATEGORIES[1]:
                    has_other_category = True
                if has_infrastructure and has_other_category:
                    repo_commits += 1
                    project_commit_list.append((REPO_NAMES[json_file[:-5]], commit_sha))
                    break
        if repo_commits < NUM_COMMITS_PER_REPO:
            outstanding_commits = NUM_COMMITS_PER_REPO - repo_commits

    return project_commit_list


def fetch_commit_data(repo, commit_hash, token):
    """Fetch commit data from GitHub API"""
    url = f"https://api.github.com/repos/{repo}/commits/{commit_hash}"
    headers = {
        "Authorization": f"token {token}",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {repo}/{commit_hash}: {e}")
        return None


def clean_message(message):
    return (message.replace("    ", "")
            .replace("   ", "")
            .replace("  ", " ")
            .replace("\t", "")
            .replace("--", "")
            .replace("\n\n", "\n")
            .replace("\n \n", "\n"))

def extract_commit_info(commit_data):
    """Extract relevant information from commit data"""
    if not commit_data:
        return None

    classifier = GitHubFileClassifier()

    files_info = []
    for file in commit_data.get('files', []):
        filename = file.get('filename')
        category = classifier.classify_file(filename)
        if category in CATEGORIES:
            patch = file.get('patch', '')
            patch = clean_message(patch)
            filename = filename.split("/")[-1]

            files_info.append({
                'filename': filename,
                'status': file.get('status'),
                #'patch': patch[:300]  # First 300 chars of patch
            })

    commit_message = commit_data.get('commit', {}).get('message', '')
    commit_message = clean_message(commit_message)

    return {
        'message': commit_message,
        'files': files_info,
    }


def main():
    commits_list = parse_json_files()
    all_commit_data = []
    env_path = Path(".env")
    load_dotenv(dotenv_path=env_path)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    print(f"Found {len(commits_list)} commits to fetch")
    print("Fetching commit data...")

    previous_repo = ""
    for i, (repo, commit_hash) in enumerate(commits_list, 1):
        if not previous_repo or repo != previous_repo:
            previous_repo = repo
            print(f"Fetching {repo}...")

        commit_data = fetch_commit_data(repo, commit_hash, GITHUB_TOKEN)
        if commit_data:
            info = extract_commit_info(commit_data)
            if info:
                all_commit_data.append(info)

    # Save to JSON file
    output_file = f"commit_data_{CATEGORIES[0].lower()}_{CATEGORIES[1].lower()}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_commit_data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"\nDone! Fetched {len(all_commit_data)} commits")
    print(f"Data saved to {output_file}")


if __name__ == "__main__":
    main()
