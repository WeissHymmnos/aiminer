import os

files = [
    'frontend/src/pages/AlphaPoolPage.tsx',
    'frontend/src/pages/ManualBacktestPage.tsx',
    'frontend/src/pages/StrategyBacktestPage.tsx',
    'frontend/src/pages/SwarmRunDetailPage.tsx'
]

for file in files:
    if not os.path.exists(file): continue
    with open(file, 'r') as f:
        text = f.read()
    
    # Add id to the first Panel (usually left/top)
    text = text.replace('<Panel defaultSize={35} minSize={20}>', '<Panel id="pool-list-panel" defaultSize={35} minSize={20}>')
    text = text.replace('<Panel defaultSize={65} minSize={30}>', '<Panel id="pool-detail-panel" defaultSize={65} minSize={30}>')
    
    text = text.replace('<Panel defaultSize={50} minSize={30}>', '<Panel id="left-panel" defaultSize={50} minSize={20}>', 1)
    text = text.replace('<Panel defaultSize={50} minSize={30}>', '<Panel id="right-panel" defaultSize={50} minSize={20}>', 1)
    
    with open(file, 'w') as f:
        f.write(text)
