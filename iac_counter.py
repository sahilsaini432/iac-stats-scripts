#!/usr/bin/env python3

import os
import json
import argparse
import tempfile
import shutil
import subprocess
import re
from collections import defaultdict
from pathlib import Path
import yaml

class IaCCounter:
    def __init__(self):
        # Define IaC file patterns and their categories
        self.iac_patterns = {
            "Terraform": {
                "extensions": [".tf", ".tfvars", ".tfstate"],
                "filenames": ["terraform.tfvars", "terraform.tfstate.backup"],
                "directories": ["terraform", ".terraform"],
            },
            "Kubernetes": {
                "extensions": [".yaml", ".yml"],
                "filenames": [
                    "deployment.yaml",
                    "service.yaml",
                    "configmap.yaml",
                    "secret.yaml",
                ],
                "directories": ["k8s", "kubernetes", "manifests"],
                "keywords": ["apiVersion:", "kind:", "metadata:", "spec:"],
            }
        }

        self.file_stats = defaultdict(list)
        self.total_files = 0
        self.total_files_scanned = 0
        self.temp_dir = None

    def is_github_url(self, url):
        """Check if the provided URL is a GitHub repository URL."""
        github_patterns = [
            r"https://github\.com/[\w\-\.]+/[\w\-\.]+/?",
            r"git@github\.com:[\w\-\.]+/[\w\-\.]+\.git",
            r"https://github\.com/[\w\-\.]+/[\w\-\.]+\.git",
        ]
        return any(re.match(pattern, url) for pattern in github_patterns)

    def normalize_github_url(self, url):
        """Normalize GitHub URL to HTTPS format for cloning."""
        # Remove trailing slash and .git if present
        url = url.rstrip("/").rstrip(".git")

        # Convert SSH to HTTPS
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/")

        # Ensure it starts with https://
        if not url.startswith("https://"):
            url = "https://github.com/" + url

        return url + ".git"

    def clone_repository(self, github_url):
        """Clone GitHub repository to a temporary directory."""
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="iac_analysis_")

            # Normalize the URL
            clone_url = self.normalize_github_url(github_url)

            print(f"🔄 Cloning repository: {clone_url}")
            print(f"📁 Temporary directory: {self.temp_dir}")

            # Clone the repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, self.temp_dir],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, result.stderr
                )

            print("✅ Repository cloned successfully")
            return self.temp_dir

        except subprocess.TimeoutExpired:
            print("❌ Error: Repository cloning timed out (5 minutes)")
            self.cleanup_temp_dir()
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Error cloning repository: {e.stderr}")
            self.cleanup_temp_dir()
            return None
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.cleanup_temp_dir()
            return None

    def cleanup_temp_dir(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️  Warning: Could not clean up temporary directory: {e}")

    def is_iac_file(self, file_path):
        """Determine if a file is an IaC file and return its category."""
        file_path = Path(file_path)
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()

        # Check each IaC category
        for category, patterns in self.iac_patterns.items():
            # Check by filename
            if filename in [f.lower() for f in patterns.get("filenames", [])]:
                return category

            # Check by extension
            if extension in patterns.get("extensions", []):
                # For files with common extensions, check content or directory
                if extension in [".yaml", ".yml", ".json"]:
                    if self._check_content_keywords(
                        file_path, patterns.get("keywords", [])
                    ):
                        return category
                    if self._check_directory_context(
                        file_path, patterns.get("directories", [])
                    ):
                        return category
                else:
                    return category

        return None

    def _check_content_keywords(self, file_path, keywords):
        """Check if file content contains specific keywords."""
        if not keywords:
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().lower()
                return any(keyword.lower() in content for keyword in keywords)
        except (UnicodeDecodeError, PermissionError, FileNotFoundError):
            return False

    def _check_directory_context(self, file_path, directories):
        """Check if file is in a directory that suggests IaC context."""
        if not directories:
            return False

        path_parts = [part.lower() for part in file_path.parts]
        return any(dir_name.lower() in path_parts for dir_name in directories)

    def scan_directory(self, directory):
        """Scan directory recursively for IaC files."""
        directory = Path(directory)

        if not directory.exists():
            print(f"Error: Directory '{directory}' does not exist.")
            return

        print(f"🔍 Scanning directory: {directory.absolute()}")
        print("-" * 50)

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and common non-IaC directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["node_modules", "__pycache__", ".git", "venv", "env"]
            ]

            for file in files:
                if file.startswith("."):
                    continue

                file_path = Path(root) / file
                self.total_files_scanned += 1
                category = self.is_iac_file(file_path)

                if category:
                    relative_path = file_path.relative_to(directory)
                    self.file_stats[category].append(
                        {
                            "path": str(relative_path),
                        }
                    )
                    self.total_files += 1

    def print_results(self, source_info=""):
        """Print the results in a formatted way."""
        if self.total_files == 0:
            print("No IaC files found in the specified directory.")
            return

        print(f"\n📊 IaC File Analysis Results")
        if source_info:
            print(f"Source: {source_info}")
        print("=" * 60)
        print(f"Total files scanned: {self.total_files_scanned}")
        print(f"Total IaC files found: {self.total_files}")
        print()

        # Sort categories by file count (descending)
        sorted_categories = sorted(
            self.file_stats.items(), key=lambda x: len(x[1]), reverse=True
        )

        for category, files in sorted_categories:
            count = len(files)
            percentage = (count / self.total_files) * 100

            print(f"🔧 {category}")
            print(f"   Files: {count} ({percentage:.1f}%)")
            print()

    def export_json(self, output_file, source_info=""):
        """Export results to JSON file."""
        results = {
            "source": source_info,
            "total_files_scanned": self.total_files_scanned,
            "total_iac_files": self.total_files,
            "categories": {},
        }

        for category, files in self.file_stats.items():
            results["categories"][category] = {
                "count": len(files),
            }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results exported to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Count and categorize Infrastructure as Code files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Scan current directory
  %(prog)s /path/to/project                   # Scan local directory
  %(prog)s https://github.com/user/repo       # Analyze GitHub repository
  %(prog)s user/repo                          # Analyze GitHub repository (short format)
  %(prog)s --json results.json .              # Export to JSON
        """,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        help="GitHub repository URL to analyze",
    )
    parser.add_argument("--json", help="Export results to JSON file")

    args = parser.parse_args()

    counter = IaCCounter()
    source_info = ""

    try:
        # Clone Repo
        source_info = args.source
        directory = counter.clone_repository(args.source)
        if directory is None:
            return 1

        # Scan the directory
        counter.scan_directory(directory)

        # Display results
        counter.print_results(source_info)

        # Export results
        if args.json:
            counter.export_json(args.json, source_info)

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
    finally:
        # Cleanup temporary directory unless --keep-temp is specified
        counter.cleanup_temp_dir()


if __name__ == "__main__":
    exit(main())
