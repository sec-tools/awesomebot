import React, { useState, useEffect } from 'react';
import './FilesPage.css';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  created_at: string;
}

interface FilesPageProps {
  token: string;
}

interface FilePreview {
  filename: string;
  file_type: string;
  content: string;
  chunk_count: number;
}

const FilesPage: React.FC<FilesPageProps> = ({ token }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState<FilePreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await fetch('/api/files/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await fetch('/api/files/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      await loadDocuments();
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handleView = async (id: string) => {
    setLoadingPreview(true);
    try {
      const response = await fetch(`/api/files/${id}/view`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        throw new Error('Failed to load document');
      }
      
      const data = await response.json();
      setPreviewData(data);
      setShowPreview(true);
    } catch (error) {
      console.error('Failed to view document:', error);
      alert('Failed to load document preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Delete this document?')) {
      try {
        const response = await fetch(`/api/files/${id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
          throw new Error('Failed to delete document');
        }
        
        await loadDocuments();
      } catch (error) {
        console.error('Failed to delete document:', error);
        alert('Failed to delete document. Please try again.');
      }
    }
  };

  const closePreview = () => {
    setShowPreview(false);
    setPreviewData(null);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="files-page">
      <div className="files-header">
        <h1>Documents</h1>
        <p>Upload documents to enable RAG (Retrieval-Augmented Generation)</p>
      </div>

      <div className="rag-info-panel">
        <div className="info-panel-header">
          <span className="info-icon">💡</span>
          <h3>How RAG (Document Search) Works</h3>
        </div>
        <div className="info-panel-content">
          <div className="info-step">
            <span className="step-number">1</span>
            <div>
              <strong>Upload Documents</strong>
              <p>Upload PDF, TXT, DOCX, or MD files below. Documents are automatically chunked and indexed.</p>
            </div>
          </div>
          <div className="info-step">
            <span className="step-number">2</span>
            <div>
              <strong>Enable RAG in Chat</strong>
              <p>Toggle "📚 Search Files" in the chat interface to turn RAG ON.</p>
            </div>
          </div>
          <div className="info-step">
            <span className="step-number">3</span>
            <div>
              <strong>Ask Questions</strong>
              <p>The AI will search your documents and answer based on their content, citing sources.</p>
            </div>
          </div>
          <div className="info-example">
            <strong>Example:</strong> "What does my document say about quantum computing?" or "Summarize the key points from my uploaded files."
          </div>
        </div>
      </div>

      <div
        className={`upload-area ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="upload-icon">📁</div>
        <h3>Drag and drop files here</h3>
        <p>or</p>
        <label className="upload-button">
          Choose File
          <input
            type="file"
            accept=".pdf,.txt,.md,.docx,.doc"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
            disabled={uploading}
          />
        </label>
        <p className="upload-hint">Supported: PDF, TXT, MD, DOCX</p>
      </div>

      {uploading && (
        <div className="uploading-indicator">
          <div className="spinner"></div>
          <span>Uploading and indexing...</span>
        </div>
      )}

      <div className="documents-list">
        {documents.map((doc) => (
          <div key={doc.id} className="document-item">
            <div className="document-icon">📄</div>
            <div className="document-info">
              <div className="document-name">{doc.filename}</div>
              <div className="document-meta">
                {formatFileSize(doc.file_size)} • {doc.chunk_count} chunks •{' '}
                {new Date(doc.created_at).toLocaleDateString()}
              </div>
            </div>
            <div className="document-actions">
              <button
                className="view-button"
                onClick={() => handleView(doc.id)}
                disabled={loadingPreview}
              >
                👁️ View
              </button>
              <button
                className="delete-button"
                onClick={() => handleDelete(doc.id)}
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {showPreview && previewData && (
        <div className="modal-overlay" onClick={closePreview}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>📄 {previewData.filename}</h2>
                <p className="modal-meta">
                  {previewData.file_type.toUpperCase()} • {previewData.chunk_count} chunks
                </p>
              </div>
              <button className="modal-close" onClick={closePreview}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <pre className="file-content">{previewData.content}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilesPage;

