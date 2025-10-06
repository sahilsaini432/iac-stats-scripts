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

        # Infrastructure and Build (avoid zero division)
        if len(self.infrastructure_commits) > 0:
            stats['infra_that_also_change_build_pct'] = len(self.infra_build_commits) / len(
                self.infrastructure_commits
            )
        else:
            stats['infra_that_also_change_build_pct'] = 0

        if len(self.build_commits) > 0:
            stats['build_that_also_change_infra_pct'] = len(self.infra_build_commits) / len(
                self.build_commits
            )
        else:
            stats['build_that_also_change_infra_pct'] = 0

        # Infrastructure and Test (avoid zero division)
        if len(self.infrastructure_commits) > 0:
            stats['infra_that_also_change_test_pct'] = len(self.infra_test_commits) / len(
                self.infrastructure_commits
            )
        else:
            stats['infra_that_also_change_test_pct'] = 0

        if len(self.test_commits) > 0:
            stats['test_that_also_change_infra_pct'] = len(self.infra_test_commits) / len(self.test_commits)
        else:
            stats['test_that_also_change_infra_pct'] = 0

        # Infrastructure and Dev (avoid zero division)
        if len(self.infrastructure_commits) > 0:
            stats['infra_that_also_change_dev_pct'] = len(self.infra_dev_commits) / len(
                self.infrastructure_commits
            )
        else:
            stats['infra_that_also_change_dev_pct'] = 0

        if len(self.dev_commits) > 0:
            stats['dev_that_also_change_infra_pct'] = len(self.infra_dev_commits) / len(self.dev_commits)
        else:
            stats['dev_that_also_change_infra_pct'] = 0

        # Dev and Test (avoid zero division)
        if len(self.dev_commits) > 0:
            stats['dev_that_also_change_test_pct'] = len(self.dev_test_commits) / len(self.dev_commits)
        else:
            stats['dev_that_also_change_test_pct'] = 0

        if len(self.test_commits) > 0:
            stats['test_that_also_change_dev_pct'] = len(self.dev_test_commits) / len(self.test_commits)
        else:
            stats['test_that_also_change_dev_pct'] = 0

        # Dev and Build (avoid zero division)
        if len(self.dev_commits) > 0:
            stats['dev_that_also_change_build_pct'] = len(self.dev_build_commits) / len(self.dev_commits)
        else:
            stats['dev_that_also_change_build_pct'] = 0

        if len(self.build_commits) > 0:
            stats['build_that_also_change_dev_pct'] = len(self.dev_build_commits) / len(self.build_commits)
        else:
            stats['build_that_also_change_dev_pct'] = 0

            # Test and Build (avoid zero division)
        if len(self.test_commits) > 0:
            stats['test_that_also_change_build_pct'] = len(self.test_build_commits) / len(self.test_commits)
        else:
            stats['test_that_also_change_build_pct'] = 0

        if len(self.build_commits) > 0:
            stats['build_that_also_change_test_pct'] = len(self.test_build_commits) / len(self.build_commits)
        else:
            stats['build_that_also_change_test_pct'] = 0

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

        print("=" * 80)
        print(f"Total commits analyzed: {stats['total_commits']:,}")
        print()

        # --------------------Infrastructure-Build------------------
        print(f"\n📊 Infrastructure-Build Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️  Infrastructure & Build File Changes:")
        print(
            f"   Infrastructure commits: {stats['infrastructure_commits']:,} ({stats['infra_commits_pct']:.1f}% of total)"
        )
        print(f"   Build commits: {stats['build_commits']:,} ({stats['build_commits_pct']:.1f}% of total)")
        print(
            f"   Commits changing both: {stats['both_infra_build']:,} ({stats['infra_build_pct']:.1f}% of total)"
        )
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Infrastructure commits that also change build files: {stats['infra_that_also_change_build_pct']:.1f}%"
        )
        print(
            f"   📈 Build commits that also change infrastructure files: {stats['build_that_also_change_infra_pct']:.1f}%"
        )
        print()

        # --------------------Infrastructure-Test------------------
        print(f"\n📊 Infrastructure-Test Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️  Infrastructure & Test File Changes:")
        print(
            f"   Infrastructure commits: {stats['infrastructure_commits']:,} ({stats['infra_commits_pct']:.1f}% of total)"
        )
        print(f"   Test commits: {stats['test_commits']:,} ({stats['test_commits_pct']:.1f}% of total)")
        print(
            f"   Commits changing both: {stats['both_infra_test']:,} ({stats['infra_test_pct']:.1f}% of total)"
        )
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Infrastructure commits that also change test files: {stats['infra_that_also_change_test_pct']:.1f}%"
        )
        print(
            f"   📈 Test commits that also change infrastructure files: {stats['test_that_also_change_infra_pct']:.1f}%"
        )
        print()

        # --------------------Infrastructure-Development------------------
        print(f"\n📊 Infrastructure-Development Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️  Infrastructure & Development File Changes:")
        print(
            f"   Infrastructure commits: {stats['infrastructure_commits']:,} ({stats['infra_commits_pct']:.1f}% of total)"
        )
        print(f"   Development commits: {stats['dev_commits']:,} ({stats['dev_commits_pct']:.1f}% of total)")
        print(
            f"   Commits changing both: {stats['both_infra_dev']:,} ({stats['infra_dev_pct']:.1f}% of total)"
        )
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Infrastructure commits that also change dev files: {stats['infra_that_also_change_dev_pct']:.1f}%"
        )
        print(
            f"   📈 Dev commits that also change infrastructure files: {stats['dev_that_also_change_infra_pct']:.1f}%"
        )
        print()

        # --------------------Development-Test------------------
        print(f"\n📊 Development-Test Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️   Development & Test File Changes:")
        print(f"   Development commits: {stats['dev_commits']:,} ({stats['dev_commits_pct']:.1f}% of total)")
        print(f"   Test commits: {stats['test_commits']:,} ({stats['test_commits_pct']:.1f}% of total)")
        print(f"   Commits changing both: {stats['both_dev_test']:,} ({stats['dev_test_pct']:.1f}% of total)")
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Development commits that also change test files: {stats['dev_that_also_change_test_pct']:.1f}%"
        )
        print(f"   📈 Test commits that also change dev files: {stats['test_that_also_change_dev_pct']:.1f}%")
        print()

        # --------------------Development-Build------------------
        print(f"\n📊 Development-Build Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️   Development & Build File Changes:")
        print(f"   Development commits: {stats['dev_commits']:,} ({stats['dev_commits_pct']:.1f}% of total)")
        print(f"   Build commits: {stats['build_commits']:,} ({stats['build_commits_pct']:.1f}% of total)")
        print(
            f"   Commits changing both: {stats['both_dev_build']:,} ({stats['dev_build_pct']:.1f}% of total)"
        )
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Development commits that also change build files: {stats['dev_that_also_change_build_pct']:.1f}%"
        )
        print(
            f"   📈 Build commits that also change dev files: {stats['build_that_also_change_dev_pct']:.1f}%"
        )
        print()

        # --------------------Build-Test------------------
        print(f"\n📊 Build-Test Overlap Analysis: {filename}")

        # Main statistics
        print("🏗️  Build & Test File Changes:")
        print(f"   Build commits: {stats['build_commits']:,} ({stats['build_commits_pct']:.1f}% of total)")
        print(f"   Test commits: {stats['test_commits']:,} ({stats['test_commits_pct']:.1f}% of total)")
        print(
            f"   Commits changing both: {stats['both_test_build']:,} ({stats['test_build_pct']:.1f}% of total)"
        )
        print()
        # Key percentages
        print("🎯 Key Overlap Metrics:")
        print(
            f"   📈 Build commits that also change test files: {stats['build_that_also_change_test_pct']:.1f}%"
        )
        print(
            f"   📈 Test commits that also change build files: {stats['test_that_also_change_build_pct']:.1f}%"
        )
        print()
        return stats

    # TODO: This is not fully set up to write all the info in a JSON file yet
    # def export_analysis(self, output_file, source_file=""):
    #     """Export analysis results to JSON."""
    #     stats = self.calculate_overlap_percentages()

    #     analysis_result = {
    #         "source_file": source_file,
    #         "analysis_type": "infrastructure_build_overlap",
    #         "summary": {
    #             "total_commits": stats['total_commits'],
    #             "infrastructure_commits": stats['infrastructure_commits'],
    #             "build_commits": stats['build_commits'],
    #             "overlap_commits": stats['overlap_commits'],
    #         },
    #         "percentages": {
    #             "infra_that_also_change_build": round(stats['infra_that_also_change_build_pct'], 2),
    #             "build_that_also_change_infra": round(stats['build_that_also_change_infra_pct'], 2),
    #             "overall_overlap": round(stats['overall_overlap_pct'], 2),
    #             "infrastructure_of_total": round(stats['infra_commits_pct'], 2),
    #             "build_of_total": round(stats['build_commits_pct'], 2),
    #         },
    #         "breakdown": {
    #             "infrastructure_only": stats['infra_only_count'],
    #             "build_only": stats['build_only_count'],
    #             "both_infra_and_build": stats['both_count'],
    #         },
    #         "sample_commits": {
    #             "overlap_examples": list(self.overlap_commits)[:10],  # First 10 examples
    #             "infra_only_examples": list(self.detailed_stats['infra_only'])[:5],
    #             "build_only_examples": list(self.detailed_stats['build_only'])[:5],
    #         },
    #     }

    #     try:
    #         with open(output_file, "w", encoding="utf-8") as f:
    #             json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    #         print(f"📄 Analysis exported to: {output_file}")
    #         return True
    #     except Exception as e:
    #         print(f"❌ Error writing analysis file: {e}")
    #         return False


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

                supp_infra_build = stats['infra_that_also_change_build_pct']
                supp_build_infra = stats['build_that_also_change_infra_pct']
                supp_infra_dev = stats['infra_that_also_change_dev_pct']
                supp_dev_infra = stats['dev_that_also_change_infra_pct']
                supp_infra_test = stats['infra_that_also_change_test_pct']
                supp_test_infra = stats['test_that_also_change_infra_pct']
                supp_dev_test = stats['dev_that_also_change_test_pct']
                supp_test_dev = stats['test_that_also_change_dev_pct']
                supp_dev_build = stats['dev_that_also_change_build_pct']
                supp_build_dev = stats['build_that_also_change_dev_pct']
                supp_test_build = stats['test_that_also_change_build_pct']
                supp_build_test = stats['build_that_also_change_test_pct']

                # Support Calculations
                print(f"\nSupp(Infrastructure|Build) = {supp_infra_build :.3f}")
                print(f"Supp(Build|Infrastructure) = {supp_build_infra :.3f}")

                print(f"Supp(Infrastructure|Development) = {supp_infra_dev :.3f}")
                print(f"Supp(Development|Infrastructure) = {supp_dev_infra :.3f}")

                print(f"Supp(Infrastructure|Test) = {supp_infra_test :.3f}")
                print(f"Supp(Test|Infrastructure) = {supp_test_infra :.3f}")

                print(f"Supp(Development|Test) = {supp_dev_test :.3f}")
                print(f"Supp(Test|Development) = {supp_test_dev :.3f}")

                print(f"Supp(Build|Development) = {supp_build_dev :.3f}")
                print(f"Supp(Development|Build) = {supp_dev_build :.3f}")

                print(f"Supp(Test|Build) = {supp_test_build :.3f}")
                print(f"Supp(Build|Test) = {supp_build_test :.3f}")

                # Confidence Calculations
                print(f"\nConf(Infrastructure|Build) = {supp_infra_build / stats['infra_commits_pct'] :.3f}")
                print(f"Conf(Build|Infrastructure) = {supp_build_infra / stats['build_commits_pct'] :.3f}")
                print(
                    f"Conf(Infrastructure|Development) = {supp_infra_dev / stats['infra_commits_pct'] :.3f}"
                )
                print(f"Conf(Development|Infrastructure) = {supp_dev_infra / stats['dev_commits_pct'] :.3f}")
                print(f"Conf(Infrastructure|Test) = {supp_infra_test / stats['infra_commits_pct'] :.3f}")
                print(f"Conf(Test|Infrastructure) = {supp_test_infra / stats['test_commits_pct'] :.3f}")
                print(f"Conf(Development|Test) = {supp_dev_test / stats['dev_commits_pct'] :.3f}")
                print(f"Conf(Test|Development) = {supp_test_dev / stats['test_commits_pct'] :.3f}")
                print(f"Conf(Build|Development) = {supp_build_dev / stats['build_commits_pct'] :.3f}")
                print(f"Conf(Development|Build) = {supp_dev_build / stats['dev_commits_pct'] :.3f}")
                print(f"Conf(Test|Build) = {supp_test_build / stats['test_commits_pct'] :.3f}")
                print(f"Conf(Build|Test) = {supp_build_test / stats['build_commits_pct'] :.3f}")

                # Lift Calculations
                print(
                    f"\nLift(Infrastructure|Build) = { (supp_infra_build / (stats['infra_commits_pct']) * stats['build_commits_pct']) :.3f}"
                )
                print(
                    f"Lift(Build|Infrastructure) = { (supp_build_infra / (stats['build_commits_pct'] * stats['infra_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Infrastructure|Development) = { (supp_infra_dev / (stats['infra_commits_pct'] * stats['dev_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Development|Infrastructure) = { (supp_dev_infra / (stats['dev_commits_pct'] * stats['infra_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Infrastructure|Test) = { (supp_infra_test / (stats['infra_commits_pct'] * stats['test_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Test|Infrastructure) = { (supp_test_infra / (stats['test_commits_pct'] * stats['infra_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Development|Test) = { (supp_dev_test / (stats['dev_commits_pct'] * stats['test_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Test|Development) = { (supp_test_dev / (stats['test_commits_pct'] * stats['dev_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Build|Development) = { (supp_build_dev / (stats['build_commits_pct'] * stats['dev_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Development|Build) = { (supp_dev_build / (stats['dev_commits_pct'] * stats['build_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Test|Build) = { (supp_test_build / (stats['test_commits_pct'] * stats['build_commits_pct'])) :.3f}"
                )
                print(
                    f"Lift(Build|Test) = { (supp_build_test / (stats['build_commits_pct'] * stats['test_commits_pct'])) :.3f}"
                )

                # path = Path(__file__).parent
                # analyzer.export_analysis(f"{path}/support_metrics/{fileName}-confidence.json", json_file)

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
