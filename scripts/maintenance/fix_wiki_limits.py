with open('frontend/src/pages/WikiPage.tsx', 'r') as f:
    text = f.read()

# Replace minSize values
text = text.replace('minSize={10}', 'minSize={1}')
text = text.replace('minSize={30}', 'minSize={1}')
text = text.replace('minSize={20}', 'minSize={1}')

with open('frontend/src/pages/WikiPage.tsx', 'w') as f:
    f.write(text)
