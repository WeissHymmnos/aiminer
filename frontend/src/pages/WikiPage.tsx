import { useQuery } from "@tanstack/react-query";
import ForceGraph2D from "react-force-graph-2d";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { SectionCard } from "../components/SectionCard";
import { api } from "../lib/api";
import type { WikiGraphEdge, WikiGraphNode } from "../types";

type Mode = "global" | "local";

function colorForType(type: string) {
  if (type === "strategy_family") return "#0c7c59";
  if (type === "market_profile") return "#d95d39";
  if (type === "technical_ref") return "#3d5a80";
  return "#b56576";
}

export function WikiPage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("global");
  const index = useQuery({
    queryKey: ["wiki-index"],
    queryFn: api.wikiIndex,
  });
  const graph = useQuery({
    queryKey: ["wiki-graph"],
    queryFn: api.wikiGraph,
  });
  const initialSlug = (index.data?.items?.[0]?.slug as string | undefined) ?? null;
  const slug = selectedSlug ?? initialSlug;
  const page = useQuery({
    queryKey: ["wiki-page", slug],
    queryFn: () => api.wikiPage(slug!),
    enabled: Boolean(slug),
  });

  const graphData = useMemo(() => {
    const nodes = graph.data?.nodes ?? [];
    const edges = graph.data?.edges ?? [];
    if (mode === "global" || !slug) {
      return { nodes, links: edges };
    }
    const allowed = new Set<string>([slug]);
    for (const edge of edges) {
      if (edge.source === slug) allowed.add(edge.target);
      if (edge.target === slug) allowed.add(edge.source);
    }
    return {
      nodes: nodes.filter((node) => allowed.has(node.slug)),
      links: edges.filter((edge) => allowed.has(edge.source) && allowed.has(edge.target)),
    };
  }, [graph.data, mode, slug]);

  return (
    <div className="wiki-layout">
      <SectionCard title="Wiki Index" className="wiki-index">
        <div className="list">
          {(index.data?.items ?? []).map((item) => {
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

      <SectionCard title={slug ? `Wiki · ${slug}` : "Wiki Page"} className="wiki-body">
        {page.data ? <ReactMarkdown>{page.data}</ReactMarkdown> : <p className="muted">Select a page.</p>}
      </SectionCard>

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
        <div className="graph-container">
          <ForceGraph2D
            graphData={graphData}
            nodeLabel={(node) =>
              `${(node as WikiGraphNode).title}\n${(node as WikiGraphNode).type}\n${(node as WikiGraphNode).status}`
            }
            nodeCanvasObject={(node, ctx, scale) => {
              const typedNode = node as WikiGraphNode;
              const radius = 3 + Math.min(typedNode.degree ?? 0, 10);
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
              ctx.fillStyle = colorForType(typedNode.type);
              ctx.fill();
              if (slug === typedNode.slug) {
                ctx.strokeStyle = "#f3a712";
                ctx.lineWidth = 2 / scale;
                ctx.stroke();
              }
            }}
            linkColor={(link) => ((link as WikiGraphEdge).kind === "related" ? "#1d7874" : "#6c757d")}
            onNodeClick={(node) => setSelectedSlug((node as WikiGraphNode).slug)}
          />
        </div>
      </SectionCard>
    </div>
  );
}
