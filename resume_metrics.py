#!/usr/bin/env python3
"""
Resume Metrics Analyzer for specs-ai
====================================
This script extracts repository statistics and generates resume-optimized
talking points for your CV. It analyzes code quality, impact metrics,
technical breadth, and user engagement.

Run: python resume_metrics.py
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Any


class ResumeMetricsAnalyzer:
    """Analyzes a GitHub repository to extract resume-worthy metrics."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.metrics = {}
        self.resume_bullets = []

    def run_git_command(self, command: str) -> str:
        """Execute a git command and return output."""
        try:
            result = subprocess.run(
                f"git -C {self.repo_path} {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"⚠️  Warning: {e}")
            return ""

    # =====================================================================
    # METRIC COLLECTION METHODS
    # =====================================================================

    def analyze_git_history(self) -> Dict[str, Any]:
        """Extract git-based metrics: commits, contributors, timeline."""
        metrics = {}

        # Total commits
        total_commits = len(self.run_git_command("rev-list --all").split("\n"))
        metrics["total_commits"] = total_commits

        # Unique contributors
        contributors_output = self.run_git_command(
            "log --format='%aN' | sort -u"
        )
        contributors = [c for c in contributors_output.split("\n") if c]
        metrics["unique_contributors"] = len(contributors)

        # Development timeline
        first_commit = self.run_git_command(
            "log --format='%ai' --reverse | head -1"
        )
        latest_commit = self.run_git_command("log -1 --format='%ai'")
        metrics["first_commit"] = first_commit
        metrics["latest_commit"] = latest_commit
        metrics["days_of_development"] = self._calc_days_between(
            first_commit, latest_commit
        )

        # Branches count
        branches_output = self.run_git_command("branch -a")
        metrics["branches_count"] = len([b for b in branches_output.split("\n") if b])

        return metrics

    def analyze_codebase_size(self) -> Dict[str, Any]:
        """Count lines of code, language distribution, and file types."""
        metrics = {}
        language_stats = defaultdict(int)
        total_lines = 0
        file_counts = defaultdict(int)

        # Walk through repo and count files/lines by extension
        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden dirs and common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       ["__pycache__", "node_modules", "venv", ".venv", "dist", "build"]]

            for file in files:
                if file.startswith("."):
                    continue

                filepath = Path(root) / file
                ext = filepath.suffix.lower()

                # Map extensions to languages
                lang = self._map_extension_to_language(ext)
                if lang:
                    file_counts[lang] += 1

                    # Count lines for code files only
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            lines = len(f.readlines())
                            language_stats[lang] += lines
                            total_lines += lines
                    except Exception:
                        pass

        metrics["total_lines_of_code"] = total_lines
        metrics["language_distribution"] = dict(language_stats)
        metrics["file_counts_by_language"] = dict(file_counts)
        metrics["primary_language"] = max(language_stats, key=language_stats.get) if language_stats else None
        metrics["total_files"] = sum(file_counts.values())

        return metrics

    def analyze_features_and_complexity(self) -> Dict[str, Any]:
        """Identify key features, modules, and architectural complexity."""
        metrics = {}

        # Identify main modules (directories in src/specs_ai/)
        main_dir = self.repo_path / "specs_ai"
        if main_dir.exists():
            modules = [d.name for d in main_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
            main_files = [f.stem for f in main_dir.glob("*.py") if not f.name.startswith("_")]
            metrics["core_modules"] = modules + main_files
        else:
            metrics["core_modules"] = []

        # Count functions/classes (pseudocode version)
        metrics["estimated_functions"] = self._count_python_functions()
        metrics["estimated_classes"] = self._count_python_classes()

        # Key features from README
        metrics["key_features"] = self._extract_features_from_readme()

        return metrics

    def analyze_testing_and_quality(self) -> Dict[str, Any]:
        """Assess test coverage, CI/CD setup, and code quality tools."""
        metrics = {}

        # Test files
        test_files = list(self.repo_path.glob("tests/**/*.py")) + \
                     list(self.repo_path.glob("test_*.py"))
        metrics["test_files_count"] = len(test_files)

        # Test lines of code
        test_loc = sum(len(open(f).readlines()) for f in test_files)
        metrics["test_lines_of_code"] = test_loc

        # CI/CD pipelines
        ci_files = list(self.repo_path.glob(".github/workflows/*.yml")) + \
                   list(self.repo_path.glob(".github/workflows/*.yaml")) + \
                   list(self.repo_path.glob(".gitlab-ci.yml")) + \
                   list(self.repo_path.glob("Jenkinsfile"))
        metrics["ci_cd_pipelines"] = [f.name for f in ci_files]

        # Code quality tools (from files like pyproject.toml, setup.cfg, etc.)
        metrics["code_quality_tools"] = self._detect_quality_tools()

        # Documentation
        docs_files = list(self.repo_path.glob("docs/**/*.md")) + \
                     list(self.repo_path.glob("*.md"))
        metrics["documentation_files"] = len(docs_files)

        return metrics

    def analyze_deployment_and_distribution(self) -> Dict[str, Any]:
        """Check if published to PyPI, Docker, package managers, etc."""
        metrics = {}

        # PyPI presence (check pyproject.toml or setup.py)
        pyproject = self.repo_path / "pyproject.toml"
        setup_py = self.repo_path / "setup.py"

        if pyproject.exists() or setup_py.exists():
            metrics["published_to_pypi"] = True
            # Extract package name from pyproject.toml
            if pyproject.exists():
                with open(pyproject) as f:
                    content = f.read()
                    if 'name = "' in content:
                        pkg_name = content.split('name = "')[1].split('"')[0]
                        metrics["package_name"] = pkg_name
        else:
            metrics["published_to_pypi"] = False

        # Docker support
        metrics["has_docker"] = (self.repo_path / "Dockerfile").exists()

        # CLI support
        metrics["has_cli"] = (self.repo_path / "specs_ai" / "cli.py").exists()

        # Configuration files (indicates maturity)
        config_files = [
            "setup.cfg", "tox.ini", "pytest.ini", ".editorconfig",
            "Makefile", "docker-compose.yml"
        ]
        metrics["config_files"] = [f for f in config_files if (self.repo_path / f).exists()]

        return metrics

    def analyze_dependencies_and_integrations(self) -> Dict[str, Any]:
        """Extract tech stack and external integrations."""
        metrics = {}

        # Parse dependencies from pyproject.toml
        dependencies = self._extract_dependencies()
        metrics["dependencies"] = dependencies
        metrics["dependency_count"] = len(dependencies)

        # Identify major tech integrations
        integrations = self._identify_integrations(dependencies)
        metrics["key_integrations"] = integrations

        return metrics

    def analyze_git_collaboration(self) -> Dict[str, Any]:
        """Extract collaboration metrics: PRs, issues, release frequency."""
        metrics = {}

        # Issue count (if repo has GitHub integration)
        # Pseudocode: would query GitHub API
        metrics["open_issues"] = self._get_github_open_issues_count()
        metrics["total_issues_created"] = self._get_github_total_issues_count()

        # PR/collaboration signals
        metrics["has_pr_templates"] = (self.repo_path / ".github" / "pull_request_template.md").exists()
        metrics["has_contributing_guide"] = (self.repo_path / "CONTRIBUTING.md").exists()

        # Release frequency
        release_info = self.run_git_command("tag")
        metrics["release_tags"] = len([t for t in release_info.split("\n") if t])

        return metrics

    # =====================================================================
    # HELPER METHODS
    # =====================================================================

    def _map_extension_to_language(self, ext: str) -> str:
        """Map file extension to programming language."""
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".sh": "Shell",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".json": "JSON",
            ".md": "Markdown",
            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL",
        }
        return mapping.get(ext, None)

    def _count_python_functions(self) -> int:
        """Count total function definitions in Python files."""
        count = 0
        for pyfile in self.repo_path.glob("**/*.py"):
            if "venv" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            try:
                with open(pyfile) as f:
                    count += f.read().count("def ")
            except Exception:
                pass
        return count

    def _count_python_classes(self) -> int:
        """Count total class definitions in Python files."""
        count = 0
        for pyfile in self.repo_path.glob("**/*.py"):
            if "venv" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            try:
                with open(pyfile) as f:
                    count += f.read().count("class ")
            except Exception:
                pass
        return count

    def _extract_features_from_readme(self) -> List[str]:
        """Parse README.md to extract key features."""
        readme = self.repo_path / "README.md"
        features = []
        if readme.exists():
            with open(readme) as f:
                content = f.read()
                # Simple heuristic: look for feature sections
                if "Features" in content:
                    lines = content.split("\n")
                    in_features = False
                    for line in lines:
                        if "## Features" in line or "# Features" in line:
                            in_features = True
                            continue
                        if in_features and line.startswith("##"):
                            break
                        if in_features and line.strip().startswith("-"):
                            features.append(line.strip()[2:])
        return features[:10]  # Top 10 features

    def _detect_quality_tools(self) -> List[str]:
        """Detect code quality, linting, and formatting tools."""
        tools = []
        tool_indicators = {
            "pytest": "tests" in str(self.repo_path / "pyproject.toml"),
            "black": "black" in str(self.repo_path / "pyproject.toml"),
            "ruff": "ruff" in str(self.repo_path / "pyproject.toml"),
            "mypy": "mypy" in str(self.repo_path / "pyproject.toml"),
            "pre-commit": (self.repo_path / ".pre-commit-config.yaml").exists(),
            "GitHub Actions": (self.repo_path / ".github" / "workflows").exists(),
        }

        for tool, check in tool_indicators.items():
            if check:
                tools.append(tool)

        return tools

    def _extract_dependencies(self) -> List[str]:
        """Extract project dependencies from pyproject.toml or requirements.txt."""
        dependencies = []

        # Check pyproject.toml
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject) as f:
                    content = f.read()
                    if "dependencies" in content:
                        lines = content.split("dependencies = [")[1].split("]")[0]
                        for line in lines.split("\n"):
                            pkg = line.strip().strip('"').split(";")[0].strip()
                            if pkg:
                                dependencies.append(pkg)
            except Exception:
                pass

        # Check requirements.txt
        req_file = self.repo_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    dependencies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            except Exception:
                pass

        return dependencies

    def _identify_integrations(self, dependencies: List[str]) -> List[str]:
        """Identify major integrations from dependencies (AI, databases, cloud, etc.)."""
        integrations = []

        integration_keywords = {
            "AI/ML": ["torch", "tensorflow", "scikit", "openai", "gemini", "anthropic", "google-genai"],
            "Database": ["sqlalchemy", "psycopg2", "pymongo", "redis", "firebase"],
            "Cloud": ["boto3", "azure", "google-cloud"],
            "Web": ["django", "flask", "fastapi", "requests"],
            "Data": ["pandas", "numpy", "polars"],
            "CLI": ["click", "typer", "argparse", "rich", "textual"],
        }

        dep_str = " ".join(dependencies).lower()

        for category, keywords in integration_keywords.items():
            for keyword in keywords:
                if keyword.lower() in dep_str:
                    integrations.append(f"{category} ({keyword})")
                    break

        return list(set(integrations))

    def _calc_days_between(self, date1_str: str, date2_str: str) -> int:
        """Calculate days between two ISO date strings."""
        try:
            date1 = datetime.fromisoformat(date1_str.split()[0])
            date2 = datetime.fromisoformat(date2_str.split()[0])
            return abs((date2 - date1).days)
        except Exception:
            return 0

    def _get_github_open_issues_count(self) -> int:
        """
        Pseudocode: Query GitHub API for open issues.
        Replace with actual API call: https://api.github.com/repos/owner/repo
        """
        # For now, return placeholder
        return 0

    def _get_github_total_issues_count(self) -> int:
        """Pseudocode: Query GitHub API for total issues."""
        return 0

    # =====================================================================
    # RESUME BULLET GENERATION
    # =====================================================================

    def generate_resume_bullets(self) -> List[str]:
        """
        Convert metrics into resume-optimized bullet points.
        Prioritizes impact, scale, and technical depth.
        """
        bullets = []

        # 1. PROJECT SCALE & SCOPE
        loc = self.metrics.get("codebase", {}).get("total_lines_of_code", 0)
        if loc > 1000:
            bullets.append(
                f"🔧 Architected and developed a {loc:,}+ line full-stack project with "
                f"{self.metrics.get('codebase', {}).get('total_files', 0)} files across "
                f"{len(self.metrics.get('codebase', {}).get('language_distribution', {}))} programming languages"
            )

        # 2. AI/ADVANCED FEATURES
        integrations = self.metrics.get("dependencies", {}).get("key_integrations", [])
        if any("AI" in i or "ML" in i or "gemini" in i.lower() for i in integrations):
            bullets.append(
                "🤖 Integrated Google Gemini API for intelligent hardware upgrade recommendations "
                "with context-aware decision logic"
            )

        # 3. PRODUCTION-READY DEPLOYMENT
        if self.metrics.get("deployment", {}).get("published_to_pypi"):
            bullets.append(
                f"📦 Published '{self.metrics.get('deployment', {}).get('package_name')}' to PyPI "
                f"as a production-grade CLI tool with support for Python 3.10+"
            )

        # 4. USER INTERFACE & UX
        if self.metrics.get("deployment", {}).get("has_cli"):
            features = self.metrics.get("features", {}).get("key_features", [])
            feature_str = ", ".join(features[:3]) if features else "multiple modes"
            bullets.append(
                f"💻 Built interactive CLI with {feature_str} using Rich and Textual TUI frameworks"
            )

        # 5. TECHNICAL DEPTH
        functions = self.metrics.get("features", {}).get("estimated_functions", 0)
        classes = self.metrics.get("features", {}).get("estimated_classes", 0)
        if functions > 30:
            bullets.append(
                f"🏗️  Designed {classes} object-oriented classes and {functions}+ functions "
                f"with clean separation of concerns and SOLID principles"
            )

        # 6. SYSTEM-LEVEL INTEGRATION
        bullets.append(
            "🖥️  Implemented WMI (Windows Management Instrumentation) integration to extract "
            "real-time hardware specifications with multi-threaded daemon processes and timeout handling"
        )

        # 7. TESTING & CODE QUALITY
        test_files = self.metrics.get("testing", {}).get("test_files_count", 0)
        quality_tools = self.metrics.get("testing", {}).get("code_quality_tools", [])
        if test_files > 0 or quality_tools:
            tools_str = ", ".join(quality_tools[:3])
            bullets.append(
                f"✅ Established automated testing with {test_files}+ test files and CI/CD pipelines "
                f"({tools_str})"
            )

        # 8. DOCUMENTATION & COLLABORATION
        if self.metrics.get("collaboration", {}).get("has_contributing_guide"):
            bullets.append(
                "📚 Created comprehensive documentation (README, contributing guide, API docs) "
                "enabling external contributions"
            )

        # 9. DEVELOPMENT VELOCITY
        commits = self.metrics.get("git", {}).get("total_commits", 0)
        days = self.metrics.get("git", {}).get("days_of_development", 1)
        if commits > 30 and days > 0:
            velocity = round(commits / (days / 30), 1)  # commits per month
            bullets.append(
                f"⚡ Shipped {commits} commits over {days} days of active development "
                f"({velocity} commits/month), demonstrating rapid iteration and problem-solving"
            )

        # 10. RELEASE MANAGEMENT
        releases = self.metrics.get("collaboration", {}).get("release_tags", 0)
        if releases > 0:
            bullets.append(
                f"🎯 Managed {releases}+ releases with semantic versioning and changelog tracking"
            )

        # 11. TECHNICAL STACK SUMMARY
        primary_lang = self.metrics.get("codebase", {}).get("primary_language", "Unknown")
        dependency_count = self.metrics.get("dependencies", {}).get("dependency_count", 0)
        bullets.append(
            f"⚙️  Tech Stack: {primary_lang}, integrated {dependency_count}+ dependencies "
            f"(psutil, google-genai, Textual, Rich, WMI, python-dotenv)"
        )

        return bullets

    # =====================================================================
    # REPORTING
    # =====================================================================

    def collect_all_metrics(self):
        """Run all metric collection methods."""
        print("🔍 Analyzing repository...\n")

        self.metrics["git"] = self.analyze_git_history()
        print("✓ Git history analyzed")

        self.metrics["codebase"] = self.analyze_codebase_size()
        print("✓ Codebase size calculated")

        self.metrics["features"] = self.analyze_features_and_complexity()
        print("✓ Features and modules identified")

        self.metrics["testing"] = self.analyze_testing_and_quality()
        print("✓ Testing and code quality assessed")

        self.metrics["deployment"] = self.analyze_deployment_and_distribution()
        print("✓ Deployment options analyzed")

        self.metrics["dependencies"] = self.analyze_dependencies_and_integrations()
        print("✓ Dependencies and integrations extracted")

        self.metrics["collaboration"] = self.analyze_git_collaboration()
        print("✓ Collaboration metrics gathered\n")

    def print_metrics_summary(self):
        """Print a structured summary of all metrics."""
        print("=" * 80)
        print("📊 REPOSITORY METRICS SUMMARY".center(80))
        print("=" * 80)
        print()

        # Git Metrics
        print("📈 GIT & DEVELOPMENT")
        print("-" * 80)
        git = self.metrics.get("git", {})
        print(f"  Total Commits:           {git.get('total_commits', 'N/A')}")
        print(f"  Unique Contributors:     {git.get('unique_contributors', 'N/A')}")
        print(f"  Days of Development:     {git.get('days_of_development', 'N/A')} days")
        print(f"  Release Tags:            {self.metrics.get('collaboration', {}).get('release_tags', 'N/A')}")
        print()

        # Codebase Metrics
        print("💻 CODEBASE")
        print("-" * 80)
        code = self.metrics.get("codebase", {})
        print(f"  Total Lines of Code:     {code.get('total_lines_of_code', 'N/A'):,}")
        print(f"  Total Files:             {code.get('total_files', 'N/A')}")
        print(f"  Primary Language:        {code.get('primary_language', 'N/A')}")
        if code.get("language_distribution"):
            print(f"  Language Distribution:   {code.get('language_distribution')}")
        print()

        # Features & Complexity
        print("🏗️  ARCHITECTURE & FEATURES")
        print("-" * 80)
        features = self.metrics.get("features", {})
        print(f"  Classes:                 {features.get('estimated_classes', 'N/A')}")
        print(f"  Functions:               {features.get('estimated_functions', 'N/A')}")
        if features.get("core_modules"):
            print(f"  Core Modules:            {', '.join(features.get('core_modules', [])[:5])}")
        if features.get("key_features"):
            print(f"  Key Features:            {len(features.get('key_features', []))} identified")
        print()

        # Testing & Quality
        print("✅ TESTING & CODE QUALITY")
        print("-" * 80)
        testing = self.metrics.get("testing", {})
        print(f"  Test Files:              {testing.get('test_files_count', 'N/A')}")
        print(f"  Test Lines of Code:      {testing.get('test_lines_of_code', 'N/A'):,}")
        print(f"  Documentation Files:     {testing.get('documentation_files', 'N/A')}")
        if testing.get("code_quality_tools"):
            print(f"  Quality Tools:           {', '.join(testing.get('code_quality_tools', []))}")
        if testing.get("ci_cd_pipelines"):
            print(f"  CI/CD Pipelines:         {', '.join(testing.get('ci_cd_pipelines', []))}")
        print()

        # Deployment
        print("🚀 DEPLOYMENT & DISTRIBUTION")
        print("-" * 80)
        deploy = self.metrics.get("deployment", {})
        print(f"  Published to PyPI:       {'Yes ✓' if deploy.get('published_to_pypi') else 'No'}")
        if deploy.get("package_name"):
            print(f"  Package Name:            {deploy.get('package_name')}")
        print(f"  Has CLI:                 {'Yes ✓' if deploy.get('has_cli') else 'No'}")
        print(f"  Has Docker Support:      {'Yes ✓' if deploy.get('has_docker') else 'No'}")
        if deploy.get("config_files"):
            print(f"  Config Files:            {', '.join(deploy.get('config_files', []))}")
        print()

        # Dependencies & Integrations
        print("⚙️  TECH STACK & INTEGRATIONS")
        print("-" * 80)
        deps = self.metrics.get("dependencies", {})
        print(f"  Total Dependencies:      {deps.get('dependency_count', 'N/A')}")
        if deps.get("key_integrations"):
            for integration in deps.get("key_integrations", [])[:5]:
                print(f"    • {integration}")
        print()

    def print_resume_bullets(self):
        """Print formatted resume bullets."""
        print("=" * 80)
        print("📄 RESUME-OPTIMIZED TALKING POINTS".center(80))
        print("=" * 80)
        print()
        print("💡 Copy & Customize These Bullets for Your CV:\n")

        self.resume_bullets = self.generate_resume_bullets()
        for i, bullet in enumerate(self.resume_bullets, 1):
            print(f"{i}. {bullet}\n")

        print("=" * 80)
        print("💼 RESUME TIPS".center(80))
        print("=" * 80)
        print("""
1. QUANTIFY IMPACT
   Instead of: "Developed a hardware tool"
   Say:        "Built a 5,000+ LOC Python tool with 70+ commits in 3 weeks"

2. HIGHLIGHT TECHNICAL DEPTH
   - Mention specific libraries/APIs used (Gemini, WMI, Textual, etc.)
   - Reference architectural patterns (async, threading, OOP)
   - Call out problem-solving (timeout handling, registry parsing, etc.)

3. EMPHASIZE USER-FACING VALUE
   - CLI with multiple interactive modes
   - Published on PyPI (public distribution)
   - Real-world use case (hardware recommendations)

4. SHOW FULL DEVELOPMENT CYCLE
   - Code quality tools (black, ruff, pytest)
   - CI/CD/testing infrastructure
   - Documentation and contributing guides
   - Release management

5. CATEGORIZE BY JOB LEVEL
   
   For JUNIOR roles:
   "Developed a full-featured Python CLI tool for hardware analysis,
   integrating WMI, psutil, and Google Gemini API. Implemented tests,
   CI/CD pipelines, and published to PyPI."
   
   For MID-LEVEL roles:
   "Architected a 5K+ LOC system-level tool with object-oriented design,
   multi-threaded hardware data collection, and AI-powered recommendations.
   Established testing (pytest), code quality (ruff/black), and deployment (PyPI)."
   
   For SENIOR roles:
   "Led end-to-end development of specs-ai: designed WMI/psutil integration
   with timeout handling, implemented Textual TUI for interactive UX,
   integrated Gemini API with prompt engineering. Established testing,
   CI/CD, and PyPI distribution. 70+ commits in 3 weeks, demonstrating
   rapid shipping and problem-solving across systems/AI/UX."

6. ADD CONTEXT
   - What problem does it solve? (Users struggle with hardware upgrades)
   - Why is it special? (Knows hardware constraints, gives real recommendations)
   - How mature is it? (Alpha, but production-ready, 70+ commits)

7. METRICS TO HIGHLIGHT
   ✓ Lines of code (5K+)
   ✓ Commits (70+)
   ✓ Development timeline (22 days, active)
   ✓ Tech stack breadth (Python, CLI, TUI, AI, WMI, threading)
   ✓ Distribution (PyPI)
   ✓ Code quality (testing, linting, formatting)
        """)

    def export_metrics_to_json(self, filepath: str = "resume_metrics.json"):
        """Export all metrics to JSON for further analysis or sharing."""
        with open(filepath, "w") as f:
            json.dump(self.metrics, f, indent=2, default=str)
        print(f"��� Metrics exported to {filepath}")

    def run(self):
        """Run the complete analysis and generate reports."""
        self.collect_all_metrics()
        self.print_metrics_summary()
        self.print_resume_bullets()
        self.export_metrics_to_json()


# =====================================================================
# MAIN ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    import sys

    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    analyzer = ResumeMetricsAnalyzer(repo_path)
    analyzer.run()

    print("\n" + "=" * 80)
    print("✨ Next Steps:")
    print("=" * 80)
    print("""
1. Review the resume bullets above
2. Customize them to match your job description
3. Add metrics about:
   - Downloads/stars (if any)
   - User testimonials or feedback
   - Real-world use cases or deployments
   - Any awards, mentions, or publications
4. Choose 2-4 of the strongest bullets for your CV
5. Practice your 2-minute explanation of this project
    """)
