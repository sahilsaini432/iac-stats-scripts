import json
import argparse
import os
from collections import defaultdict


class InfraBuildOverlapAnalyzer:
    def __init__(self):
        self.total_devs = 0
        self.dev_names = set()

        self.infrastructure_devs = set()
        self.dev_devs = set()
        self.test_devs = set()
        self.build_devs = set()

        self.infra_test_devs = set()
        self.infra_dev_devs = set()
        self.infra_build_devs = set()
        self.dev_test_devs = set()
        self.dev_build_devs = set()
        self.test_build_devs = set()

        self.dev_categories = defaultdict(set)  # Maps commit devs to set of categories
        self.detailed_stats = {
            "both_infra_test": set(),
            "both_infra_dev": set(),
            "both_infra_build": set(),
            "both_dev_test": set(),
            "both_dev_build": set(),
            "both_test_build": set(),
        }

        self.stats = defaultdict(dict)

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
        self.total_devs = 0
        self.dev_names.clear()

        self.infrastructure_devs.clear()
        self.build_devs.clear()
        self.test_devs.clear()
        self.dev_devs.clear()

        self.infra_build_devs.clear()
        self.infra_test_devs.clear()
        self.infra_dev_devs.clear()
        self.dev_test_devs.clear()
        self.dev_build_devs.clear()
        self.test_build_devs.clear()

        self.dev_categories.clear()

        for key in self.detailed_stats:
            self.detailed_stats[key].clear()

        # Process each commit
        for commit_sha, commit_data in data.items():
            author = commit_data.get("Author")
            self.dev_names.add(author)

            files = commit_data.get("Files", [])
            if files is None or len(files) == 0:
                continue  # Skip devs with no files

            # Get all categories for this commit
            dev_categories = set()

            for file_info in files:
                category = file_info.get("category", "Unknown")
                dev_categories.add(category)

            # Store categories for this commit
            self.dev_categories[author] = dev_categories

            # Check if commit touches infrastructure or build files
            has_infrastructure = "Infrastructure" in dev_categories
            has_build = "Build" in dev_categories
            has_test = "Test" in dev_categories
            has_dev = "Development" in dev_categories

            if has_infrastructure:
                self.infrastructure_devs.add(author)

            if has_build:
                self.build_devs.add(author)

            if has_test:
                self.test_devs.add(author)

            if has_dev:
                self.dev_devs.add(author)

        self.total_devs = len(self.dev_names)

        # Process dev categories
        for author in self.dev_names:
            is_infrastructure = author in self.infrastructure_devs
            is_build = author in self.build_devs
            is_test = author in self.test_devs
            is_dev = author in self.dev_devs

            if is_infrastructure and is_build:
                self.infra_build_devs.add(author)
                self.detailed_stats['both_infra_build'].add(author)

            if is_infrastructure and is_test:
                self.infra_test_devs.add(author)
                self.detailed_stats['both_infra_test'].add(author)

            if is_infrastructure and is_dev:
                self.infra_dev_devs.add(author)
                self.detailed_stats['both_infra_dev'].add(author)

            if is_dev and is_test:
                self.dev_test_devs.add(author)
                self.detailed_stats['both_dev_test'].add(author)

            if is_dev and is_build:
                self.dev_build_devs.add(author)
                self.detailed_stats['both_dev_build'].add(author)

            if is_test and is_build:
                self.test_build_devs.add(author)
                self.detailed_stats['both_test_build'].add(author)

        return True

    def calculate_overlap_percentages(self):
        """Calculate various overlap percentages."""
        stats = {}

        # Basic counts
        stats['total_devs'] = self.total_devs

        stats['infrastructure_devs'] = len(self.infrastructure_devs)
        stats['build_devs'] = len(self.build_devs)
        stats['test_devs'] = len(self.test_devs)
        stats['dev_devs'] = len(self.dev_devs)

        stats['both_infra_test'] = len(self.infra_test_devs)
        stats['both_infra_dev'] = len(self.infra_dev_devs)
        stats['both_infra_build'] = len(self.infra_build_devs)

        stats['supp_infra'] = len(self.infrastructure_devs) / self.total_devs
        stats['supp_build'] = len(self.build_devs) / self.total_devs
        stats['supp_test'] = len(self.test_devs) / self.total_devs
        stats['supp_dev'] = len(self.dev_devs) / self.total_devs

        stats['supp_infra_build'] = len(self.infra_build_devs) / self.total_devs
        stats['supp_infra_test'] = len(self.infra_test_devs) / self.total_devs
        stats['supp_infra_dev'] = len(self.infra_dev_devs) / self.total_devs

        # Infrastructure and Build (avoid zero division)
        if len(self.infrastructure_devs) > 0:
            stats['conf_infra_build'] = len(self.infra_build_devs) / len(self.infrastructure_devs)
            stats['conf_infra_test'] = len(self.infra_test_devs) / len(self.infrastructure_devs)
            stats['conf_infra_dev'] = len(self.infra_dev_devs) / len(self.infrastructure_devs)
        else:
            stats['conf_infra_build'] = 0
            stats['conf_infra_test'] = 0
            stats['conf_infra_dev'] = 0

        if len(self.build_devs) > 0:
            stats['conf_build_infra'] = len(self.infra_build_devs) / len(self.build_devs)
        else:
            stats['conf_build_infra'] = 0

        if len(self.test_devs) > 0:
            stats['conf_test_infra'] = len(self.infra_test_devs) / len(self.test_devs)
        else:
            stats['conf_test_infra'] = 0

        if len(self.dev_devs) > 0:
            stats['conf_dev_infra'] = len(self.infra_dev_devs) / len(self.dev_devs)
        else:
            stats['conf_dev_infra'] = 0

        self.stats = stats


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
                analyzer.calculate_overlap_percentages()

                for key, value in analyzer.stats.items():
                    print(f"{key}: {value}")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
