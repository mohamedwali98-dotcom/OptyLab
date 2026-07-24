import React, { useState, useEffect } from 'react';

const BACKEND_URL = 'http://localhost:8000';

const AnalysisAdmin = () => {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [training, setTraining] = useState(false);

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

  useEffect(() => { fetchStats(); }, []);

  const handleRetrain = async () => {
    setTraining(true);
    try {
      const res = await fetch(`${BACKEND_URL}/train`, { method: 'POST' });
      if (res.ok) {
        await fetchStats();
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

  return (
    <>
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

        {/* Model Performance Section */}
        <section>
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
            <span className="material-symbols-outlined text-primary">insights</span>
            Model Performance (5-Fold Cross-Validation)
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
                <div className="grid grid-cols-3 gap-xs max-w-xs">
                  <div />
                  <div className="text-center font-label-md text-label-md text-secondary py-xs">Pred: Good</div>
                  <div className="text-center font-label-md text-label-md text-secondary py-xs">Pred: Damaged</div>
                  <div className="font-label-md text-label-md text-secondary py-xs">Act: Good</div>
                  <div className="bg-primary/20 text-primary font-headline-sm text-headline-sm text-center py-md rounded">{stats.confusion_matrix[0][0]}</div>
                  <div className="bg-error/10 text-error font-headline-sm text-headline-sm text-center py-md rounded">{stats.confusion_matrix[0][1]}</div>
                  <div className="font-label-md text-label-md text-secondary py-xs">Act: Damaged</div>
                  <div className="bg-error/10 text-error font-headline-sm text-headline-sm text-center py-md rounded">{stats.confusion_matrix[1][0]}</div>
                  <div className="bg-primary/20 text-primary font-headline-sm text-headline-sm text-center py-md rounded">{stats.confusion_matrix[1][1]}</div>
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
              <input className="w-full pl-xl pr-sm py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-sm focus:border-primary outline-none" placeholder="Search..." type="text" />
            </div>
          </div>
          <div className="overflow-x-auto flex-grow">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container-low sticky top-0 z-10 border-b border-surface-variant">
                <tr>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Analysis ID</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Filename</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Timestamp</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Prediction</th>
                  <th className="p-sm font-label-md text-label-md text-on-surface-variant font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody className="font-body-sm text-body-sm divide-y divide-surface-variant">
                <tr>
                  <td colSpan={5} className="py-xl text-center text-secondary font-body-sm">
                    Upload images and run classification to see results here.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
};

export default AnalysisAdmin;
