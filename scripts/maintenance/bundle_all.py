import os
import subprocess

# 配置
ignore_dirs = {
    ".git",
    "__pycache__",
    ".aider.tags.cache.v4",
    "target",
    "data",
    "logs",
    "results",
    ".gemini",
    "node_modules",
    ".venv",
    "venv",
}
include_extensions = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".txt",
    ".rs",
    ".toml",
    ".json",
    ".sh",
    ".example",
}
branches_to_bundle = ["master"]
output_file = "project_bundle.md"


def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


def should_include(path, current_output):
    parts = path.split(os.sep)
    if any(part in ignore_dirs for part in parts):
        return False
    if (
        os.path.basename(path) == current_output
        or os.path.basename(path) == "bundle_all.py"
    ):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in include_extensions or os.path.basename(path) in {
        ".gitignore",
        "Dockerfile",
        "environment.yml",
    }


def get_bundle_content(branch_name):
    content = f"# Branch: {branch_name}\n\n"

    # 结构部分
    content += "## Project Structure\n```\n"
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(".", "", 1).count(os.sep)
        indent = "  " * level
        if root != ".":
            content += f"{indent}{os.path.basename(root)}/\n"
        subindent = "  " * (level + 1)
        for f in files:
            if should_include(os.path.join(root, f), output_file):
                content += f"{subindent}{f}\n"
    content += "```\n\n---\n\n"

    # 文件内容部分
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            file_path = os.path.normpath(os.path.join(root, f))
            if should_include(file_path, output_file):
                lang = os.path.splitext(f)[1][1:] if "." in f else ""
                content += f"# File: {file_path} (Branch: {branch_name})\n"
                content += f"```{lang}\n"
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as src:
                        content += src.read()
                except Exception as e:
                    content += f"// Error reading file: {e}\n"
                content += "\n```\n\n"
    return content


def main():
    original_branch = run_cmd("git branch --show-current")
    # 暂存更改
    has_changes = run_cmd("git status --porcelain") != ""
    if has_changes:
        print("Stashing local changes...")
        run_cmd("git stash")

    final_content = "# Multi-Branch Project Bundle\n\n"

    try:
        for branch in branches_to_bundle:
            print(f"Bundling branch: {branch}...")
            run_cmd(f"git checkout {branch}")
            final_content += f"{get_bundle_content(branch)}\n\n"
    finally:
        print(f"Switching back to {original_branch}...")
        run_cmd(f"git checkout {original_branch}")
        if has_changes:
            print("Restoring local changes...")
            run_cmd("git stash pop")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"Done! Bundled {len(branches_to_bundle)} branches into {output_file}")


if __name__ == "__main__":
    main()
