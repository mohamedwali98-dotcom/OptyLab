import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useApp } from '../context/AppContext';

const BACKEND_URL = 'http://localhost:8000';

const UploadImagery = () => {
  const { addNotification } = useApp();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [queue, setQueue] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    // Load existing queue from backend on mount
    fetch(`${BACKEND_URL}/queue`)
      .then(res => res.json())
      .then(data => {
        if (data && data.queue) {
          const loadedQueue = data.queue.map(f => ({
            id: `${f.filename}-${Date.now()}`,
            name: f.filename,
            size: 0, // Size isn't returned by backend queue endpoint
            status: f.status
          }));
          setQueue(loadedQueue);
        }
      })
      .catch(err => console.error('Failed to load queue:', err));
  }, []);

  const addFilesToQueue = async (files) => {
    const validExts = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'];
    const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/') || validExts.some(ext => f.name.toLowerCase().endsWith(ext)));
    if (imageFiles.length === 0) {
      alert('No valid images found in the selection. Please select PNG, JPG, BMP, or TIFF files only.');
      return;
    }

    // Add to local queue with pending status
    const newEntries = imageFiles.map(f => ({
      id: `${f.name}-${Date.now()}`,
      name: f.name,
      size: f.size,
      status: 'uploading',
      file: f,
    }));
    setQueue(prev => [...prev, ...newEntries]);

    // Upload to backend
    const formData = new FormData();
    imageFiles.forEach(f => formData.append('files', f));

    try {
      const res = await fetch(`${BACKEND_URL}/upload`, { method: 'POST', body: formData });
      const data = res.ok ? await res.json() : null;

      setQueue(prev => prev.map(entry => {
        const wasUploaded = newEntries.find(n => n.id === entry.id);
        if (!wasUploaded) return entry;
        return { ...entry, status: data ? 'queued' : 'error' };
      }));

      if (data) {
        addNotification('success', `${imageFiles.length} image${imageFiles.length > 1 ? 's' : ''} uploaded successfully.`);
      } else {
        addNotification('error', `Upload failed for ${imageFiles.length} image${imageFiles.length > 1 ? 's' : ''}.`);
      }
    } catch {
      setQueue(prev => prev.map(entry => {
        const wasUploaded = newEntries.find(n => n.id === entry.id);
        if (!wasUploaded) return entry;
        return { ...entry, status: 'error', error: 'Backend offline' };
      }));
      addNotification('error', 'Upload failed — backend is offline.');
    }
  };

  const handleFileChange = (e) => addFilesToQueue(e.target.files);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    addFilesToQueue(e.dataTransfer.files);
  }, []);

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);

  const clearQueue = async () => {
    try {
      await fetch(`${BACKEND_URL}/clear-uploads`, { method: 'DELETE' });
      setQueue([]);
      addNotification('info', 'Queue cleared.');
    } catch {
      alert('Cannot connect to backend to clear queue.');
    }
  };

  const removeEntry = async (id, filename) => {
    try {
      const res = await fetch(`${BACKEND_URL}/upload/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (res.ok) {
        setQueue(prev => prev.filter(q => q.id !== id));
      } else {
        addNotification('error', `Failed to remove ${filename}`);
      }
    } catch {
      addNotification('error', 'Cannot connect to backend to remove file.');
    }
  };

  const statusBadge = (status) => {
    const map = {
      uploading: { label: 'Uploading…', cls: 'bg-yellow-100 text-yellow-800' },
      queued:    { label: 'Queued',     cls: 'bg-blue-100 text-blue-800' },
      error:     { label: 'Error',      cls: 'bg-red-100 text-red-800' },
    };
    const s = map[status] || { label: status, cls: 'bg-gray-100 text-gray-800' };
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${s.cls}`}>{s.label}</span>;
  };

  const formatBytes = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <>
      <main className="flex-grow flex flex-col px-gutter py-margin gap-gutter max-w-[1440px] mx-auto w-full">
        {/* Header */}
        <header>
          <h1 className="font-headline-md text-headline-md text-on-surface">Upload Imagery</h1>
          <p className="font-body-md text-body-md text-secondary mt-1">Transfer high-resolution scans for automated diagnostic analysis.</p>
        </header>

        <div className="flex flex-col gap-gutter">
          {/* Drop Zone */}
          <div
            onClick={() => fileInputRef.current.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition-all min-h-72 relative group overflow-hidden
              ${isDragging
                ? 'border-primary bg-primary/5 scale-[1.01]'
                : 'border-dashed border-outline-variant bg-surface hover:bg-surface-container-low'}`}
          >
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-transform group-hover:scale-110
              ${isDragging ? 'bg-primary/20' : 'bg-primary-container/20'}`}>
              <span className="material-symbols-outlined text-[36px] text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
                {isDragging ? 'download' : 'cloud_upload'}
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">
              {isDragging ? 'Drop images here' : 'Drag & drop images here'}
            </h3>
            <p className="font-body-sm text-body-sm text-secondary mb-4">Supports PNG, JPG, BMP, and TIFF images</p>
            <button className="bg-primary text-on-primary font-label-md px-md py-sm rounded hover:opacity-90 transition-opacity cursor-pointer active:opacity-80">
              Browse Files
            </button>
          </div>

          {/* Folder Upload */}
          <div className="border border-outline-variant rounded-lg bg-surface-container-lowest p-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-md">
              <div className="w-12 h-12 rounded-lg bg-surface-container flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-secondary">folder_zip</span>
              </div>
              <div>
                <h4 className="font-headline-sm text-headline-sm text-on-surface">Batch Upload</h4>
                <p className="font-body-sm text-body-sm text-secondary">Upload a folder of PNG scans</p>
              </div>
            </div>
            <button
              onClick={() => folderInputRef.current.click()}
              className="border border-primary text-primary font-label-md px-md py-sm rounded hover:bg-surface-container-low transition-colors cursor-pointer active:opacity-80 flex items-center gap-xs whitespace-nowrap"
            >
              <span className="material-symbols-outlined text-[18px]">upload</span>
              Select Folder
            </button>
          </div>

          {/* Hidden inputs */}
          <input ref={fileInputRef} type="file" accept="image/png, image/jpeg, image/bmp, image/tiff" multiple onChange={handleFileChange} style={{ display: 'none' }} />
          <input ref={folderInputRef} type="file" accept="image/png, image/jpeg, image/bmp, image/tiff" webkitdirectory="true" directory="true" multiple onChange={handleFileChange} style={{ display: 'none' }} />

          {/* Queue */}
          <div>
            <div className="flex justify-between items-center mb-sm">
              <h4 className="font-label-md text-label-md text-secondary uppercase tracking-wider">
                Transfer Queue {queue.length > 0 && `(${queue.length} file${queue.length > 1 ? 's' : ''})`}
              </h4>
              {queue.length > 0 && (
                <button onClick={clearQueue} className="text-secondary hover:text-error font-body-sm text-body-sm transition-colors cursor-pointer flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">delete</span>
                  Clear
                </button>
              )}
            </div>

            {queue.length === 0 ? (
              <div className="border border-outline-variant rounded-lg p-xl text-center bg-surface-container-lowest">
                <span className="material-symbols-outlined text-[32px] text-secondary mb-2 block">inbox</span>
                <p className="font-body-sm text-body-sm text-secondary">No active transfers. Ready for upload.</p>
              </div>
            ) : (
              <div className="border border-outline-variant rounded-lg bg-surface-container-lowest overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-surface-container border-b border-surface-variant">
                    <tr>
                      <th className="py-sm px-md font-label-md text-label-md text-secondary">Filename</th>
                      <th className="py-sm px-md font-label-md text-label-md text-secondary">Size</th>
                      <th className="py-sm px-md font-label-md text-label-md text-secondary">Status</th>
                      <th className="py-sm px-md font-label-md text-label-md text-secondary text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue.map((entry) => (
                      <tr key={entry.id} className="border-b border-surface-variant last:border-0 hover:bg-surface-container-low transition-colors">
                        <td className="py-sm px-md font-body-sm text-body-sm text-on-surface flex items-center gap-sm">
                          <span className="material-symbols-outlined text-[18px] text-primary">image</span>
                          <span className="truncate max-w-xs">{entry.name}</span>
                        </td>
                        <td className="py-sm px-md font-body-sm text-body-sm text-secondary">{formatBytes(entry.size)}</td>
                        <td className="py-sm px-md">{statusBadge(entry.status)}</td>
                        <td className="py-sm px-md text-right">
                          <button
                            onClick={() => removeEntry(entry.id, entry.name)}
                            className="text-secondary hover:text-error transition-colors p-1 rounded hover:bg-surface-variant cursor-pointer inline-flex items-center justify-center"
                            title="Remove file"
                          >
                            <span className="material-symbols-outlined text-[18px]">close</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
};

export default UploadImagery;
