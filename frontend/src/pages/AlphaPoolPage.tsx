import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useRef, useState } from 'react';
import {
  Panel,
  Group,
  type PanelImperativeHandle,
} from 'react-resizable-panels';
import { ResizeHandle } from '../components/ResizeHandle';
import { JsonView } from '../components/JsonView';
import { MetricGrid } from '../components/MetricGrid';
import { SectionCard } from '../components/SectionCard';
import { Sparkline } from '../components/Sparkline';
import { api, getErrorMessage } from '../lib/api';
import type { FactorSummary } from '../types';

const FACTOR_PAGE_SIZE = 50;

export function AlphaPoolPage() {
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedParentIds, setSelectedParentIds] = useState<string[]>([]);
  const [crossoverMessage, setCrossoverMessage] = useState('');
  const [detailCollapsed, setDetailCollapsed] = useState(false);
  const detailPanelRef = useRef<PanelImperativeHandle | null>(null);
  const queryClient = useQueryClient();
  const factorsOffset = page * FACTOR_PAGE_SIZE;
  const factors = useQuery({
    queryKey: ['factors', factorsOffset, FACTOR_PAGE_SIZE],
    queryFn: () =>
      api.listFactors({ offset: factorsOffset, limit: FACTOR_PAGE_SIZE }),
    placeholderData: keepPreviousData,
    refetchInterval: 10000,
  });
  const factorDetail = useQuery({
    queryKey: ['factor', selectedId],
    queryFn: () => api.getFactor(selectedId!),
    enabled: Boolean(selectedId),
  });
  const factorItems = factors.data?.items ?? [];
  const hasNextPage =
    (factors.data?.next_offset ?? 0) < (factors.data?.total ?? 0);
  const crossoverMutation = useMutation({
    mutationFn: () =>
      api.crossoverFactors({
        factor_ids: selectedParentIds,
        crossover_iterations: 1,
      }),
    onSuccess: (data) => {
      const factor = data.factor as Record<string, unknown> | undefined;
      const factorId = typeof factor?.id === 'string' ? factor.id : '';
      const status = String(data.status ?? '');
      const reason = String(data.reason ?? '');
      setCrossoverMessage(
        status === 'accepted' && factorId
          ? `Accepted hybrid factor ${factorId}.`
          : `Crossover rejected: ${reason || 'no accepted factor'}.`,
      );
      if (status === 'accepted' && factorId) {
        setSelectedId(factorId);
        setSelectedParentIds([]);
        if (detailCollapsed) {
          detailPanelRef.current?.expand();
          setDetailCollapsed(false);
        }
      }
      void queryClient.invalidateQueries({ queryKey: ['factors'] });
      void queryClient.invalidateQueries({ queryKey: ['factor'] });
    },
    onError: (error) => setCrossoverMessage(getErrorMessage(error)),
  });

  function toggleParent(factorId: string) {
    setSelectedParentIds((current) => {
      if (current.includes(factorId)) {
        return current.filter((id) => id !== factorId);
      }
      if (current.length >= 2) {
        return [current[1], factorId];
      }
      return [...current, factorId];
    });
  }

  return (
    <Group orientation="horizontal" className="panel-container">
      <Panel id="pool-list-panel" defaultSize={35} minSize={20}>
        <SectionCard
          title="Alpha Pool"
          actions={
            <div className="button-group wrap">
              <button
                type="button"
                className="button"
                disabled={
                  selectedParentIds.length === 1 || crossoverMutation.isPending
                }
                onClick={() => {
                  setCrossoverMessage('');
                  crossoverMutation.mutate();
                }}
              >
                {crossoverMutation.isPending
                  ? 'Crossing...'
                  : selectedParentIds.length >= 2
                    ? 'Crossover Selected'
                    : 'Crossover Top 2'}
              </button>
              <button
                type="button"
                className="button"
                onClick={() => {
                  if (detailCollapsed) {
                    detailPanelRef.current?.expand();
                    setDetailCollapsed(false);
                  } else {
                    detailPanelRef.current?.collapse();
                    setDetailCollapsed(true);
                  }
                }}
              >
                {detailCollapsed ? 'Show Detail' : 'Hide Detail'}
              </button>
            </div>
          }
        >
          {factors.isPending && !factors.data ? (
            <div className="status-block loading">Loading alpha pool...</div>
          ) : null}
          {factors.isError ? (
            <div className="status-block error">
              {getErrorMessage(factors.error)}
            </div>
          ) : null}
          {crossoverMessage ? (
            <div className="status-block">{crossoverMessage}</div>
          ) : null}
          {selectedParentIds.length === 1 ? (
            <div className="status-block loading">
              Select one more parent factor, or clear the current selection to
              use top 2.
            </div>
          ) : null}
          <div className="list">
            {factorItems.map((factor: FactorSummary) => (
              <div
                key={factor.id}
                className={`list-row ${selectedId === factor.id ? 'selected' : ''}`}
              >
                <label className="factor-parent-toggle">
                  <input
                    type="checkbox"
                    checked={selectedParentIds.includes(factor.id)}
                    onChange={() => toggleParent(factor.id)}
                  />
                  Parent
                </label>
                <button
                  type="button"
                  className="button-reset factor-row-main"
                  onClick={() => {
                    setSelectedId(factor.id);
                    if (detailCollapsed) {
                      detailPanelRef.current?.expand();
                      setDetailCollapsed(false);
                    }
                  }}
                >
                  <strong>{factor.id}</strong>
                  <p className="muted">{factor.hypothesis}</p>
                </button>
                <span className="factor-row-ic">
                  {factor.ic?.toFixed?.(4) ?? '-'}
                </span>
              </div>
            ))}
            {!factors.isPending && !factorItems.length ? (
              <p className="muted">No factors on this page.</p>
            ) : null}
          </div>
          <div className="pagination-bar">
            <button
              className="button"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              Prev
            </button>
            <span className="pagination-summary">
              Page {page + 1}
              {typeof factors.data?.total === 'number'
                ? ` · ${factors.data.total} factors`
                : ''}
            </span>
            <button
              className="button"
              disabled={!hasNextPage}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </SectionCard>
      </Panel>
      <ResizeHandle />
      <Panel
        id="pool-detail-panel"
        defaultSize={65}
        minSize={30}
        collapsible
        collapsedSize={0}
        panelRef={detailPanelRef}
        onResize={(size) => setDetailCollapsed(size.asPercentage <= 0.1)}
      >
        <SectionCard
          title="Factor Detail"
          actions={
            <button
              type="button"
              className="button"
              onClick={() => {
                if (detailCollapsed) {
                  detailPanelRef.current?.expand();
                  setDetailCollapsed(false);
                } else {
                  detailPanelRef.current?.collapse();
                  setDetailCollapsed(true);
                }
              }}
            >
              {detailCollapsed ? 'Expand' : 'Collapse'}
            </button>
          }
        >
          {factorDetail.isError ? (
            <div className="status-block error">
              {getErrorMessage(factorDetail.error)}
            </div>
          ) : null}
          {factorDetail.isPending && selectedId ? (
            <div className="status-block loading">Loading factor detail...</div>
          ) : null}
          {factorDetail.data ? (
            <div className="stack">
              <MetricGrid
                metrics={
                  (factorDetail.data.metrics as Record<string, unknown>) ?? {}
                }
              />
              <Sparkline
                title="Cumulative Returns"
                returns={
                  (factorDetail.data.returns as Record<string, number>) ?? {}
                }
              />
              <JsonView value={factorDetail.data} />
            </div>
          ) : (
            <p className="muted">Select a factor to inspect it.</p>
          )}
        </SectionCard>
      </Panel>
    </Group>
  );
}
