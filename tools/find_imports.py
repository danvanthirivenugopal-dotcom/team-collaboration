import os
import ast

def get_imports(directory):
    imports = set()
    for root, dirs, files in os.walk(directory):
        if '.venv' in root or '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                except Exception:
                    pass
    return sorted(list(imports))

print(get_imports(r'D:\FaceAI_Project(!@#)'))
