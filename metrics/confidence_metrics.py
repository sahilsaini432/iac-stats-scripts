#!/usr/bin/env python3

from ast import Not
import json
import argparse
import os
from collections import defaultdict
from pathlib import Path
import stat


class InfraBuildOverlapAnalyzer:
    def __init__(self):
        self.total_commits = 0

        self.infrastructure_commits = set()
        self.dev_commits = set()
        self.test_commits = set()
        self.build_commits = set()

        self.infra_test_commits = set()
        self.infra_dev_commits = set()
        self.infra_build_commits = set()
        self.dev_test_commits = set()
        self.dev_build_commits = set()
        self.test_build_commits = set()

        self.commit_categories = defaultdict(set)  # Maps commit SHA to set of categories
        self.detailed_stats = {
            "infra_only": set(),
            "build_only": set(),
            "test_only": set(),
            "dev_only": set(),
            # Pairs
            "both_infra_test": set(),
            "both_infra_dev": set(),
            "both_infra_build": set(),
            "both_dev_test": set(),
            "both_dev_build": set(),
            "both_test_build": set(),
        }

    def analyze_json_file(self, json_file_path):
        """Analyze a JSON file for category overlap."""
        print(f"🔍 Analyzing {json_file_path}...")

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

        # Reset counters
        self.total_commits = 0
        self.infrastructure_commits.clear()
        self.build_commits.clear()
        self.test_commits.clear()
        self.dev_commits.clear()

        self.infra_build_commits.clear()
        self.infra_test_commits.clear()
        self.infra_dev_commits.clear()
        self.dev_test_commits.clear()
        self.dev_build_commits.clear()
        self.test_build_commits.clear()

        self.commit_categories.clear()

        for key in self.detailed_stats:
            self.detailed_stats[key].clear()

        # Process each commit
        for commit_sha, commit_data in data.items():
            files = commit_data.get("Files", [])
            if files is None or len(files) == 0:
                continue  # Skip commits with no files

            self.total_commits += 1

            # Get all categories for this commit
            commit_categories = set()

            for file_info in files:
                category = file_info.get("category", "Unknown")
                commit_categories.add(category)

            # Store categories for this commit
            self.commit_categories[commit_sha] = commit_categories

            # Check if commit touches infrastructure or build files
            has_infrastructure = "Infrastructure" in commit_categories
            has_build = "Build" in commit_categories
            has_test = "Test" in commit_categories
            has_dev = "Development" in commit_categories

            if has_infrastructure:
                self.infrastructure_commits.add(commit_sha)

            if has_build:
                self.build_commits.add(commit_sha)

            if has_test:
                self.test_commits.add(commit_sha)

            if has_dev:
                self.dev_commits.add(commit_sha)

            if has_infrastructure and not has_build and not has_test and not has_dev:
                self.detailed_stats['infra_only'].add(commit_sha)

            elif has_build and not has_infrastructure and not has_test and not has_dev:
                self.detailed_stats['build_only'].add(commit_sha)

            elif has_test and not has_infrastructure and not has_build and not has_dev:
                self.detailed_stats['test_only'].add(commit_sha)

            elif has_dev and not has_infrastructure and not has_build and not has_test:
                self.detailed_stats['dev_only'].add(commit_sha)

            if has_infrastructure and has_build:
                self.infra_build_commits.add(commit_sha)
                self.detailed_stats['both_infra_build'].add(commit_sha)

            if has_infrastructure and has_test:
                self.infra_test_commits.add(commit_sha)
                self.detailed_stats['both_infra_test'].add(commit_sha)

            if has_infrastructure and has_dev:
                self.infra_dev_commits.add(commit_sha)
                self.detailed_stats['both_infra_dev'].add(commit_sha)

            if has_dev and has_test:
                self.dev_test_commits.add(commit_sha)
                self.detailed_stats['both_dev_test'].add(commit_sha)

            if has_dev and has_build:
                self.dev_build_commits.add(commit_sha)
                self.detailed_stats['both_dev_build'].add(commit_sha)

            if has_test and has_build:
                self.test_build_commits.add(commit_sha)
                self.detailed_stats['both_test_build'].add(commit_sha)

        return True

    def calculate_overlap_percentages(self):
        """Calculate various overlap percentages."""
        stats = {}

        # Basic counts
        stats['total_commits'] = self.total_commits

        stats['infrastructure_commits'] = len(self.infrastructure_commits)
        stats['build_commits'] = len(self.build_commits)
        stats['test_commits'] = len(self.test_commits)
        stats['dev_commits'] = len(self.dev_commits)

        stats['both_infra_test'] = len(self.infra_test_commits)
        stats['both_infra_dev'] = len(self.infra_dev_commits)
        stats['both_infra_build'] = len(self.infra_build_commits)
        stats['both_dev_test'] = len(self.dev_test_commits)
        stats['both_dev_build'] = len(self.dev_build_commits)
        stats['both_test_build'] = len(self.test_build_commits)

        if self.total_commits > 0:
            stats['infra_commits_pct'] = len(self.infrastructure_commits) / self.total_commits
            stats['build_commits_pct'] = len(self.build_commits) / self.total_commits
            stats['test_commits_pct'] = len(self.test_commits) / self.total_commits
            stats['dev_commits_pct'] = len(self.dev_commits) / self.total_commits

            stats['infra_build_pct'] = len(self.infra_build_commits) / self.total_commits
            stats['infra_test_pct'] = len(self.infra_test_commits) / self.total_commits
            stats['infra_dev_pct'] = len(self.infra_dev_commits) / self.total_commits
            stats['dev_test_pct'] = len(self.dev_test_commits) / self.total_commits
            stats['dev_build_pct'] = len(self.dev_build_commits) / self.total_commits
            stats['test_build_pct'] = len(self.test_build_commits) / self.total_commits
        else:
            stats['infra_commits_pct'] = 0
            stats['build_commits_pct'] = 0
            stats['test_commits_pct'] = 0
            stats['dev_commits_pct'] = 0

            stats['infra_build_pct'] = 0
            stats['infra_test_pct'] = 0
            stats['infra_dev_pct'] = 0
            stats['dev_test_pct'] = 0
            stats['dev_build_pct'] = 0
            stats['test_build_pct'] = 0

        # Detailed breakdown
        stats['infra_only_count'] = len(self.detailed_stats['infra_only'])
        stats['build_only_count'] = len(self.detailed_stats['build_only'])
        stats['test_only_count'] = len(self.detailed_stats['test_only'])
        stats['dev_only_count'] = len(self.detailed_stats['dev_only'])

        stats['both_infra_build_count'] = len(self.detailed_stats['both_infra_build'])
        stats['both_infra_test_count'] = len(self.detailed_stats['both_infra_test'])
        stats['both_infra_dev_count'] = len(self.detailed_stats['both_infra_dev'])
        stats['both_dev_test_count'] = len(self.detailed_stats['both_dev_test'])
        stats['both_dev_build_count'] = len(self.detailed_stats['both_dev_build'])
        stats['both_test_build_count'] = len(self.detailed_stats['both_test_build'])

        return stats

    def print_analysis(self, filename=""):
        """Print detailed overlap analysis."""
        stats = self.calculate_overlap_percentages()
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Analyze category overlap in commit data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("json_files", nargs="+", help="JSON file(s) to analyze")
    args = parser.parse_args()
    analyzer = InfraBuildOverlapAnalyzer()

    try:
        # Process each JSON file
        for json_file in args.json_files:
            if not os.path.exists(json_file):
                print(f"⚠️  File not found: {json_file}")
                continue

            fileName = os.path.basename(json_file)
            success = analyzer.analyze_json_file(json_file)
            if success:
                stats = analyzer.print_analysis(fileName)

                # Print Metrics for Report
                print(f"\n📊 Metrics for Report")

                print(f"\nP(Infrastructure) = {stats['infra_commits_pct'] :.3f}")
                print(f"P(Development) = {stats['dev_commits_pct'] :.3f}")
                print(f"P(Build) = {stats['build_commits_pct'] :.3f}")
                print(f"P(Test) = {stats['infra_commits_pct'] :.3f}")

                # Support Calculations
                print(f"\nSupp(Infrastructure|Build) = {stats['infra_build_pct'] :.3f}")
                print(f"Supp(Infrastructure|Development) = {stats['infra_dev_pct'] :.3f}")
                print(f"Supp(Infrastructure|Test) = {stats['infra_test_pct'] :.3f}")

                # Confidence Calculations
                print(f"\nConf(Infrastructure|Build) = {stats['infra_build_pct'] / stats['infra_commits_pct'] :.3f}")
                print(f"Conf(Build|Infrastructure) = {stats['infra_build_pct'] / stats['build_commits_pct'] :.3f}")
                print(f"Conf(Infrastructure|Development) = {stats['infra_dev_pct'] / stats['infra_commits_pct'] :.3f}")
                print(f"Conf(Development|Infrastructure) = {stats['infra_dev_pct'] / stats['dev_commits_pct'] :.3f}")
                print(f"Conf(Infrastructure|Test) = {stats['infra_test_pct'] / stats['infra_commits_pct'] :.3f}")
                print(f"Conf(Test|Infrastructure) = {stats['infra_test_pct'] / stats['test_commits_pct'] :.3f}")

                # Lift Calculations
                infra_build_lift = stats['infra_build_pct'] / (stats['infra_commits_pct'] * stats['build_commits_pct'])
                print(f"\nLift(Infrastructure|Build) = { infra_build_lift :.3f}")
                infra_dev_lift = stats['infra_dev_pct'] / (stats['infra_commits_pct'] * stats['dev_commits_pct'])
                print(f"Lift(Infrastructure|Development) = { infra_dev_lift :.3f}")
                infra_test_lift = stats['infra_test_pct'] / (stats['infra_commits_pct'] * stats['test_commits_pct'])
                print(f"Lift(Infrastructure|Test) = { infra_test_lift :.3f}")

            print("\n" + "=" * 80 + "\n")  # Separator between files

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
