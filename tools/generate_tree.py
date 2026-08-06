import os

def print_tree(startpath, exclude_dirs=['.git', '.venv', '__pycache__', '.idea', 'node_modules', '.temp_env']):
    tree_str = []
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree_str.append('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree_str.append('{}{}'.format(subindent, f))
    return '\n'.join(tree_str)

tree = print_tree(r'D:\FaceAI_Project(!@#)')
with open(r'C:\Users\Acer\.gemini\antigravity\brain\1d771361-0b4e-4844-991f-32db947f5ccd\file_tree.txt', 'w', encoding='utf-8') as f:
    f.write(tree)
print("Tree generated.")
