import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { BACKEND_URL } from '../backend';

const AnalysisResults = () => {
  const { addNotification, settings, setQueue } = useApp();
  const [results, setResults]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [classifying, setClassifying] = useState(false);
  const [classifyProgress, setClassifyProgress] = useState(null);
  const [error, setError]           = useState(null);
  const [lightbox, setLightbox]     = useState(null);
  const [sortKey, setSortKey]       = useState(null);   // column key to sort by
  const [sortDir, setSortDir]       = useState('asc');  // 'asc' | 'desc'
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [showHeat, setShowHeat] = useState(false);   // damage overlay toggle in lightbox
  const tableContainerRef = useRef(null);

  const groupedResults = React.useMemo(() => {
    const groups = [];
    const map = new Map();

    results.forEach(r => {
      const gId = r.group_id || r.id;
      if (!map.has(gId)) {
        map.set(gId, {
          groupId: gId,
          items: [],
          prediction: 'Good',
          confidence: 0,
        });
        groups.push(map.get(gId));
      }
      const g = map.get(gId);
      g.items.push(r);
      if (r.prediction === 'Damaged') {
        g.prediction = 'Damaged';
      }
      g.confidence = g.items.reduce((sum, item) => sum + item.confidence, 0) / g.items.length;
      // Expose timestamp from first item for sorting
      g.timestamp = g.items[0].timestamp;
    });

    // ── Sorting ──────────────────────────────────────────────────────
    if (sortKey) {
      groups.sort((a, b) => {
        let va, vb;
        if (sortKey === 'name') {
          va = (a.items.length > 1 ? 'Multi-Perspective Lens' : a.items[0].filename).toLowerCase();
          vb = (b.items.length > 1 ? 'Multi-Perspective Lens' : b.items[0].filename).toLowerCase();
        } else if (sortKey === 'state') {
          va = a.prediction; vb = b.prediction;
        } else if (sortKey === 'confidence') {
          va = a.confidence; vb = b.confidence;
        } else if (sortKey === 'timestamp') {
          va = a.timestamp; vb = b.timestamp;
        }
        if (va < vb) return sortDir === 'asc' ? -1 : 1;
        if (va > vb) return sortDir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return groups;
  }, [results, sortKey, sortDir]);

  // ── Scroll-to-top visibility ──────────────────────────────────────
  const handleTableScroll = useCallback(() => {
    if (tableContainerRef.current) {
      setShowScrollTop(tableContainerRef.current.scrollTop > 120);
    }
  }, []);

  const scrollToTop = () => {
    tableContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ── Column sort toggle ────────────────────────────────────────────
  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const SortIcon = ({ colKey }) => {
    if (sortKey !== colKey) return <span className="material-symbols-outlined text-[14px] opacity-30 ml-0.5">unfold_more</span>;
    return (
      <span className="material-symbols-outlined text-[14px] text-primary ml-0.5">
        {sortDir === 'asc' ? 'arrow_upward' : 'arrow_downward'}
      </span>
    );
  };

  const deleteResult = async (filename) => {
    if (!window.confirm(`Delete "${filename}"? This removes the image from the upload folder.`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/upload/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (res.ok) {
        setLightbox(null);
        await fetchResults();
        addNotification('info', `Deleted ${filename}`);
      } else {
        addNotification('error', 'Failed to delete image.');
      }
    } catch {
      addNotification('error', 'Cannot connect to backend.');
    }
  };

  const fetchResults = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/results`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      } else {
        setError('Could not load results.');
      }
    } catch {
      setError('Backend offline. Start the Python server on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchResults(); }, []);

  // Re-fetch when the window is focused (e.g. user clears uploads on another page then comes back)
  useEffect(() => {
    const onFocus = () => fetchResults();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);

  // Auto-refresh polling
  useEffect(() => {
    if (!settings.autoRefresh) return;
    const interval = setInterval(fetchResults, 10000); // 10s
    return () => clearInterval(interval);
  }, [settings.autoRefresh]);

  // Close lightbox on Escape key, navigate on Left/Right
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') setLightbox(null);
    if (lightbox && lightbox.group.items.length > 1) {
      if (e.key === 'ArrowLeft') {
        setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex > 0 ? prev.currentIndex - 1 : prev.group.items.length - 1 }));
      }
      if (e.key === 'ArrowRight') {
        setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex < prev.group.items.length - 1 ? prev.currentIndex + 1 : 0 }));
      }
    }
  }, [lightbox]);
  useEffect(() => {
    if (lightbox) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
      // Default to the PLAIN image. The damage-localization overlay is opt-in
      // via the "Show damage" toggle, so the default picture is never the
      // heatmap/circle view.
      setShowHeat(false);
    } else {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [lightbox, handleKeyDown]);

  const handleClassify = async () => {
    setClassifying(true);
    setClassifyProgress({ current: 0, total: 1, text: 'Initializing...' });
    
    try {
      const res = await fetch(`${BACKEND_URL}/classify-stream`, { method: 'POST' });
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data.detail || 'Classification failed.';
        alert(msg);
        addNotification('error', `Classification failed: ${msg}`);
        setClassifying(false);
        setClassifyProgress(null);
        return;
      }
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep the last incomplete line in buffer
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === 'progress') {
              setClassifyProgress({ current: data.progress, total: data.total, text: data.current });
            } else if (data.type === 'result') {
              if (data.mode) {
                await fetchResults();
                const mode = data.mode === 'mock' ? ' (mock mode — no model trained)' : '';
                addNotification('success', `Classification complete: ${data.count} image${data.count !== 1 ? 's' : ''} processed${mode}.`);
                // Mark items in the transfer queue as classified
                setQueue(prev => prev.map(item => item.status === 'queued' ? { ...item, status: 'classified' } : item));
              } else {
                 addNotification('error', data.message || 'Classification failed.');
              }
            }
          } catch (e) {
            console.error('Parse error on streaming line', e);
          }
        }
      }
    } catch {
      alert('Cannot connect to backend.');
      addNotification('error', 'Classification failed — backend is offline.');
    } finally {
      setClassifying(false);
      setClassifyProgress(null);
    }
  };

  const stateBadge = (prediction) => {
    if (prediction === 'Good') {
      return (
        <span className="inline-flex items-center gap-xs px-sm py-xs rounded-full font-label-sm text-label-sm bg-primary-container/30 text-primary">
          <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
          Good
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-xs px-sm py-xs rounded-full font-label-sm text-label-sm bg-error-container text-on-error-container">
        <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>error</span>
        Damaged
      </span>
    );
  };

  return (
    <>

      {/* ── Lightbox overlay ─────────────────────────────────────────────── */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 50,
            background: 'rgba(0,0,0,0.55)',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'fadeIn 0.18s ease',
          }}
        >
          {lightbox.group.items.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex > 0 ? prev.currentIndex - 1 : prev.group.items.length - 1 })); }}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-4 text-white hover:bg-white/20 rounded-full transition-colors z-50 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[48px]">chevron_left</span>
            </button>
          )}

          {/* Card — clicks inside do NOT close the overlay */}
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--color-surface-container-lowest, #fff)',
              borderRadius: '16px',
              boxShadow: '0 24px 64px rgba(0,0,0,0.35)',
              padding: '12px',
              maxWidth: '80vw',
              maxHeight: '80vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px',
              animation: 'scaleIn 0.18s ease',
              position: 'relative'
            }}
          >
            <img
              src={
                (() => {
                  const it = lightbox.group.items[lightbox.currentIndex];
                  if (showHeat && it.heatmap) return `${BACKEND_URL}/heatmap/${it.filename}`;
                  return `${BACKEND_URL}/thumbnail/${it.filename}`;
                })()
              }
              alt={lightbox.group.items[lightbox.currentIndex].filename}
              style={{
                maxWidth: '70vw',
                maxHeight: '65vh',
                borderRadius: '10px',
                objectFit: 'contain',
                display: 'block',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', justifyContent: 'space-between' }}>
              <div className="flex items-center gap-2">
                <span style={{ fontSize: '13px', opacity: 0.7, fontWeight: 500 }}>
                  {lightbox.group.items[lightbox.currentIndex].filename}
                </span>
                {stateBadge(lightbox.group.items[lightbox.currentIndex].prediction)}
              </div>
              <div className="flex items-center gap-2">
                {lightbox.group.items[lightbox.currentIndex].heatmap ? (
                  <button
                    type="button"
                    onClick={() => setShowHeat(v => !v)}
                    title="Toggle damage localization overlay"
                    className="flex items-center gap-xs px-sm py-xs rounded-full text-[12px] font-label-sm cursor-pointer transition-colors"
                    style={{
                      border: '1px solid var(--color-outline-variant, #ccc)',
                      color: showHeat ? 'var(--color-on-error-container, #fff)' : 'var(--color-error, #d32f2f)',
                      background: showHeat ? 'var(--color-error, #d32f2f)' : 'transparent',
                    }}
                  >
                    <span className="material-symbols-outlined text-[16px]">local_fire_department</span>
                    {showHeat ? 'Hide damage' : 'Show damage'}
                  </button>
                ) : (
                  <span className="font-label-sm text-[11px] text-secondary opacity-70">No damage overlay</span>
                )}
                <button
                  type="button"
                  onClick={() => deleteResult(lightbox.group.items[lightbox.currentIndex].filename)}
                  title="Delete this image"
                  className="flex items-center gap-xs px-sm py-xs rounded-full text-[12px] font-label-sm cursor-pointer transition-colors"
                  style={{
                    border: '1px solid var(--color-outline-variant, #ccc)',
                    color: 'var(--color-error, #d32f2f)',
                    background: 'transparent',
                  }}
                >
                  <span className="material-symbols-outlined text-[16px]">delete</span>
                  Delete
                </button>
                {lightbox.group.items.length > 1 && (
                  <span className="font-label-sm text-secondary bg-surface-variant px-2 py-0.5 rounded">
                    Perspective {lightbox.currentIndex + 1} of {lightbox.group.items.length}
                  </span>
                )}
              </div>
            </div>
            <p style={{ fontSize: '11px', opacity: 0.45, margin: 0 }}>
              Click outside or press Esc to close
            </p>
          </div>

          {lightbox.group.items.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex < prev.group.items.length - 1 ? prev.currentIndex + 1 : 0 })); }}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-4 text-white hover:bg-white/20 rounded-full transition-colors z-50 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[48px]">chevron_right</span>
            </button>
          )}
        </div>
      )}

      <style>{`
        @keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
        @keyframes scaleIn { from { transform: scale(0.92); opacity: 0 } to { transform: scale(1); opacity: 1 } }
      `}</style>

      <main className="flex-1 px-gutter py-margin max-w-[1440px] mx-auto w-full">
        {/* Page Header */}
        <div className="mb-margin flex flex-col md:flex-row md:items-end justify-between gap-md">
          <div>
            <h1 className="font-headline-md text-headline-md text-on-surface mb-xs">Analysis Results</h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Classification results from the eye lens condition model.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-sm">
            <button
              onClick={handleClassify}
              disabled={classifying}
              className="flex items-center gap-xs px-md py-sm bg-primary text-on-primary rounded-lg font-label-sm text-label-sm hover:opacity-90 transition-opacity shadow-sm cursor-pointer disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-[16px]">
                {classifying ? 'hourglass_empty' : 'play_arrow'}
              </span>
              {classifying ? 'Classifying…' : 'Run Classification'}
            </button>
            <button
              onClick={fetchResults}
              className="flex items-center gap-xs px-md py-sm bg-surface-container-lowest border border-outline-variant rounded-lg font-label-sm text-label-sm text-on-surface hover:bg-surface-container-low transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Refresh
            </button>
          </div>
        </div>
        
        {classifyProgress && (
          <div className="mb-margin bg-surface-container-low p-md rounded-xl border border-surface-variant shadow-sm animate-scaleIn origin-top">
            <div className="flex justify-between items-center mb-sm">
              <span className="font-label-md text-label-md text-on-surface">Classifying images...</span>
              <span className="font-label-sm text-label-sm text-primary">
                {classifyProgress.current} / {classifyProgress.total}
              </span>
            </div>
            <div className="w-full h-2 bg-surface-variant rounded-full overflow-hidden mb-xs">
              <div 
                className="h-full bg-primary transition-all duration-300 ease-out rounded-full" 
                style={{ width: `${Math.max(5, (classifyProgress.current / Math.max(1, classifyProgress.total)) * 100)}%` }} 
              />
            </div>
            <div className="font-body-xs text-body-xs text-secondary truncate">
              {classifyProgress.text}
            </div>
          </div>
        )}

        {/* Table Card */}
        <div className="bg-surface-container-lowest border border-surface-variant rounded-xl shadow-sm" style={{ overflow: 'clip' }}>
          {/* Scrollable container — sticky thead works because overflow-clip doesn't break it */}
          <div
            ref={tableContainerRef}
            onScroll={handleTableScroll}
            className="overflow-x-auto overflow-y-auto"
            style={{ maxHeight: '65vh', position: 'relative' }}
          >
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container sticky top-0 z-20 border-b border-outline-variant shadow-sm">
                <tr>
                  <th className={`px-md font-label-md text-label-md text-on-surface-variant w-24 ${settings.compactView ? 'py-xs' : 'py-sm'}`}>Picture</th>
                  <th
                    className={`px-md font-label-md text-label-md text-on-surface-variant cursor-pointer select-none hover:text-on-surface transition-colors ${settings.compactView ? 'py-xs' : 'py-sm'}`}
                    onClick={() => handleSort('name')}
                  >
                    <span className="inline-flex items-center">Name <SortIcon colKey="name" /></span>
                  </th>
                  <th
                    className={`px-md font-label-md text-label-md text-on-surface-variant cursor-pointer select-none hover:text-on-surface transition-colors ${settings.compactView ? 'py-xs' : 'py-sm'}`}
                    onClick={() => handleSort('state')}
                  >
                    <span className="inline-flex items-center">State <SortIcon colKey="state" /></span>
                  </th>
                  {settings.showConfidence && (
                    <th
                      className={`px-md font-label-md text-label-md text-on-surface-variant cursor-pointer select-none hover:text-on-surface transition-colors ${settings.compactView ? 'py-xs' : 'py-sm'}`}
                      onClick={() => handleSort('confidence')}
                    >
                      <span className="inline-flex items-center">Confidence <SortIcon colKey="confidence" /></span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="font-body-sm text-body-sm">
                {loading && (
                  <tr>
                    <td colSpan={4} className="py-xl text-center text-secondary">
                      <span className="material-symbols-outlined text-[32px] mb-2 block animate-spin">progress_activity</span>
                      Loading results…
                    </td>
                  </tr>
                )}
                {!loading && error && (
                  <tr>
                    <td colSpan={4} className="py-xl text-center text-error">
                      <span className="material-symbols-outlined text-[32px] mb-2 block">cloud_off</span>
                      {error}
                    </td>
                  </tr>
                )}
                {!loading && !error && groupedResults.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-xl text-center text-secondary">
                      <span className="material-symbols-outlined text-[32px] mb-2 block">image_search</span>
                      No results yet. Upload images and click <strong>Run Classification</strong>.
                    </td>
                  </tr>
                )}
                {!loading && groupedResults.map((group, i) => (
                  <tr
                    key={group.groupId}
                    className={`border-b border-surface-variant hover:bg-surface-container-low transition-colors ${i % 2 === 1 ? 'bg-surface-container-low/30' : ''}`}
                  >
                    {/* Thumbnail — clickable */}
                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div
                        onClick={() => group.items[0].thumbnail && setLightbox({
                          group: group,
                          currentIndex: 0
                        })}
                        className={`${settings.compactView ? 'w-10 h-10' : 'w-16 h-16'} rounded-lg overflow-hidden border border-outline-variant bg-surface-container-low flex items-center justify-center relative`}
                        style={{ cursor: group.items[0].thumbnail ? 'zoom-in' : 'default', transition: 'transform 0.15s', }}
                        onMouseEnter={e => { if (group.items[0].thumbnail) e.currentTarget.style.transform = 'scale(1.07)'; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
                        title={group.items[0].thumbnail ? 'Click to enlarge' : ''}
                      >
                        {group.items[0].thumbnail ? (
                          <>
                            <img
                              className="w-full h-full object-cover"
                              src={`${BACKEND_URL}/thumbnail/${group.items[0].filename}`}
                              alt={group.items[0].filename}
                            />
                            {group.items[0].heatmap && (
                              <div className="absolute top-0 left-0 bg-error text-on-error-container text-[10px] font-bold px-1 rounded-br-md flex items-center gap-0.5">
                                <span className="material-symbols-outlined text-[12px]">local_fire_department</span>
                                damage
                              </div>
                            )}
                            {group.items.length > 1 && (
                              <div className="absolute bottom-0 right-0 bg-black/60 text-white text-[10px] px-1 font-bold rounded-tl-md">
                                {group.items.length}
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="material-symbols-outlined text-secondary">image</span>
                        )}
                      </div>
                    </td>

                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div className="font-label-md text-label-md text-on-surface truncate max-w-[160px]">
                        {group.items.length > 1 ? `Multi-Perspective Lens` : group.items[0].filename}
                      </div>
                      {group.items.length > 1 && (
                        <div className="text-[11px] text-secondary">{group.items.length} images grouped</div>
                      )}
                    </td>
                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>{stateBadge(group.prediction)}</td>
                    {settings.showConfidence && (
                      <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div className="flex items-center gap-xs">
                        <div className="w-16 h-2 bg-surface-variant rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${group.prediction === 'Good' ? 'bg-primary' : 'bg-error'}`}
                            style={{ width: `${Math.round(group.confidence * 100)}%` }}
                          />
                        </div>
                        <span className={`font-medium text-xs ${group.prediction === 'Good' ? 'text-primary' : 'text-error'}`}>
                          {Math.round(group.confidence * 100)}%
                        </span>
                      </div>
                    </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {groupedResults.length > 0 && (
            <div className="p-sm border-t border-surface-variant bg-surface-container-lowest flex justify-between items-center text-body-sm text-on-surface-variant">
              <span>Showing {groupedResults.length} result{groupedResults.length !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
        {/* Scroll-to-top FAB */}
        {showScrollTop && (
          <button
            onClick={scrollToTop}
            title="Back to top"
            className="fixed bottom-6 right-6 z-40 w-11 h-11 rounded-full bg-primary text-on-primary shadow-lg flex items-center justify-center hover:opacity-90 active:scale-95 transition-all cursor-pointer"
            style={{ boxShadow: '0 4px 20px rgba(0,0,0,0.25)' }}
          >
            <span className="material-symbols-outlined text-[20px]">arrow_upward</span>
          </button>
        )}
      </main>
    </>
  );
};

export default AnalysisResults;
