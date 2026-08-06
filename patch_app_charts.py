import re

file_path = r'D:\FaceAI_Project(!@#)\frontend\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add get_plotly_theme to import
content = content.replace('from utils.theme import apply_global_theme, render_theme_toggle', 'from utils.theme import apply_global_theme, render_theme_toggle, get_plotly_theme')

# Find all fig.update_layout blocks and inject **get_plotly_theme()
pattern = re.compile(r'(fig\.update_layout\([^)]*?)paper_bgcolor=.*?plot_bgcolor=.*?,([^)]*\))', re.DOTALL)
content = pattern.sub(r'\1**get_plotly_theme(),\2', content)

# Check for other instances that might not have matched exactly
content = re.sub(r'fig\.update_layout\(\s*margin=', 'fig.update_layout(\n                    **get_plotly_theme(),\n                    margin=', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated app.py charts")
