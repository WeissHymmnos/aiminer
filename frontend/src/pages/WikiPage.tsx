import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ForceGraph2D from "react-force-graph-2d";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Panel, Group } from "react-resizable-panels";
import { CodeEditor } from "../components/CodeEditor";
import { JsonView } from "../components/JsonView";
import { ResizeHandle } from "../components/ResizeHandle";
import { SectionCard } from "../components/SectionCard";
import { api, getErrorMessage } from "../lib/api";
import type { WikiGraphEdge, WikiGraphNode } from "../types";

type Mode = "global" | "local";
type OperationResult = {
  label: string;
  payload: unknown;
};
type MarkdownNode = {
  type: string;
  value?: string;
  url?: string;
  title?: string | null;
  children?: MarkdownNode[];
};
type WikiDirtyWindow = Window & {
  __aiminerConfirmWikiDiscard?: () => boolean;
};

const WIKI_INDEX_PAGE_SIZE = 50;

function colorForType(type: string) {
  if (type === "strategy_family") return "#a6da95";
  if (type === "market_profile") return "#f5a97f";
  if (type === "technical_ref") return "#8aadf4";
  return "#c6a0f6";
}

function parseFrontmatter(text: string) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) {
    return { metadata: {} as Record<string, unknown>, content: text };
  }

  const metadata: Record<string, unknown> = {};
  for (const rawLine of match[1].split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const separatorIndex = line.indexOf(":");
    if (separatorIndex === -1) {
      continue;
    }
    const key = line.slice(0, separatorIndex).trim();
    let value: unknown = line.slice(separatorIndex + 1).trim();

    if (typeof value === "string" && ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))) {
      value = value.slice(1, -1);
    } else if (typeof value === "string" && value.startsWith("[") && value.endsWith("]")) {
      value = value
        .slice(1, -1)
        .split(",")
        .map((item) => item.trim().replace(/^["']|["']$/g, ""))
        .filter(Boolean);
    } else if (value === "true") {
      value = true;
    } else if (value === "false") {
      value = false;
    } else if (value === "null" || value === "") {
      value = null;
    } else if (typeof value === "string" && !Number.isNaN(Number(value))) {
      value = Number(value);
    }

    metadata[key] = value;
  }

  return { metadata, content: match[2] };
}

function normalizeWikiLinkTarget(value: string) {
  return value.trim().replace(/\.md$/i, "").replace(/^\/+/, "");
}

function splitWikiLinks(value: string) {
  const nodes: MarkdownNode[] = [];
  const regex = /\[\[([^\]\n]+)\]\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(value))) {
    const [raw, inner] = match;
    const [targetText, labelText] = inner.split("|");
    const target = normalizeWikiLinkTarget(targetText ?? "");
    if (!target) {
      continue;
    }
    if (match.index > lastIndex) {
      nodes.push({ type: "text", value: value.slice(lastIndex, match.index) });
    }
    nodes.push({
      type: "link",
      url: `wiki:${encodeURIComponent(target)}`,
      title: null,
      children: [{ type: "text", value: (labelText ?? target).trim() || target }],
    });
    lastIndex = match.index + raw.length;
  }

  if (!nodes.length) {
    return null;
  }
  if (lastIndex < value.length) {
    nodes.push({ type: "text", value: value.slice(lastIndex) });
  }
  return nodes;
}

function transformWikiLinks(node: MarkdownNode) {
  if (!node.children?.length) {
    return;
  }
  const nextChildren: MarkdownNode[] = [];
  for (const child of node.children) {
    if (child.type === "text" && typeof child.value === "string") {
      nextChildren.push(...(splitWikiLinks(child.value) ?? [child]));
      continue;
    }
    transformWikiLinks(child);
    nextChildren.push(child);
  }
  node.children = nextChildren;
}

function remarkWikiLinks() {
  return (tree: MarkdownNode) => transformWikiLinks(tree);
}

export function WikiPage() {
  const [indexPage, setIndexPage] = useState(0);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("global");
  const [isEditing, setIsEditing] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [loadedSlug, setLoadedSlug] = useState<string | null>(null);
  const [staleDays, setStaleDays] = useState("30");
  const [migrateDryRun, setMigrateDryRun] = useState(true);
  const [operationResult, setOperationResult] = useState<OperationResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 420, height: 640 });
  const queryClient = useQueryClient();
  const indexOffset = indexPage * WIKI_INDEX_PAGE_SIZE;

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
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
    queryKey: ["wiki-index", indexOffset, WIKI_INDEX_PAGE_SIZE],
    queryFn: () => api.wikiIndex({ offset: indexOffset, limit: WIKI_INDEX_PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });
  const graph = useQuery({
    queryKey: ["wiki-graph"],
    queryFn: api.wikiGraph,
  });
  const indexItems = index.data?.items ?? [];
  const initialSlug = (indexItems[0]?.slug as string | undefined) ?? null;
  const slug = selectedSlug ?? initialSlug;
  const page = useQuery({
    queryKey: ["wiki-page", slug],
    queryFn: () => api.wikiPage(slug!),
    enabled: Boolean(slug),
  });
  const isDirty = isEditing && draftText !== (page.data ?? "");

  function confirmDiscardChanges() {
    return !isDirty || window.confirm("Discard unsaved wiki edits?");
  }

  function selectWikiSlug(nextSlug: string) {
    if (!confirmDiscardChanges()) {
      return;
    }
    setSelectedSlug(nextSlug);
    setIsEditing(false);
    setDraftText("");
    setLoadedSlug(null);
  }

  function setWikiIndexPage(nextPage: number | ((page: number) => number)) {
    if (!confirmDiscardChanges()) {
      return;
    }
    setIndexPage(nextPage);
    if (!selectedSlug) {
      setIsEditing(false);
      setDraftText("");
      setLoadedSlug(null);
    }
  }

  useEffect(() => {
    if (!page.data || !slug) {
      return;
    }
    if (!isEditing || loadedSlug !== slug) {
      setDraftText(page.data);
      setLoadedSlug(slug);
    }
  }, [isEditing, loadedSlug, page.data, slug]);

  useEffect(() => {
    if (!isDirty) {
      return;
    }
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  useEffect(() => {
    const targetWindow = window as WikiDirtyWindow;
    targetWindow.__aiminerConfirmWikiDiscard = confirmDiscardChanges;
    return () => {
      if (targetWindow.__aiminerConfirmWikiDiscard === confirmDiscardChanges) {
        delete targetWindow.__aiminerConfirmWikiDiscard;
      }
    }
  });

  const saveMutation = useMutation({
    mutationFn: ({ nextSlug, content }: { nextSlug: string; content: string }) => api.updateWikiPage(nextSlug, content),
    onSuccess: (payload) => {
      setErrorMessage("");
      setIsEditing(false);
      setOperationResult({ label: "Save Result", payload });
      void queryClient.invalidateQueries({ queryKey: ["wiki-page", slug] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-index"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-graph"] });
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });
  const lintMutation = useMutation({
    mutationFn: () => api.wikiLint(Number(staleDays) || 30),
    onSuccess: (payload) => {
      setErrorMessage("");
      setOperationResult({ label: "Lint Report", payload });
      void queryClient.invalidateQueries({ queryKey: ["wiki-index"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-graph"] });
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });
  const migrateMutation = useMutation({
    mutationFn: () => api.wikiMigrate(migrateDryRun),
    onSuccess: (payload) => {
      setErrorMessage("");
      setOperationResult({ label: migrateDryRun ? "Migration Dry Run" : "Migration Result", payload });
      void queryClient.invalidateQueries({ queryKey: ["wiki-index"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-graph"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-page"] });
    },
    onError: (error) => setErrorMessage((error as Error).message),
  });

  const parsedPage = useMemo(() => parseFrontmatter(page.data ?? ""), [page.data]);

  const graphData = useMemo(() => {
    const nodes = graph.data?.nodes ?? [];
    const edges = graph.data?.edges ?? [];

    const getId = (value: string | WikiGraphNode) =>
      typeof value === "object" && value !== null ? value.slug || value.id : value;

    if (mode === "global" || !slug) {
      return { nodes, links: edges };
    }

    const allowed = new Set<string>([slug]);
    for (const edge of edges) {
      const sourceId = getId(edge.source);
      const targetId = getId(edge.target);
      if (sourceId === slug) {
        allowed.add(targetId);
      }
      if (targetId === slug) {
        allowed.add(sourceId);
      }
    }

    return {
      nodes: nodes.filter((node) => allowed.has(node.slug)),
      links: edges.filter((edge) => allowed.has(getId(edge.source)) && allowed.has(getId(edge.target))),
    };
  }, [graph.data, mode, slug]);

  const busy = saveMutation.isPending || lintMutation.isPending || migrateMutation.isPending;
  const hasNextIndexPage = (index.data?.next_offset ?? 0) < (index.data?.total ?? 0);

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="wiki-index-panel" defaultSize={24} minSize={14}>
        <SectionCard
          title="Wiki Index"
          className="wiki-index"
          actions={
            <div className="button-group">
              <button className="button" disabled={busy} onClick={() => lintMutation.mutate()}>
                Lint
              </button>
              <button className="button" disabled={busy} onClick={() => migrateMutation.mutate()}>
                Migrate
              </button>
            </div>
          }
        >
          {index.isPending && !index.data ? <div className="status-block loading">Loading wiki index...</div> : null}
          {index.isError ? <div className="status-block error">{getErrorMessage(index.error)}</div> : null}
          <div className="wiki-toolbar">
            <label className="field">
              Stale Days
              <input value={staleDays} onChange={(event) => setStaleDays(event.target.value)} />
            </label>
            <label className="field-toggle">
              <span>Migrate Dry Run</span>
              <input
                type="checkbox"
                checked={migrateDryRun}
                onChange={(event) => setMigrateDryRun(event.target.checked)}
              />
            </label>
          </div>
          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          {operationResult ? (
            <div className="stack wiki-operation-result">
              <strong>{operationResult.label}</strong>
              <JsonView value={operationResult.payload} maxLines={24} />
            </div>
          ) : (
            <p className="muted">Lint and migration results appear here.</p>
          )}
          <div className="list">
            {indexItems.map((item) => {
              const itemSlug = String(item.slug ?? "");
              return (
                <button
                  type="button"
                  key={itemSlug}
                  className={`list-row button-reset ${slug === itemSlug ? "selected" : ""}`}
                  onClick={() => selectWikiSlug(itemSlug)}
                >
                  <div>
                    <strong>{String(item.title ?? itemSlug)}</strong>
                    <p className="muted">{String(item.type ?? "")}</p>
                  </div>
                </button>
              );
            })}
            {!index.isPending && !indexItems.length ? <p className="muted">No wiki pages on this page.</p> : null}
          </div>
          <div className="pagination-bar">
            <button className="button" disabled={indexPage === 0} onClick={() => setWikiIndexPage((page) => Math.max(0, page - 1))}>
              Prev
            </button>
            <span className="pagination-summary">
              Page {indexPage + 1}
              {typeof index.data?.total === "number" ? ` · ${index.data.total} pages` : ""}
            </span>
            <button className="button" disabled={!hasNextIndexPage} onClick={() => setWikiIndexPage((page) => page + 1)}>
              Next
            </button>
          </div>
        </SectionCard>
      </Panel>

      <ResizeHandle />

      <Panel id="wiki-content-panel" defaultSize={41} minSize={24}>
        <SectionCard
          title={slug ? `Wiki · ${slug}` : "Wiki Page"}
          className="wiki-body"
          actions={
            slug ? (
              isEditing ? (
                <div className="button-group">
                  <button
                    className="button"
                    disabled={saveMutation.isPending}
                    onClick={() => saveMutation.mutate({ nextSlug: slug, content: draftText })}
                  >
                    Save
                  </button>
                  <button
                    className="button"
                    disabled={saveMutation.isPending}
                    onClick={() => {
                      setDraftText(page.data ?? "");
                      setIsEditing(false);
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button className="button" disabled={page.isPending} onClick={() => setIsEditing(true)}>
                  Edit Raw Markdown
                </button>
              )
            ) : null
          }
        >
          {page.isError ? <div className="status-block error">{getErrorMessage(page.error)}</div> : null}
          {slug ? (
            isEditing ? (
              <div className="stack">
                <p className="muted">Editing raw markdown with frontmatter. Save writes back to the wiki vault file directly.</p>
                <CodeEditor value={draftText} onChange={setDraftText} language="markdown" height="100%" />
              </div>
            ) : (
              <div className="stack">
                {page.isPending && !page.data ? <div className="status-block loading">Loading wiki page...</div> : null}
                {Object.keys(parsedPage.metadata).length > 0 ? (
                  <div className="wiki-metadata">
                    <div className="metric-grid">
                      {Object.entries(parsedPage.metadata).map(([key, value]) => {
                        if (key === "title" || key === "summary") {
                          return null;
                        }
                        return (
                          <div className="metric" key={key}>
                            <span>{key}</span>
                            <strong>{Array.isArray(value) ? value.join(", ") : String(value)}</strong>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
                <div className="markdown-body">
                  <h1>{String(parsedPage.metadata.title ?? slug)}</h1>
                  {parsedPage.metadata.summary ? <p className="muted">{String(parsedPage.metadata.summary)}</p> : null}
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkWikiLinks]}
                    components={{
                      a: ({ href, children, ...props }) => {
                        if (href?.startsWith("wiki:")) {
                          const nextSlug = decodeURIComponent(href.slice("wiki:".length));
                          return (
                            <button
                              type="button"
                              className="wiki-link"
                              onClick={() => selectWikiSlug(nextSlug)}
                            >
                              {children}
                            </button>
                          );
                        }
                        return (
                          <a href={href} target="_blank" rel="noreferrer" {...props}>
                            {children}
                          </a>
                        );
                      },
                    }}
                  >
                    {parsedPage.content}
                  </ReactMarkdown>
                </div>
              </div>
            )
          ) : (
            <p className="muted">Select a page.</p>
          )}
        </SectionCard>
      </Panel>

      <ResizeHandle />

      <Panel id="wiki-graph-panel" defaultSize={35} minSize={18}>
        <SectionCard
          title="Obsidian Graph"
          className="wiki-graph"
          actions={
            <div className="button-group">
              <button className={`button ${mode === "global" ? "active" : ""}`} onClick={() => setMode("global")}>
                Global
              </button>
              <button className={`button ${mode === "local" ? "active" : ""}`} onClick={() => setMode("local")}>
                Local
              </button>
            </div>
          }
        >
          {graph.isError ? <div className="status-block error">{getErrorMessage(graph.error)}</div> : null}
          {graph.isPending && !graph.data ? <div className="status-block loading">Loading graph...</div> : null}
          <div className="graph-container" ref={containerRef}>
            <ForceGraph2D
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              nodeLabel={(node) => {
                const typedNode = node as WikiGraphNode;
                return `${typedNode.title}\n${typedNode.type}\n${typedNode.status}`;
              }}
              nodeCanvasObject={(node, ctx, scale) => {
                const typedNode = node as WikiGraphNode;
                const radius = 1.2 + Math.sqrt(typedNode.degree ?? 0) * 0.6;

                ctx.beginPath();
                ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
                ctx.fillStyle = colorForType(typedNode.type);
                ctx.fill();

                if (slug === typedNode.slug) {
                  ctx.strokeStyle = "#f5a97f";
                  ctx.lineWidth = 2 / scale;
                  ctx.stroke();
                }

                if (scale > 2.5) {
                  const label = typedNode.title;
                  const fontSize = 11 / scale;
                  ctx.font = `${fontSize}px "IBM Plex Sans", sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = "rgba(202, 211, 245, 0.7)";
                  ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + radius + fontSize);
                }
              }}
              linkColor={(link) => ((link as WikiGraphEdge).kind === "related" ? "#8aadf4" : "#5b6078")}
              onNodeClick={(node) => {
                selectWikiSlug((node as WikiGraphNode).slug);
              }}
            />
          </div>
        </SectionCard>
      </Panel>
    </Group>
  );
}
