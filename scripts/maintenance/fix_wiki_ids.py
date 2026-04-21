with open('frontend/src/pages/WikiPage.tsx', 'r') as f:
    text = f.read()

text = text.replace('<Panel defaultSize={20} minSize={1}>', '<Panel id="wiki-index-panel" defaultSize={20} minSize={1}>')
text = text.replace('<Panel defaultSize={45} minSize={1}>', '<Panel id="wiki-content-panel" defaultSize={45} minSize={1}>')
text = text.replace('<Panel defaultSize={35} minSize={1}>', '<Panel id="wiki-graph-panel" defaultSize={35} minSize={1}>')

with open('frontend/src/pages/WikiPage.tsx', 'w') as f:
    f.write(text)
