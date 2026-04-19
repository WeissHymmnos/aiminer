import { useState } from "react";

type Props = {
  value: unknown;
  maxLines?: number;
};

export function JsonView({ value, maxLines = 100 }: Props) {
  const [showFull, setShowFull] = useState(false);
  
  if (value === undefined || value === null) {
    return <pre className="code-block">null</pre>;
  }

  const jsonString = JSON.stringify(value, null, 2);
  const lines = jsonString.split("\n");
  const isLarge = lines.length > maxLines;

  const displayContent = !showFull && isLarge 
    ? lines.slice(0, maxLines).join("\n") + "\n\n... [Truncated for performance. Click below to show all] ..."
    : jsonString;

  return (
    <div className="json-view-container" style={{ display: "flex", flexDirection: "column" }}>
      <pre className="code-block" style={{ margin: 0 }}>{displayContent}</pre>
      {isLarge && (
        <button 
          className="button-reset muted" 
          style={{ 
            fontSize: "0.8rem", 
            marginTop: "8px", 
            alignSelf: "flex-start",
            textDecoration: "underline",
            padding: "4px 8px",
            borderRadius: "4px"
          }}
          onClick={() => setShowFull(!showFull)}
        >
          {showFull ? "Show Less" : `Show All (${lines.length} lines)`}
        </button>
      )}
    </div>
  );
}
