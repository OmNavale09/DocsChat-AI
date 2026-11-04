
import React, { useEffect, useRef, useState } from 'react';
import { renderAsync } from 'docx-preview';

export default function DocxViewer({ file }) {
  const containerRef = useRef(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!file || !containerRef.current) return;

    let cancelled = false;
    const container = containerRef.current;

    async function renderDocument() {
      container.innerHTML = '';
      setError('');
      setLoading(true);

      try {
        const buffer = await file.arrayBuffer();

        if (cancelled) return;

        await renderAsync(buffer, container, null, {
          className: 'docx',
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          useBase64URL: true,
        });
      } catch (err) {
        console.error('DOCX rendering error:', err);

        if (!cancelled) {
          setError(
            'Could not display this Word document. Please check that it is a valid .docx file.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    renderDocument();

    return () => {
      cancelled = true;
      container.innerHTML = '';
    };
  }, [file]);

  if (!file) {
    return <p>Select a document to view it.</p>;
  }

  return (
    <div className="docx-viewer">
      {loading && <p className="docx-loading">Rendering document...</p>}

      {error && <p className="document-error">{error}</p>}

      <div ref={containerRef} />
    </div>
  );
}
