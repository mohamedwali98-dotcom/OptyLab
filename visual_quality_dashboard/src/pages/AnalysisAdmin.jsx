import React, { useState, useEffect } from 'react';

const BACKEND_URL = 'http://localhost:8000';

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

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setLightbox(null);
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

  const filteredResults = results.filter((row) => {
    const query = searchQuery.toLowerCase();
    return (
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
              {stateBadge(lightbox.prediction, false)}
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
            Detailed Cross-Validation Report
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

              {/* Per-fold accuracy bar chart */}
              <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-md mb-md">
                <h3 className="font-label-md text-label-md text-secondary uppercase tracking-wider mb-md">Accuracy per Fold</h3>
                <div className="flex items-end gap-md h-32">
                  {stats.fold_accuracies.map((acc, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-xs">
                      <span className="font-body-sm text-body-sm text-primary font-semibold">{(acc * 100).toFixed(0)}%</span>
                      <div className="w-full bg-surface-variant rounded-t" style={{ height: `${acc * 100}%` }}>
                        <div className="w-full h-full bg-primary rounded-t opacity-80" />
                      </div>
                      <span className="font-body-sm text-body-sm text-secondary">Fold {i + 1}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Confusion Matrix */}
              <div className="bg-surface-container-lowest border border-surface-variant rounded-lg p-md">
                <h3 className="font-label-md text-label-md text-secondary uppercase tracking-wider mb-md">Confusion Matrix</h3>
                <div className="max-w-md overflow-hidden border border-outline-variant rounded-lg">
                  <table className="w-full text-center border-collapse">
                    <thead>
                      <tr className="bg-surface-container border-b border-outline-variant">
                        <th className="p-sm font-label-md text-label-md text-secondary"></th>
                        <th className="p-sm font-label-md text-label-md text-secondary font-semibold">Pred: Good</th>
                        <th className="p-sm font-label-md text-label-md text-secondary font-semibold">Pred: Damaged</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-outline-variant hover:bg-surface-container-low/50">
                        <td className="p-sm font-label-md text-label-md text-secondary font-semibold text-left bg-surface-container/30">
                          Act: Good
                        </td>
                        <td className="p-sm bg-primary/10 text-primary font-bold text-center">
                          <div className="text-lg font-bold">{stats.confusion_matrix[0][0]}</div>
                          <div className="text-[10px] opacity-75 font-normal">True Good</div>
                        </td>
                        <td className="p-sm bg-error/10 text-error font-bold text-center">
                          <div className="text-lg font-bold">{stats.confusion_matrix[0][1]}</div>
                          <div className="text-[10px] opacity-75 font-normal">False Damaged</div>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-low/50">
                        <td className="p-sm font-label-md text-label-md text-secondary font-semibold text-left bg-surface-container/30">
                          Act: Damaged
                        </td>
                        <td className="p-sm bg-error/10 text-error font-bold text-center">
                          <div className="text-lg font-bold">{stats.confusion_matrix[1][0]}</div>
                          <div className="text-[10px] opacity-75 font-normal">False Good</div>
                        </td>
                        <td className="p-sm bg-primary/10 text-primary font-bold text-center">
                          <div className="text-lg font-bold">{stats.confusion_matrix[1][1]}</div>
                          <div className="text-[10px] opacity-75 font-normal">True Damaged</div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="font-body-sm text-body-sm text-secondary mt-sm">Training images: {stats.n_good} Good, {stats.n_damaged} Damaged</p>
              </div>
            </>
          )}
        </section>

        {/* Scan Review Table */}
        <section className="bg-surface-container-lowest rounded-lg border border-surface-variant overflow-hidden flex flex-col flex-grow">
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
          <div className="overflow-x-auto flex-grow">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-low sticky top-0 z-10 border-b border-surface-variant">
                <tr>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Picture</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Filename</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Timestamp</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Prediction</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Confidence</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="font-body-sm text-body-sm divide-y divide-surface-variant">
                {resultsLoading ? (
                  <tr>
                    <td colSpan={6} className="py-xl text-center text-secondary font-body-sm">
                      <span className="material-symbols-outlined text-[32px] mb-2 block animate-spin">progress_activity</span>
                      Loading scans...
                    </td>
                  </tr>
                ) : filteredResults.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-xl text-center text-secondary font-body-sm">
                      {searchQuery ? 'No matching scans found.' : 'Upload images and run classification to see results here.'}
                    </td>
                  </tr>
                ) : (
                  filteredResults.map((row, i) => (
                    <tr
                      key={row.id || i}
                      className={`hover:bg-surface-container-low transition-colors ${i % 2 === 1 ? 'bg-surface-container-low/30' : ''}`}
                    >
                      <td className="p-sm">
                        {row.thumbnail ? (
                          <div
                            onClick={() => setLightbox({
                              src: `${BACKEND_URL}/thumbnail/${row.filename}`,
                              filename: row.filename,
                              prediction: row.prediction,
                            })}
                            className="w-12 h-12 rounded-lg overflow-hidden border border-outline-variant bg-surface-container-low flex items-center justify-center flex-shrink-0 cursor-zoom-in hover:scale-105 transition-transform"
                          >
                            <img className="w-full h-full object-cover" src={`${BACKEND_URL}/thumbnail/${row.filename}`} alt={row.filename} />
                          </div>
                        ) : (
                          <div className="w-12 h-12 rounded-lg border border-outline-variant bg-surface-container-low flex items-center justify-center flex-shrink-0">
                            <span className="material-symbols-outlined text-secondary">image</span>
                          </div>
                        )}
                      </td>
                      <td className="p-sm font-medium text-on-surface max-w-[200px] truncate">{row.filename}</td>
                      <td className="p-sm text-secondary">{new Date(row.timestamp).toLocaleString()}</td>
                      <td className="p-sm">{stateBadge(row.prediction, row.corrected)}</td>
                      <td className="p-sm text-secondary font-medium">{row.confidence ? `${Math.round(row.confidence * 100)}%` : 'N/A'}</td>
                      <td className="p-sm">
                        <button
                          disabled={correctingFile === row.filename}
                          onClick={() => handleCorrect(row.filename, row.prediction === 'Good' ? 'Damaged' : 'Good')}
                          className="flex items-center gap-xs px-sm py-xs border border-primary text-primary hover:bg-primary-container/10 rounded font-label-sm text-[12px] cursor-pointer transition-colors disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-[14px]">edit</span>
                          {correctingFile === row.filename ? 'Updating...' : row.prediction === 'Good' ? 'Mark Damaged' : 'Mark Good'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
};

export default AnalysisAdmin;
