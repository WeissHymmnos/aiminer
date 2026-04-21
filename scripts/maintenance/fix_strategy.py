import re

with open('frontend/src/pages/StrategyBacktestPage.tsx', 'r') as f:
    text = f.read()

# Replace the top-level <div className="page-grid two-col"> inside return (
text = re.sub(
    r'  return \(\n    <div className="page-grid two-col">\n      <SectionCard',
    r'  return (\n    <PanelGroup direction="horizontal" className="panel-container">\n      <Panel defaultSize={50} minSize={30}>\n      <SectionCard',
    text,
    count=1
)

with open('frontend/src/pages/StrategyBacktestPage.tsx', 'w') as f:
    f.write(text)
