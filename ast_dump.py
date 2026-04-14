import ast
import os

def parse_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        return ""
    
    try:
        tree = ast.parse(code)
    except:
        return ""

    output = f"## {filepath}\n"
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            output += f"Class: {node.name}\n"
            doc = ast.get_docstring(node)
            if doc:
                output += f"  Doc: {doc.splitlines()[0]}\n"
            for n in node.body:
                if isinstance(n, ast.FunctionDef):
                    output += f"  Method: {n.name}(...)\n"
                    mdoc = ast.get_docstring(n)
                    if mdoc:
                        output += f"    Doc: {mdoc.splitlines()[0]}\n"
        elif isinstance(node, ast.FunctionDef) and not isinstance(node.parent if hasattr(node, "parent") else None, ast.ClassDef):
            # Hacky way to skip methods already covered, since ast.walk doesn't maintain parent
            # but we just want an overview.
            pass
            
    # Better logic:
    return output

def dump_project(root_dir):
    res = ""
    for root, dirs, files in os.walk(root_dir):
        if '.git' in root or '__pycache__' in root or 'venv' in root or '.pytest' in root or '.aider' in root or 'polars_plugins' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                # Correct parsing logic
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code = f.read()
                    tree = ast.parse(code)
                except:
                    continue
                res += f"### {filepath}\n"
                for node in getattr(tree, 'body', []):
                    if isinstance(node, ast.ClassDef):
                        res += f"- Class `{node.name}`:\n"
                        doc = ast.get_docstring(node)
                        if doc: res += f"  - Doc: {doc.splitlines()[0][:100]}\n"
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                res += f"  - Method `{item.name}`\n"
                                mdoc = ast.get_docstring(item)
                                if mdoc: res += f"    - Doc: {mdoc.splitlines()[0][:100]}\n"
                    elif isinstance(node, ast.FunctionDef):
                        res += f"- Function `{node.name}`\n"
                        doc = ast.get_docstring(node)
                        if doc: res += f"  - Doc: {doc.splitlines()[0][:100]}\n"
    return res

print(dump_project('.'))
