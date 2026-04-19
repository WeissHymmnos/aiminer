import { useQuery } from "@tanstack/react-query";
import ForceGraph2D from "react-force-graph-2d";
import { useMemo, useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Panel, Group } from "react-resizable-panels";
import { ResizeHandle } from "../components/ResizeHandle";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { WikiGraphEdge, WikiGraphNode } from "../types";

type Mode = "global" | "local";

function colorForType(type: string) {
  if (type === "strategy_family") return "#a6da95"; // ctp-green
  if (type === "market_profile") return "#f5a97f"; // ctp-peach
  if (type === "technical_ref") return "#8aadf4"; // ctp-blue
  return "#c6a0f6"; // ctp-mauve
}

export function WikiPage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("global");
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;
    
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });
    
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const index = useQuery({
    queryKey: ["wiki-index"],
    queryFn: api.wikiIndexAll,
  });
  const graph = useQuery({
    queryKey: ["wiki-graph"],
    queryFn: api.wikiGraph,
  });
  const initialSlug = (index.data?.[0]?.slug as string | undefined) ?? null;
  const slug = selectedSlug ?? initialSlug;
  const page = useQuery({
    queryKey: ["wiki-page", slug],
    queryFn: () => api.wikiPage(slug!),
    enabled: Boolean(slug),
  });

  const parsedPage = useMemo(() => {
    if (!page.data) return { metadata: {}, content: "" };
    
    // Robust Frontmatter regex (handles different line endings and whitespace)
    const fmRegex = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/;
    const match = page.data.match(fmRegex);
    
    if (match) {
      const yaml = match[1];
      const content = match[2];
      const metadata: Record<string, any> = {};
      
      // Improved manual YAML parser
      yaml.split("\n").forEach(line => {
        const trimmedLine = line.trim();
        if (!trimmedLine || trimmedLine.startsWith("#")) return;

        const separatorIndex = trimmedLine.indexOf(":");
        if (separatorIndex === -1) return;

        const key = trimmedLine.substring(0, separatorIndex).trim();
        let value: any = trimmedLine.substring(separatorIndex + 1).trim();
        
        // Remove quotes
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
          value = value.substring(1, value.length - 1);
        }
        
        // Handle basic types and arrays
        if (value.startsWith("[") && value.endsWith("]")) {
          try {
            // Convert YAML array notation to JSON-like for parsing
            const sanitizedArray = value.replace(/'/g, '"');
            value = JSON.parse(sanitizedArray);
          } catch(e) {
            // Fallback for simple comma-separated if JSON parse fails
            value = value.slice(1, -1).split(",").map((s: string) => s.trim().replace(/^["']|["']$/g, ""));
          }
        } else if (value.toLowerCase() === "true") {
          value = true;
        } else if (value.toLowerCase() === "false") {
          value = false;
        } else if (value === "" || value === "null") {
          value = null;
        } else if (!isNaN(Number(value)) && value.trim() !== "") {
          value = Number(value);
        }
        
        metadata[key] = value;
      });
      
      return { metadata, content };
    }
    
    return { metadata: {}, content: page.data };
  }, [page.data]);

  const graphData = useMemo(() => {
    const nodes = graph.data?.nodes ?? [];
    const edges = graph.data?.edges ?? [];
    
    // Helper to extract string ID whether edge endpoint is a string or a mutated node object
    const getId = (val: any) => (typeof val === "object" && val !== null ? val.slug || val.id : val);
    
    if (mode === "global" || !slug) {
      return { nodes, links: edges };
    }
    
    const allowed = new Set<string>([slug]);
    for (const edge of edges) {
      const sourceId = getId(edge.source);
      const targetId = getId(edge.target);
      if (sourceId === slug) allowed.add(targetId);
      if (targetId === slug) allowed.add(sourceId);
    }
    
    return {
      nodes: nodes.filter((node) => allowed.has(node.slug)),
      links: edges.filter((edge) => {
        const sourceId = getId(edge.source);
        const targetId = getId(edge.target);
        return allowed.has(sourceId) && allowed.has(targetId);
      }),
    };
  }, [graph.data, mode, slug]);

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="wiki-index-panel" defaultSize={20} minSize={1}>
        <SectionCard title="Wiki Index" className="wiki-index">
          <div className="list">
            {(index.data ?? []).map((item) => {
              const itemSlug = String(item.slug ?? "");
              return (
                <button
                  type="button"
                  key={itemSlug}
                  className={`list-row button-reset ${slug === itemSlug ? "selected" : ""}`}
                  onClick={() => setSelectedSlug(itemSlug)}
                >
                  <div>
                    <strong>{String(item.title ?? itemSlug)}</strong>
                    <p className="muted">{String(item.type ?? "")}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </SectionCard>
      </Panel>
      <ResizeHandle />
      <Panel id="wiki-content-panel" defaultSize={45} minSize={1}>
        <SectionCard title={slug ? `Wiki · ${slug}` : "Wiki Page"} className="wiki-body">
          {page.data ? (
            <div className="stack">
              {Object.keys(parsedPage.metadata).length > 0 && (
                <div className="wiki-metadata">
                  <div className="metric-grid">
                    {Object.entries(parsedPage.metadata).map(([key, value]) => {
                      if (key === "title" || key === "summary") return null;
                      return (
                        <div className="metric" key={key}>
                          <span>{key}</span>
                          <strong>{Array.isArray(value) ? value.join(", ") : String(value)}</strong>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              <div className="markdown-body">
                <h1>{parsedPage.metadata.title || slug}</h1>
                {parsedPage.metadata.summary && <p className="muted">{parsedPage.metadata.summary}</p>}
                <ReactMarkdown>{parsedPage.content}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <p className="muted">Select a page.</p>
          )}
        </SectionCard>
      </Panel>
      <ResizeHandle />
...
      <Panel id="wiki-graph-panel" defaultSize={35} minSize={1}>
        <SectionCard
          title="Obsidian Graph"
          className="wiki-graph"
          actions={
            <div className="button-group">
              <button className="button" onClick={() => setMode("global")}>Global</button>
              <button className="button" onClick={() => setMode("local")}>Local</button>
            </div>
          }
        >
          <div className="graph-container" ref={containerRef}>
            <ForceGraph2D
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              nodeLabel={(node) =>
                `${(node as WikiGraphNode).title}\n${(node as WikiGraphNode).type}\n${(node as WikiGraphNode).status}`
              }              nodeCanvasObject={(node, ctx, scale) => {
                const typedNode = node as WikiGraphNode;
                // Smaller nodes, scaling with sqrt of degree for a more natural feel
                const radius = 1.2 + Math.sqrt(typedNode.degree ?? 0) * 0.6;

                ctx.beginPath();
                ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
                ctx.fillStyle = colorForType(typedNode.type);
                ctx.fill();

                // Highlight selected node with Catppuccin Peach
                if (slug === typedNode.slug) {
                  ctx.strokeStyle = "#f5a97f"; 
                  ctx.lineWidth = 2 / scale;
                  ctx.stroke();
                }

                // Draw labels only when zoomed in to keep the graph clean
                if (scale > 2.5) {
                  const label = typedNode.title;
                  const fontSize = 11 / scale;
                  ctx.font = `${fontSize}px "IBM Plex Sans", sans-serif`;
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = "rgba(202, 211, 245, 0.7)"; // ctp-text with opacity
                  ctx.fillText(label, (node.x ?? 0), (node.y ?? 0) + radius + fontSize);
                }
              }}              linkColor={(link) => ((link as WikiGraphEdge).kind === "related" ? "#8aadf4" : "#5b6078")}
              onNodeClick={(node) => setSelectedSlug((node as WikiGraphNode).slug)}
            />
          </div>
        </SectionCard>
      </Panel>
    </Group>
  );
}
