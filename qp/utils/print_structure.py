import os
from pathlib import Path

def print_project_structure(root_dir, indent=""):
    root = Path(root_dir)
    # Get all items, sorting directories before files
    items = sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    
    for i, path in enumerate(items):
        # Skip hidden files/folders like .git or .venv
        if path.name.startswith(('.', '__pycache__')):
            continue
            
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        print(f"{indent}{connector}{path.name}")
        
        if path.is_dir():
            new_indent = indent + ("    " if is_last else "│   ")
            print_project_structure(path, new_indent)

# Usage: Run from your project root
if __name__ == "__main__":
    print(f"{os.path.basename(os.getcwd())}/")
    print_project_structure(".")