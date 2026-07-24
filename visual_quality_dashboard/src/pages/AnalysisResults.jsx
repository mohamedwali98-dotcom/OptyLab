import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';

const BACKEND_URL = 'http://localhost:8000';

const AnalysisResults = () => {
  const { addNotification, settings } = useApp();
  const [results, setResults]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [classifying, setClassifying] = useState(false);
  const [error, setError]           = useState(null);
  const [lightbox, setLightbox]     = useState(null); // { src, filename, prediction }

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

  // Auto-refresh polling
  useEffect(() => {
    if (!settings.autoRefresh) return;
    const interval = setInterval(fetchResults, 10000); // 10s
    return () => clearInterval(interval);
  }, [settings.autoRefresh]);

  // Close lightbox on Escape key
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') setLightbox(null);
  }, []);
  useEffect(() => {
    if (lightbox) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
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
    try {
      const res = await fetch(`${BACKEND_URL}/classify`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        await fetchResults();
        const mode = data.mode === 'mock' ? ' (mock mode — no model trained)' : '';
        addNotification('success', `Classification complete: ${data.count} image${data.count !== 1 ? 's' : ''} processed${mode}.`);
      } else {
        const data = await res.json();
        const msg = data.detail || 'Classification failed.';
        alert(msg);
        addNotification('error', `Classification failed: ${msg}`);
      }
    } catch {
      alert('Cannot connect to backend.');
      addNotification('error', 'Classification failed — backend is offline.');
    } finally {
      setClassifying(false);
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
            }}
          >
            <img
              src={lightbox.src}
              alt={lightbox.filename}
              style={{
                maxWidth: '70vw',
                maxHeight: '65vh',
                borderRadius: '10px',
                objectFit: 'contain',
                display: 'block',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '13px', opacity: 0.7, fontWeight: 500 }}>
                {lightbox.filename}
              </span>
              {stateBadge(lightbox.prediction)}
            </div>
            <p style={{ fontSize: '11px', opacity: 0.45, margin: 0 }}>
              Click outside or press Esc to close
            </p>
          </div>
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

        {/* Table Card */}
        <div className="bg-surface-container-lowest border border-surface-variant rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container sticky top-0 z-10 border-b border-outline-variant">
                <tr>
                  <th className={`px-md font-label-md text-label-md text-on-surface-variant w-24 ${settings.compactView ? 'py-xs' : 'py-sm'}`}>Picture</th>
                  <th className={`px-md font-label-md text-label-md text-on-surface-variant ${settings.compactView ? 'py-xs' : 'py-sm'}`}>Name</th>
                  <th className={`px-md font-label-md text-label-md text-on-surface-variant ${settings.compactView ? 'py-xs' : 'py-sm'}`}>State</th>
                  {settings.showConfidence && (
                    <th className={`px-md font-label-md text-label-md text-on-surface-variant ${settings.compactView ? 'py-xs' : 'py-sm'}`}>Confidence</th>
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
                {!loading && !error && results.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-xl text-center text-secondary">
                      <span className="material-symbols-outlined text-[32px] mb-2 block">image_search</span>
                      No results yet. Upload images and click <strong>Run Classification</strong>.
                    </td>
                  </tr>
                )}
                {!loading && results.map((row, i) => (
                  <tr
                    key={row.id || i}
                    className={`border-b border-surface-variant hover:bg-surface-container-low transition-colors ${i % 2 === 1 ? 'bg-surface-container-low/30' : ''}`}
                  >
                    {/* Thumbnail — clickable */}
                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div
                        onClick={() => row.thumbnail && setLightbox({
                          src: `${BACKEND_URL}/thumbnail/${row.filename}`,
                          filename: row.filename,
                          prediction: row.prediction,
                        })}
                        className={`${settings.compactView ? 'w-10 h-10' : 'w-16 h-16'} rounded-lg overflow-hidden border border-outline-variant bg-surface-container-low flex items-center justify-center`}
                        style={{ cursor: row.thumbnail ? 'zoom-in' : 'default', transition: 'transform 0.15s', }}
                        onMouseEnter={e => { if (row.thumbnail) e.currentTarget.style.transform = 'scale(1.07)'; }}
                        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
                        title={row.thumbnail ? 'Click to enlarge' : ''}
                      >
                        {row.thumbnail ? (
                          <img
                            className="w-full h-full object-cover"
                            src={`${BACKEND_URL}/thumbnail/${row.filename}`}
                            alt={row.filename}
                          />
                        ) : (
                          <span className="material-symbols-outlined text-secondary">image</span>
                        )}
                      </div>
                    </td>

                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div className="font-label-md text-label-md text-on-surface truncate max-w-[160px]">{row.filename}</div>
                    </td>
                    <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>{stateBadge(row.prediction)}</td>
                    {settings.showConfidence && (
                      <td className={`px-md ${settings.compactView ? 'py-xs' : 'py-sm'}`}>
                      <div className="flex items-center gap-xs">
                        <div className="w-16 h-2 bg-surface-variant rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${row.prediction === 'Good' ? 'bg-primary' : 'bg-error'}`}
                            style={{ width: `${Math.round(row.confidence * 100)}%` }}
                          />
                        </div>
                        <span className={`font-medium text-xs ${row.prediction === 'Good' ? 'text-primary' : 'text-error'}`}>
                          {Math.round(row.confidence * 100)}%
                        </span>
                      </div>
                    </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {results.length > 0 && (
            <div className="p-sm border-t border-surface-variant bg-surface-container-lowest flex justify-between items-center text-body-sm text-on-surface-variant">
              <span>Showing {results.length} result{results.length !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      </main>
    </>
  );
};

export default AnalysisResults;
