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

class TestFileCounter:
    def __init__(self):
        # Define test file patterns by language/framework
        self.test_patterns = {
            "Python": {
                "extensions": [".py"],
                "filename_patterns": [
                    r"test_.*\.py$",
                    r".*_test\.py$", 
                    r".*tests\.py$",
                    r"test.*\.py$"
                ],
                "directory_patterns": ["test", "tests", "testing"],
            },
            "JavaScript/TypeScript": {
                "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs"],
                "filename_patterns": [
                    r".*\.test\.(js|ts|jsx|tsx|mjs)$",
                    r".*\.spec\.(js|ts|jsx|tsx|mjs)$",
                    r"test.*\.(js|ts|jsx|tsx|mjs)$"
                ],
                "directory_patterns": ["test", "tests", "__tests__", "spec", "specs"],
            },
            "Java": {
                "extensions": [".java"],
                "filename_patterns": [
                    r".*Test\.java$",
                    r".*Tests\.java$",
                    r"Test.*\.java$"
                ],
                "directory_patterns": ["test", "tests", "src/test"],
            },
            "Go": {
                "extensions": [".go"],
                "filename_patterns": [
                    r".*_test\.go$"
                ],
                "directory_patterns": [],
            },
            "Ruby": {
                "extensions": [".rb"],
                "filename_patterns": [
                    r".*_spec\.rb$",
                    r".*_test\.rb$",
                    r"spec_.*\.rb$",
                    r"test_.*\.rb$"
                ],
                "directory_patterns": ["test", "tests", "spec", "specs"],
            },
            "C#": {
                "extensions": [".cs"],
                "filename_patterns": [
                    r".*\.Tests\.cs$",
                    r".*Test\.cs$",
                    r".*Tests\.cs$",
                    r"Test.*\.cs$"
                ],
                "directory_patterns": ["test", "tests", "Test", "Tests"],
            },
            "PHP": {
                "extensions": [".php"],
                "filename_patterns": [
                    r".*Test\.php$",
                    r".*_test\.php$",
                    r"test_.*\.php$"
                ],
                "directory_patterns": ["test", "tests", "Test", "Tests"],
            },
            "Rust": {
                "extensions": [".rs"],
                "filename_patterns": [
                    r".*_test\.rs$",
                    r"test_.*\.rs$"
                ],
                "directory_patterns": ["tests"],
            },
            "Swift": {
                "extensions": [".swift"],
                "filename_patterns": [
                    r".*Test\.swift$",
                    r".*Tests\.swift$"
                ],
                "directory_patterns": ["test", "tests", "Test", "Tests"],
            }
        }

        self.test_files = defaultdict(list)
        self.total_test_files = 0
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
            self.temp_dir = tempfile.mkdtemp(prefix="test_analysis_")

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

    def is_test_file(self, file_path):
        """Determine if a file is a test file and return its category."""
        file_path = Path(file_path)
        filename = file_path.name
        extension = file_path.suffix.lower()

        # Check each test pattern category
        for category, patterns in self.test_patterns.items():
            # Check by extension first
            if extension in patterns.get("extensions", []):
                # Check filename patterns
                for pattern in patterns.get("filename_patterns", []):
                    if re.match(pattern, filename, re.IGNORECASE):
                        return category
                
                # Check directory context
                if self._check_directory_context(file_path, patterns.get("directory_patterns", [])):
                    return category

        return None

    def _check_directory_context(self, file_path, directory_patterns):
        """Check if file is in a directory that suggests test context."""
        if not directory_patterns:
            return False

        path_parts = [part.lower() for part in file_path.parts]
        return any(dir_pattern.lower() in path_parts for dir_pattern in directory_patterns)

    def scan_directory(self, directory):
        """Scan directory recursively for test files."""
        directory = Path(directory)

        if not directory.exists():
            print(f"Error: Directory '{directory}' does not exist.")
            return

        print(f"🔍 Scanning directory: {directory.absolute()}")
        print("-" * 50)

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and common non-source directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["node_modules", "__pycache__", ".git", "venv", "env", "target", "build", "dist", "vendor"]
            ]

            for file in files:
                if file.startswith("."):
                    continue

                file_path = Path(root) / file
                self.total_files_scanned += 1
                category = self.is_test_file(file_path)

                if category:
                    relative_path = file_path.relative_to(directory)
                    self.test_files[category].append(
                        {
                            "path": str(relative_path),
                            "size": (
                                file_path.stat().st_size if file_path.exists() else 0
                            ),
                        }
                    )
                    self.total_test_files += 1

    def print_results(self, source_info=""):
        """Print the results in a formatted way."""
        if self.total_test_files == 0:
            print("No test files found in the specified directory.")
            print(f"Total files scanned: {self.total_files_scanned}")
            return

        print(f"\n📊 Test File Analysis Results")
        if source_info:
            print(f"Source: {source_info}")
        print("=" * 60)
        print(f"Total files scanned: {self.total_files_scanned}")
        print(f"Total test files found: {self.total_test_files}")
        test_percentage = (self.total_test_files / self.total_files_scanned) * 100 if self.total_files_scanned > 0 else 0
        print(f"Test coverage ratio: {test_percentage:.1f}% of files are test files")
        print()

        # Sort categories by file count (descending)
        sorted_categories = sorted(
            self.test_files.items(), key=lambda x: len(x[1]), reverse=True
        )

        for category, files in sorted_categories:
            count = len(files)
            percentage = (count / self.total_test_files) * 100

            print(f"🧪 {category}")
            print(f"   Files: {count} ({percentage:.1f}%)")
            print()

    def export_json(self, output_file, source_info=""):
        """Export results to JSON file."""
        
        results = {
            "source": source_info,
            "total_files_scanned": self.total_files_scanned,
            "total_test_files": self.total_test_files,
            "categories": {},
        }

        for category, files in self.test_files.items():
            results["categories"][category] = {
                "count": len(files),
                "files": files,
                "total_size": sum(f["size"] for f in files),
            }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results exported to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Count and categorize test files in repositories",
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
        help="Directory path or GitHub repository URL to analyze",
    )
    parser.add_argument("--json", help="Export results to JSON file")

    args = parser.parse_args()

    counter = TestFileCounter()
    source_info = ""

    try:
        # Clone repository
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
        # Cleanup temporary directory if it was created
        counter.cleanup_temp_dir()


if __name__ == "__main__":
    exit(main())
