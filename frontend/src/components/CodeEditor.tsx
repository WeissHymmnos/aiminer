import Editor, { type OnMount } from "@monaco-editor/react";
import { useState } from "react";
import "../lib/monaco";

type Props = {
  value: string;
  onChange: (value: string) => void;
  language?: "python" | "json" | "markdown" | "plaintext";
  height?: number | string;
  minimap?: boolean;
  readOnly?: boolean;
};

const themeName = "aiminer-night";

export function CodeEditor({
  value,
  onChange,
  language = "plaintext",
  height = 240,
  minimap = false,
  readOnly = false,
}: Props) {
  const [hasError, setHasError] = useState(false);

  const handleMount: OnMount = (editor, monacoInstance) => {
    try {
      editor.addCommand(monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.KeyS, () => {
        editor.getAction("editor.action.formatDocument")?.run().catch(() => undefined);
      });
    } catch (e) {
      console.warn("Monaco shortcut setup failed:", e);
    }
  };

  if (hasError) {
    return (
      <div className="editor-shell" style={{ height: typeof height === "number" ? `${height}px` : height }}>
        <textarea
          className="code-block"
          style={{
            width: "100%",
            height: "100%",
            resize: "vertical",
            border: "none",
            outline: "none",
            boxSizing: "border-box",
            padding: "12px",
          }}
          value={value}
          readOnly={readOnly}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
        />
      </div>
    );
  }

  return (
    <div className="editor-shell" style={{ height: typeof height === "number" ? `${height}px` : height }}>
      <Editor
        theme={themeName}
        language={language}
        value={value}
        height={height}
        loading={<div className="editor-loading muted">Loading editor...</div>}
        onMount={handleMount}
        beforeMount={(editorMonaco) => {
          try {
            editorMonaco.editor.defineTheme(themeName, {
              base: "vs-dark",
              inherit: true,
              rules: [
                { token: "comment", foreground: "6E738D" },
                { token: "keyword", foreground: "C6A0F6" },
                { token: "string", foreground: "A6DA95" },
                { token: "number", foreground: "F5A97F" },
              ],
              colors: {
                "editor.background": "#181926",
                "editor.foreground": "#CAD3F5",
                "editor.lineHighlightBackground": "#24273A",
                "editorLineNumber.foreground": "#6E738D",
                "editorLineNumber.activeForeground": "#B7BDF8",
                "editorCursor.foreground": "#F5BDE6",
                "editor.selectionBackground": "#494D6499",
                "editor.inactiveSelectionBackground": "#363A4F99",
                "editorIndentGuide.background1": "#363A4F",
                "editorIndentGuide.activeBackground1": "#5B6078",
              },
            });
          } catch (e) {
            console.warn("Monaco theme definition error:", e);
          }
        }}
        options={{
          readOnly,
          minimap: { enabled: minimap },
          roundedSelection: true,
          automaticLayout: true,
          padding: { top: 12, bottom: 12 },
          fontFamily: '"IBM Plex Mono", monospace',
          fontLigatures: true,
          fontSize: 13,
          lineHeight: 20,
          scrollBeyondLastLine: false,
          renderWhitespace: "selection",
          wordWrap: "on",
          tabSize: language === "json" ? 2 : 4,
          smoothScrolling: true,
          scrollbar: {
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8,
          },
        }}
        onChange={(nextValue) => onChange(nextValue ?? "")}
      />
    </div>
  );
}
