import os
import glob
from pathlib import Path

def generate_report():
    report = []
    report.append("# Project Inventory and Cleanup Report\n")
    
    # 1. Gather all files
    all_files = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or ".venv" in root or "__pycache__" in root or ".pytest_cache" in root:
            continue
        for file in files:
            all_files.append(os.path.join(root, file))
            
    # 2. Duplicate file detection
    filenames = {}
    for filepath in all_files:
        name = os.path.basename(filepath)
        if name not in filenames:
            filenames[name] = []
        filenames[name].append(filepath)
        
    report.append("## Duplicate Files Candidates\n")
    for name, paths in filenames.items():
        if len(paths) > 1 and name.endswith(".py") and name != "__init__.py":
            report.append(f"- `{name}` found in:\n")
            for p in paths:
                report.append(f"  - `{p}`\n")
                
    # 3. Find specific unwanted files
    unwanted = []
    for f in all_files:
        if any(f.endswith(ext) for ext in [".pyc", ".pyo", ".tmp", ".temp", ".bak", ".old", ".orig"]):
            unwanted.append(f)
            
    report.append("\n## Unwanted Files\n")
    for u in unwanted:
        report.append(f"- `{u}`\n")
        
    with open("tools/cleanup_report.md", "w", encoding="utf-8") as f:
        f.writelines(report)
        
if __name__ == "__main__":
    generate_report()
    print("Report generated at tools/cleanup_report.md")
