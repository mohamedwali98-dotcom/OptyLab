import React, { useState, useEffect, useRef, useCallback } from 'react';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AnalysisAdmin = () => {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [training, setTraining] = useState(false);
  
  const [results, setResults] = useState([]);
  const [resultsLoading, setResultsLoading] = useState(true);
  const [uploadStats, setUploadStats] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [correctingFile, setCorrectingFile] = useState(null);
  const [lightbox, setLightbox] = useState(null);
  const [sortKey, setSortKey]   = useState(null);
  const [sortDir, setSortDir]   = useState('asc');
  const [showScrollTop, setShowScrollTop] = useState(false);
  const tableContainerRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setLightbox(null);
      if (lightbox && lightbox.group.items.length > 1) {
        if (e.key === 'ArrowLeft') {
          setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex > 0 ? prev.currentIndex - 1 : prev.group.items.length - 1 }));
        }
        if (e.key === 'ArrowRight') {
          setLightbox(prev => ({ ...prev, currentIndex: prev.currentIndex < prev.group.items.length - 1 ? prev.currentIndex + 1 : 0 }));
        }
      }
    };
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
  }, [lightbox]);

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
      g.timestamp  = g.items[0].timestamp;
    });

    // ── Sorting ─────────────────────────────────────────────────────
    if (sortKey) {
      groups.sort((a, b) => {
        let va, vb;
        if (sortKey === 'name') {
          va = (a.items.length > 1 ? 'Multi-Perspective Lens' : a.items[0].filename).toLowerCase();
          vb = (b.items.length > 1 ? 'Multi-Perspective Lens' : b.items[0].filename).toLowerCase();
        } else if (sortKey === 'timestamp') {
          va = a.timestamp; vb = b.timestamp;
        } else if (sortKey === 'final') {
          va = a.prediction; vb = b.prediction;
        } else if (sortKey === 'confidence') {
          va = a.confidence; vb = b.confidence;
        }
        if (va < vb) return sortDir === 'asc' ? -1 : 1;
        if (va > vb) return sortDir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return groups;
  }, [results, sortKey, sortDir]);

  // ── Scroll helpers ───────────────────────────────────────────
  const handleTableScroll = useCallback(() => {
    if (tableContainerRef.current) {
      setShowScrollTop(tableContainerRef.current.scrollTop > 120);
    }
  }, []);
  const scrollToTop = () => tableContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });

  // ── Column sort toggle ────────────────────────────────────────
  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };
  const SortIcon = ({ colKey }) => {
    if (sortKey !== colKey) return <span className="material-symbols-outlined text-[13px] opacity-25 ml-0.5 align-middle">unfold_more</span>;
    return <span className="material-symbols-outlined text-[13px] text-primary ml-0.5 align-middle">{sortDir === 'asc' ? 'arrow_upward' : 'arrow_downward'}</span>;
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/model-stats`);
      if (res.ok) setStats(await res.json());
    } catch {
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchResults = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/results`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch (e) {
      console.error('Failed to fetch results:', e);
    } finally {
      setResultsLoading(false);
    }
  };

  const fetchUploadStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/upload-stats`);
      if (res.ok) {
        setUploadStats(await res.json());
      }
    } catch (e) {
      console.error('Failed to fetch upload stats:', e);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchResults();
    fetchUploadStats();
  }, []);

  const handleRetrain = async () => {
    setTraining(true);
    try {
      const res = await fetch(`${BACKEND_URL}/train`, { method: 'POST' });
      if (res.ok) {
        await fetchStats();
        await fetchResults();
        await fetchUploadStats();
        alert('Model retrained successfully!');
      } else {
        const d = await res.json();
        alert(d.detail || 'Training failed.');
      }
    } catch {
      alert('Cannot connect to backend.');
    } finally {
      setTraining(false);
    }
  };

  const handleCorrect = async (filename, correctedLabel) => {
    setCorrectingFile(filename);
    try {
      const res = await fetch(`${BACKEND_URL}/correct-prediction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, corrected_label: correctedLabel }),
      });
      if (res.ok) {
        await fetchResults();
        await fetchUploadStats();
        alert(`Corrected ${filename} classification to ${correctedLabel} and added to DB.`);
      } else {
        const d = await res.json();
        alert(d.detail || 'Correction failed.');
      }
    } catch {
      alert('Cannot connect to backend.');
    } finally {
      setCorrectingFile(null);
    }
  };

  const MetricCard = ({ label, value, icon, color }) => (
    <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant flex flex-col justify-between">
      <div className="flex justify-between items-start mb-md">
        <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">{label}</span>
        <span className={`material-symbols-outlined ${color}`}>{icon}</span>
      </div>
      <div>
        <div className={`font-headline-lg text-headline-lg ${color}`}>{value}</div>
      </div>
    </div>
  );

  const stateBadge = (prediction, corrected) => {
    if (prediction === 'Good') {
      return (
        <span className="inline-flex items-center gap-xs px-sm py-xs rounded-full font-label-sm text-label-sm bg-primary-container/30 text-primary">
          <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
          Good {corrected && <span className="text-[10px] opacity-70 ml-1 font-semibold">(Corrected)</span>}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-xs px-sm py-xs rounded-full font-label-sm text-label-sm bg-error-container text-on-error-container">
        <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>error</span>
        Damaged {corrected && <span className="text-[10px] opacity-70 ml-1 font-semibold">(Corrected)</span>}
      </span>
    );
  };

  const filteredResults = groupedResults.filter((group) => {
    const query = searchQuery.toLowerCase();
    return group.items.some(row => 
      (row.id && row.id.toLowerCase().includes(query)) ||
      (row.filename && row.filename.toLowerCase().includes(query))
    );
  });

  return (
    <>
      {/* ── Lightbox overlay ─────────────────────────────────────────────── */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 50,
            background: 'rgba(0,0,0,0.55)',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
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
              src={`${BACKEND_URL}/thumbnail/${lightbox.group.items[lightbox.currentIndex].filename}`}
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
                {stateBadge(lightbox.group.items[lightbox.currentIndex].prediction, lightbox.group.items[lightbox.currentIndex].corrected)}
              </div>
              {lightbox.group.items.length > 1 && (
                <span className="font-label-sm text-secondary bg-surface-variant px-2 py-0.5 rounded">
                  Perspective {lightbox.currentIndex + 1} of {lightbox.group.items.length}
                </span>
              )}
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

      <main className="flex-grow p-gutter md:p-margin max-w-7xl mx-auto w-full flex flex-col gap-margin">
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-md">
          <div>
            <h1 className="font-display-lg text-display-lg text-on-background mb-xs">Analysis Admin</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant">Review model performance and override predictions.</p>
          </div>
          <div className="flex gap-sm">
            <button
              onClick={handleRetrain}
              disabled={training}
              className="px-md py-sm rounded bg-primary text-on-primary font-label-md hover:opacity-90 transition-opacity flex items-center gap-xs cursor-pointer disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-[18px]">{training ? 'hourglass_empty' : 'model_training'}</span>
              {training ? 'Training…' : 'Retrain Model'}
            </button>
          </div>
        </header>

        {/* Dashboard Overview Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-md">
          <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant flex flex-col justify-between">
            <div className="flex justify-between items-start mb-sm">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Total Uploaded Scans</span>
              <span className="material-symbols-outlined text-primary">cloud_upload</span>
            </div>
            <div>
              <div className="font-headline-lg text-headline-lg text-primary font-semibold">
                {uploadStats ? uploadStats.total_uploaded : 0}
              </div>
              <p className="font-body-sm text-body-sm text-secondary mt-1">
                {uploadStats ? uploadStats.total_classified : 0} classified, {uploadStats ? (uploadStats.total_uploaded - uploadStats.total_classified) : 0} pending
              </p>
            </div>
          </div>

          <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant flex flex-col justify-between">
            <div className="flex justify-between items-start mb-sm">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Model Accuracy (Latest)</span>
              <span className="material-symbols-outlined text-secondary">check_circle</span>
            </div>
            <div>
              <div className="font-headline-lg text-headline-lg text-secondary font-semibold">
                {stats ? `${(stats.mean_accuracy * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <p className="font-body-sm text-body-sm text-secondary mt-1">
                {stats ? 'Previous accuracy metric' : 'Model not trained yet'}
              </p>
            </div>
          </div>

          <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant flex flex-col justify-between">
            <div className="flex justify-between items-start mb-sm">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Training Database</span>
              <span className="material-symbols-outlined text-tertiary">database</span>
            </div>
            <div>
              <div className="font-headline-lg text-headline-lg text-tertiary font-semibold">
                {stats ? (stats.n_good + stats.n_damaged) : 0}
              </div>
              <p className="font-body-sm text-body-sm text-secondary mt-1">
                {stats ? `${stats.n_good} Good, ${stats.n_damaged} Damaged` : 'No images in training DB'}
              </p>
            </div>
          </div>
        </section>

        {/* Model Performance Section */}
        <section>
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
            <span className="material-symbols-outlined text-primary">insights</span>
            Detailed Model Performance Report
          </h2>

          {statsLoading && (
            <div className="text-center py-xl text-secondary">
              <span className="material-symbols-outlined text-[32px] block mb-2 animate-spin">progress_activity</span>
              Loading model stats…
            </div>
          )}

          {!statsLoading && !stats && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-md flex items-start gap-sm text-yellow-800 mb-md">
              <span className="material-symbols-outlined">warning</span>
              <div>
                <div className="font-label-md font-semibold mb-xs">Model not trained yet</div>
                <div className="font-body-sm text-body-sm">
                  Add images to <code>DB/Good</code> and <code>DB/Damaged</code>, then click <strong>Retrain Model</strong> to train the classifier.
                </div>
              </div>
            </div>
          )}

          {stats && (
            <>
              {/* Metric cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-md mb-md">
                <MetricCard label="Mean Accuracy" value={`${(stats.mean_accuracy * 100).toFixed(1)}%`} icon="check_circle" color="text-primary" />
                <MetricCard label="Precision" value={`${(stats.precision * 100).toFixed(1)}%`} icon="ads_click" color="text-secondary" />
                <MetricCard label="Recall" value={`${(stats.recall * 100).toFixed(1)}%`} icon="search" color="text-tertiary" />
                <MetricCard label="F1-Score" value={`${(stats.f1 * 100).toFixed(1)}%`} icon="balance" color="text-on-surface" />
              </div>

              {/* Per-model accuracy bar chart */}
              <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-md mb-md">
                <h3 className="font-label-md text-label-md text-secondary uppercase tracking-wider mb-md">Accuracy per Model</h3>
                <div className="flex items-end gap-md h-32">
                  {(stats.model_accuracies || []).map((acc, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-xs">
                      <span className="font-body-sm text-body-sm text-primary font-semibold">{(acc * 100).toFixed(0)}%</span>
                      <div className="w-full bg-surface-variant rounded-t" style={{ height: `${acc * 100}%` }}>
                        <div className="w-full h-full bg-primary rounded-t opacity-80" />
                      </div>
                      <span className="font-body-sm text-body-sm text-secondary">{['SVM', 'CNN', 'ViT'][i] || `Model ${i+1}`}</span>
                    </div>
                  ))}
                </div>
              </div>

            </>
          )}
        </section>

        {/* Scan Review Table */}
        <section className="bg-surface-container-lowest rounded-lg border border-surface-variant flex flex-col flex-grow" style={{ overflow: 'clip' }}>
          <div className="p-sm md:p-md border-b border-surface-variant bg-surface-container-low flex justify-between items-center">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">Recent Scans</h2>
            <div className="relative w-64">
              <span className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-secondary">search</span>
              <input
                className="w-full pl-xl pr-sm py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-sm focus:border-primary outline-none"
                placeholder="Search scans..."
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <div
            ref={tableContainerRef}
            onScroll={handleTableScroll}
            className="overflow-x-auto overflow-y-auto flex-grow"
            style={{ maxHeight: '55vh' }}
          >
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-low sticky top-0 z-20 border-b border-surface-variant shadow-sm">
                <tr>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Picture</th>
                  <th
                    className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold cursor-pointer select-none hover:text-on-surface transition-colors"
                    onClick={() => handleSort('name')}
                  >
                    <span className="inline-flex items-center">Filename <SortIcon colKey="name" /></span>
                  </th>
                  <th
                    className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold cursor-pointer select-none hover:text-on-surface transition-colors"
                    onClick={() => handleSort('timestamp')}
                  >
                    <span className="inline-flex items-center">Timestamp <SortIcon colKey="timestamp" /></span>
                  </th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">SVM</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">CNN</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">ViT</th>
                  <th
                    className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold cursor-pointer select-none hover:text-on-surface transition-colors"
                    onClick={() => handleSort('final')}
                  >
                    <span className="inline-flex items-center">Final <SortIcon colKey="final" /></span>
                  </th>
                  <th
                    className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold cursor-pointer select-none hover:text-on-surface transition-colors"
                    onClick={() => handleSort('confidence')}
                  >
                    <span className="inline-flex items-center">Conf <SortIcon colKey="confidence" /></span>
                  </th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="font-body-sm text-body-sm divide-y divide-surface-variant">
                {resultsLoading ? (
                  <tr>
                    <td colSpan={9} className="py-xl text-center text-secondary font-body-sm">
                      <span className="material-symbols-outlined text-[32px] mb-2 block animate-spin">progress_activity</span>
                      Loading scans...
                    </td>
                  </tr>
                ) : filteredResults.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-xl text-center text-secondary font-body-sm">
                      {searchQuery ? 'No matching scans found.' : 'Upload images and run classification to see results here.'}
                    </td>
                  </tr>
                ) : (
                  filteredResults.map((group, i) => {
                    const row = group.items[0]; // Representative item for table
                    return (
                    <tr
                      key={group.groupId}
                      className={`hover:bg-surface-container-low transition-colors ${i % 2 === 1 ? 'bg-surface-container-low/30' : ''}`}
                    >
                      <td className="p-sm">
                        {row.thumbnail ? (
                          <div
                            onClick={() => setLightbox({
                              group: group,
                              currentIndex: 0
                            })}
                            className="w-12 h-12 rounded-lg overflow-hidden border border-outline-variant bg-surface-container-low flex items-center justify-center flex-shrink-0 cursor-zoom-in hover:scale-105 transition-transform relative"
                          >
                            <img className="w-full h-full object-cover" src={`${BACKEND_URL}/thumbnail/${row.filename}`} alt={row.filename} />
                            {group.items.length > 1 && (
                              <div className="absolute bottom-0 right-0 bg-black/60 text-white text-[10px] px-1 font-bold rounded-tl-md">
                                {group.items.length}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="w-12 h-12 rounded-lg border border-outline-variant bg-surface-container-low flex items-center justify-center flex-shrink-0">
                            <span className="material-symbols-outlined text-secondary">image</span>
                          </div>
                        )}
                      </td>
                      <td className="p-sm font-medium text-on-surface max-w-[200px] truncate">
                        {group.items.length > 1 ? `Multi-Perspective Lens` : row.filename}
                        {group.items.length > 1 && <div className="text-[11px] text-secondary font-normal">{group.items.length} images</div>}
                      </td>
                      <td className="p-sm text-secondary">{new Date(row.timestamp).toLocaleString()}</td>
                      <td className="p-sm">{stateBadge(row.models?.svm?.prediction || row.prediction, false)}</td>
                      <td className="p-sm">{stateBadge(row.models?.cnn?.prediction || row.prediction, false)}</td>
                      <td className="p-sm">{stateBadge(row.models?.vit?.prediction || row.prediction, false)}</td>
                      <td className="p-sm">{stateBadge(group.prediction, row.corrected)}</td>
                      <td className="p-sm text-secondary font-medium">{group.confidence ? `${Math.round(group.confidence * 100)}%` : 'N/A'}</td>
                      <td className="p-sm">
                        <button
                          disabled={correctingFile === row.filename}
                          onClick={() => handleCorrect(row.filename, group.prediction === 'Good' ? 'Damaged' : 'Good')}
                          className="flex items-center gap-xs px-sm py-xs border border-primary text-primary hover:bg-primary-container/10 rounded font-label-sm text-[12px] cursor-pointer transition-colors disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-[14px]">edit</span>
                          {correctingFile === row.filename ? 'Updating...' : group.prediction === 'Good' ? 'Mark Damaged' : 'Mark Good'}
                        </button>
                      </td>
                    </tr>
                  )})
                )}
              </tbody>
            </table>
          </div>
        </section>

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

export default AnalysisAdmin;
