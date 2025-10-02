#!/usr/bin/env python3
import json
import argparse
import os
from collections import defaultdict, Counter
from pathlib import Path

categories = ["Development", "Test", "Build", "Infrastructure"]


class CommitCategoryAnalyzer:
    def __init__(self):
        self.total_commits = 0
        self.commits_by_category = defaultdict(
            set
        )  # Use set to avoid counting same commit multiple times per category
        self.files_by_category = defaultdict(int)
        self.lines_changed_by_category = defaultdict(int)
        self.category_stats = defaultdict(lambda: {"commits": 0, "files": 0, "lines_changed": 0})

    def analyze_json_file(self, json_file_path):
        """Analyze a single JSON file and extract commit statistics."""
        print(f"📊 Analyzing {json_file_path}...")

        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON file {json_file_path}: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ File not found: {json_file_path}")
            return False
        except Exception as e:
            print(f"❌ Error reading file {json_file_path}: {e}")
            return False

        # Reset counters for this file
        self.total_commits = 0
        self.commits_by_category.clear()
        self.files_by_category.clear()
        self.lines_changed_by_category.clear()
        self.category_stats.clear()

        # Process each commit
        for commit_sha, commit_data in data.items():
            files = commit_data.get("Files", [])
            if files is None or len(files) == 0:
                continue  # Skip commits with no files

            self.total_commits += 1

            # Process files in this commit
            commit_categories = set()  # Track categories touched by this commit

            for file_info in files:
                category = file_info.get("category", "Unknown")
                lines_changed = file_info.get("lines_changed", 0)

                # Add this commit to the category
                self.commits_by_category[category].add(commit_sha)
                commit_categories.add(category)

                # Count files and lines changed
                self.files_by_category[category] += 1
                self.lines_changed_by_category[category] += lines_changed

        # Calculate final statistics
        for category in self.commits_by_category:
            self.category_stats[category] = {
                "commits": len(self.commits_by_category[category]),
                "files": self.files_by_category[category],
                "lines_changed": self.lines_changed_by_category[category],
            }

        return True

    def print_summary(self, filename=""):
        """Print a summary of the analysis."""
        if filename:
            print(f"\n📊 Analysis Results for: {filename}")
        else:
            print(f"\n📊 Analysis Results")

        print("=" * 70)
        print(f"Total commits analyzed: {self.total_commits:,}")

        if not self.category_stats:
            print("No categorized data found.")
            return

        print(f"Categories found: {len(self.category_stats)}")
        print()

        # Sort categories by number of commits (descending)
        sorted_categories = sorted(self.category_stats.items(), key=lambda x: x[1]["commits"], reverse=True)

        print("📈 Commits by Category:")
        print(f"{'Category':<20} {'Commits':<10} {'Files':<10} {'Lines Changed':<15} {'% of Commits':<12}")
        print("-" * 70)

        for category, stats in sorted_categories:
            percentage = (stats["commits"] / self.total_commits) * 100 if self.total_commits > 0 else 0
            print(
                f"{category:<20} {stats['commits']:<10,} {stats['files']:<10,} {stats['lines_changed']:<15,} {percentage:<12.1f}%"
            )

        # Show infrastructure-specific details if present
        for category in self.category_stats:
            infra_stats = self.category_stats[category]
            print(f"\n🏗️  {category} Insights:")
            print(f"   • {infra_stats['commits']:,} commits modified {category} files")
            print(f"   • {infra_stats['files']:,} {category} files were changed")
            print(f"   • {infra_stats['lines_changed']:,} total lines changed in {category} files")
            infra_percentage = (infra_stats["commits"] / self.total_commits) * 100
            print(f"   • {infra_percentage:.1f}% of all commits touched {category}")

    def export_summary(self, output_file, source_file=""):
        """Export analysis results to JSON."""
        summary = {
            "source_file": source_file,
            "analysis_date": str(Path().cwd()),
            "total_commits": self.total_commits,
            "total_categories": len(self.category_stats),
            "categories": {},
        }

        for category, stats in self.category_stats.items():
            percentage = (stats["commits"] / self.total_commits) * 100 if self.total_commits > 0 else 0
            summary["categories"][category] = {
                "commits": stats["commits"],
                "files": stats["files"],
                "lines_changed": stats["lines_changed"],
                "percentage_of_commits": round(percentage, 2),
            }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"📄 Summary exported to: {output_file}")
            return True
        except Exception as e:
            print(f"❌ Error writing summary file: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Analyze commit data from JSON files generated by repo_scraper.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("json_files", nargs="+", help="JSON file(s) to analyze (supports wildcards)")

    args = parser.parse_args()

    analyzer = CommitCategoryAnalyzer()

    try:
        # Process each JSON file
        for json_file in args.json_files:
            if not os.path.exists(json_file):
                print(f"⚠️  File not found: {json_file}")
                continue

            fileName = os.path.basename(json_file)
            success = analyzer.analyze_json_file(json_file)
            if success:
                analyzer.print_summary(os.path.basename(json_file))

                # Export summary if requested
                # TODO: Enable this to create a json file with stats
                # analyzer.export_summary(f"{fileName}-stats.json", json_file)

            print()  # Add spacing between files

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
