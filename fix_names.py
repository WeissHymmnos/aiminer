import os
import re

for root, dirs, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            # Replace PanelGroup with Group
            content = content.replace('PanelGroup', 'Group')
            # Replace PanelResizeHandle with Separator (if any left)
            content = content.replace('PanelResizeHandle', 'Separator')
            # Replace direction="horizontal" with orientation="horizontal"
            content = content.replace('direction="horizontal"', 'orientation="horizontal"')
            # Replace direction="vertical" with orientation="vertical"
            content = content.replace('direction="vertical"', 'orientation="vertical"')
            
            with open(path, 'w') as f:
                f.write(content)
