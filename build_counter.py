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

class BuildFileCounter:
    def __init__(self):
        # Define build file patterns by language/framework/tool
        self.build_patterns = {
            "Python": {
                "filenames": [
                    "setup.py", "setup.cfg", "pyproject.toml", "requirements.txt",
                    "requirements-dev.txt", "dev-requirements.txt", "Pipfile",
                    "Pipfile.lock", "poetry.lock", "conda.yml", "environment.yml",
                    "tox.ini", "pytest.ini", "mypy.ini", "flake8.cfg", ".flake8"
                ],
                "filename_patterns": [
                    r"requirements.*\.txt$",
                    r".*requirements\.txt$",
                ],
            },
            "JavaScript/Node.js": {
                "filenames": [
                    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                    "webpack.config.js", "webpack.config.ts", "rollup.config.js",
                    "vite.config.js", "vite.config.ts", "gulpfile.js", "gruntfile.js",
                    "babel.config.js", "babel.config.json", ".babelrc", ".babelrc.js",
                    "tsconfig.json", "jsconfig.json", "next.config.js", "nuxt.config.js",
                    "vue.config.js", "angular.json", ".eslintrc.js", ".eslintrc.json",
                    "prettier.config.js", ".prettierrc", "jest.config.js", "vitest.config.js"
                ],
                "filename_patterns": [
                    r"webpack\..*\.js$",
                    r"rollup\..*\.js$",
                    r"vite\..*\.(js|ts)$",
                    r".*\.config\.(js|ts|json)$",
                ],
            },
            "Java/Maven": {
                "filenames": [
                    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
                    "gradle.properties", "gradlew", "gradlew.bat", "maven-wrapper.properties"
                ],
                "filename_patterns": [
                    r".*\.gradle$",
                    r".*\.gradle\.kts$",
                ],
            },
            "C/C++": {
                "filenames": [
                    "Makefile", "makefile", "CMakeLists.txt", "configure.ac",
                    "configure.in", "Makefile.am", "Makefile.in", "conanfile.txt",
                    "conanfile.py", "vcpkg.json", "meson.build", "BUILD", "BUILD.bazel"
                ],
                "filename_patterns": [
                    r"Makefile\..*$",
                    r".*\.mk$",
                    r".*\.cmake$",
                ],
            },
            "C#/.NET": {
                "filenames": [
                    "Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props",
                    "global.json", "nuget.config", "NuGet.Config", "packages.config",
                    ".editorconfig"
                ],
                "filename_patterns": [
                    r".*\.csproj$",
                    r".*\.vbproj$",
                    r".*\.fsproj$",
                    r".*\.sln$",
                    r".*\.props$",
                    r".*\.targets$",
                ],
            },
            "Go": {
                "filenames": [
                    "go.mod", "go.sum", "go.work", "go.work.sum", "Gopkg.toml",
                    "Gopkg.lock", "vendor.json", "glide.yaml", "glide.lock"
                ],
            },
            "Rust": {
                "filenames": [
                    "Cargo.toml", "Cargo.lock", "build.rs", "rust-toolchain",
                    "rust-toolchain.toml"
                ],
            },
            "Ruby": {
                "filenames": [
                    "Gemfile", "Gemfile.lock", "Rakefile", ".ruby-version",
                    ".rvmrc", "gems.rb", "gems.locked"
                ],
                "filename_patterns": [
                    r".*\.gemspec$",
                ],
            },
            "PHP": {
                "filenames": [
                    "composer.json", "composer.lock", "phpunit.xml", "phpunit.xml.dist",
                    "build.xml", "phing.xml", "box.json"
                ],
            },
            "Swift": {
                "filenames": [
                    "Package.swift", "Package.resolved", "Cartfile", "Cartfile.resolved",
                    "Podfile", "Podfile.lock", "project.pbxproj", "xcshareddata"
                ],
                "filename_patterns": [
                    r".*\.xcodeproj$",
                    r".*\.xcworkspace$",
                ],
            },
            "Scala/SBT": {
                "filenames": [
                    "build.sbt", "project/build.properties", "project/plugins.sbt"
                ],
                "filename_patterns": [
                    r".*\.sbt$",
                ],
            },
            "Docker/Containers": {
                "filenames": [
                    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                    "docker-compose.override.yml", ".dockerignore", "Containerfile"
                ],
                "filename_patterns": [
                    r"Dockerfile\..*$",
                    r"docker-compose\..*\.ya?ml$",
                ],
            },
            "CI/CD": {
                "filenames": [
                    ".travis.yml", "appveyor.yml", "circle.yml", "codecov.yml",
                    ".codecov.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml",
                    "buildspec.yml", "cloudbuild.yaml", "cloudbuild.yml",
                    "Jenkinsfile", ".github/workflows", ".gitlab-ci.yml"
                ],
                "filename_patterns": [
                    r"\.travis\.ya?ml$",
                    r"\.github/workflows/.*\.ya?ml$",
                    r"\.circleci/.*\.ya?ml$",
                ],
                "directory_patterns": [".github/workflows", ".circleci"],
            },
            "Build Tools": {
                "filenames": [
                    "Taskfile.yml", "Taskfile.yaml", "justfile", "dodo.py",
                    "invoke.yaml", "invoke.yml", "noxfile.py", "fabfile.py"
                ],
            },
            "Linting/Formatting": {
                "filenames": [
                    ".editorconfig", ".gitignore", ".gitattributes", ".pre-commit-config.yaml",
                    ".clang-format", ".clang-tidy", "pyproject.toml", "setup.cfg",
                    "tox.ini", ".pylintrc", "mypy.ini", ".isort.cfg", ".yapfrc",
                    ".black", "ruff.toml", ".ruff.toml"
                ],
                "filename_patterns": [
                    r"\..*rc$",
                    r"\..*ignore$",
                ],
            }
        }

        self.build_files = defaultdict(list)
        self.total_build_files = 0
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
            self.temp_dir = tempfile.mkdtemp(prefix="build_analysis_")

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

    def is_build_file(self, file_path):
        """Determine if a file is a build file and return its category."""
        file_path = Path(file_path)
        filename = file_path.name
        filename_lower = filename.lower()

        # Check each build pattern category
        for category, patterns in self.build_patterns.items():
            # Check exact filename matches
            if filename in patterns.get("filenames", []) or filename_lower in [f.lower() for f in patterns.get("filenames", [])]:
                return category
            
            # Check filename patterns
            for pattern in patterns.get("filename_patterns", []):
                if re.match(pattern, filename, re.IGNORECASE):
                    return category
            
            # Check directory context
            if self._check_directory_context(file_path, patterns.get("directory_patterns", [])):
                return category

        return None

    def _check_directory_context(self, file_path, directory_patterns):
        """Check if file is in a directory that suggests build context."""
        if not directory_patterns:
            return False

        path_str = str(file_path)
        return any(dir_pattern in path_str for dir_pattern in directory_patterns)

    def scan_directory(self, directory):
        """Scan directory recursively for build files."""
        directory = Path(directory)

        if not directory.exists():
            print(f"Error: Directory '{directory}' does not exist.")
            return

        print(f"🔍 Scanning directory: {directory.absolute()}")
        print("-" * 50)

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and common non-source directories, but keep some important ones
            dirs[:] = [
                d
                for d in dirs
                if not (d.startswith(".") and d not in [".github", ".circleci"])
                and d not in ["node_modules", "__pycache__", "venv", "env", "target", "build", "dist", "vendor"]
            ]

            for file in files:
                # Don't skip hidden files for build files as many are hidden (.eslintrc, etc.)
                file_path = Path(root) / file
                self.total_files_scanned += 1
                category = self.is_build_file(file_path)

                if category:
                    relative_path = file_path.relative_to(directory)
                    self.build_files[category].append(
                        {
                            "path": str(relative_path),
                            "size": (
                                file_path.stat().st_size if file_path.exists() else 0
                            ),
                        }
                    )
                    self.total_build_files += 1

    def print_results(self, source_info=""):
        """Print the results in a formatted way."""
        if self.total_build_files == 0:
            print("No build files found in the specified directory.")
            print(f"Total files scanned: {self.total_files_scanned}")
            return

        print(f"\n📊 Build File Analysis Results")
        if source_info:
            print(f"Source: {source_info}")
        print("=" * 60)
        print(f"Total files scanned: {self.total_files_scanned}")
        print(f"Total build files found: {self.total_build_files}")
        build_percentage = (self.total_build_files / self.total_files_scanned) * 100 if self.total_files_scanned > 0 else 0
        print(f"Build file ratio: {build_percentage:.1f}% of files are build-related")
        print()

        # Sort categories by file count (descending)
        sorted_categories = sorted(
            self.build_files.items(), key=lambda x: len(x[1]), reverse=True
        )

        for category, files in sorted_categories:
            count = len(files)
            total_size = sum(f["size"] for f in files)
            percentage = (count / self.total_build_files) * 100

            print(f"🔧 {category}")
            print(f"   Files: {count} ({percentage:.1f}%)")
            print(f"   Total Size: {self._format_size(total_size)}")

            # Show file paths (limit to first 15 for readability)
            for i, file_info in enumerate(files[:15]):
                print(f"   📄 {file_info['path']}")

            if len(files) > 15:
                print(f"   ... and {len(files) - 15} more files")
            print()

    def _format_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def export_json(self, output_file, source_info=""):
        """Export results to JSON file."""
        build_percentage = (self.total_build_files / self.total_files_scanned) * 100 if self.total_files_scanned > 0 else 0
        
        results = {
            "source": source_info,
            "total_files_scanned": self.total_files_scanned,
            "total_build_files": self.total_build_files,
            "build_file_percentage": round(build_percentage, 1),
            "categories": {},
        }

        for category, files in self.build_files.items():
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
        description="Count and categorize build files in repositories",
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

    counter = BuildFileCounter()
    source_info = ""

    try:
        # Check if source is a GitHub URL or local directory
        if counter.is_github_url(args.source) or ("/" in args.source and not os.path.exists(args.source)):
            # Clone repository
            source_info = args.source
            directory = counter.clone_repository(args.source)
            if directory is None:
                return 1
        else:
            # Use local directory
            directory = args.source
            source_info = f"Local directory: {os.path.abspath(directory)}"

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
