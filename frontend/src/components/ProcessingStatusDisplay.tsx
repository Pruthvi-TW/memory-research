import React, { useState, useEffect } from 'react';
import { 
  Clock, CheckCircle, XCircle, AlertCircle, 
  Loader, Upload, Link, Github, RefreshCw 
} from 'lucide-react';

export interface ProcessingStatus {
  task_id: string;
  status: 'pending' | 'extracting' | 'vectorizing' | 'storing' | 'completed' | 'failed';
  progress: {
    documents_processed: number;
    chunks_created: number;
    vector_embeddings: number;
    memory_items_stored: number;
    processing_time: number;
  };
  result?: {
    documents_processed: number;
    chunks_created: number;
    vector_embeddings: number;
    memory_items_stored: number;
    errors: Array<{
      error_type: string;
      message: string;
      suggested_action: string;
    }>;
    processing_time: number;
    source_type: string;
    source_identifier: string;
  };
  message: string;
}

interface ProcessingStatusDisplayProps {
  taskId: string;
  sourceType: 'upload' | 'url' | 'github';
  sourceIdentifier: string;
  onRetry?: () => void;
  onClose?: () => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const ProcessingStatusDisplay: React.FC<ProcessingStatusDisplayProps> = ({
  taskId,
  sourceType,
  sourceIdentifier,
  onRetry,
  onClose,
  autoRefresh = true,
  refreshInterval = 2000
}) => {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`/api/dynamic-context/status/${taskId}`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        setError(null);
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [taskId]);

  useEffect(() => {
    if (!autoRefresh || !status) return;

    // Stop auto-refresh for terminal states
    if (status.status === 'completed' || status.status === 'failed') {
      return;
    }

    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [status, autoRefresh, refreshInterval]);

  const getSourceIcon = () => {
    switch (sourceType) {
      case 'upload':
        return <Upload size={16} />;
      case 'url':
        return <Link size={16} />;
      case 'github':
        return <Github size={16} />;
      default:
        return <Upload size={16} />;
    }
  };

  const getStatusIcon = () => {
    if (!status) return <Loader size={16} className="animate-spin" />;

    switch (status.status) {
      case 'pending':
        return <Clock size={16} className="text-yellow-500" />;
      case 'extracting':
      case 'vectorizing':
      case 'storing':
        return <Loader size={16} className="animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <AlertCircle size={16} className="text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    if (!status) return 'border-gray-300';

    switch (status.status) {
      case 'pending':
        return 'border-yellow-300 bg-yellow-50';
      case 'extracting':
      case 'vectorizing':
      case 'storing':
        return 'border-blue-300 bg-blue-50';
      case 'completed':
        return 'border-green-300 bg-green-50';
      case 'failed':
        return 'border-red-300 bg-red-50';
      default:
        return 'border-gray-300 bg-gray-50';
    }
  };

  const getProgressPercentage = () => {
    if (!status) return 0;

    switch (status.status) {
      case 'pending':
        return 0;
      case 'extracting':
        return 25;
      case 'vectorizing':
        return 50;
      case 'storing':
        return 75;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      default:
        return 0;
    }
  };

  const formatProcessingTime = (seconds: number): string => {
    if (seconds < 1) return '< 1s';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getSourceDisplayName = (identifier: string): string => {
    if (sourceType === 'upload') {
      return identifier;
    } else if (sourceType === 'url') {
      try {
        const url = new URL(identifier);
        return url.hostname + (url.pathname !== '/' ? url.pathname : '');
      } catch {
        return identifier;
      }
    } else if (sourceType === 'github') {
      return identifier.replace('https://github.com/', '');
    }
    return identifier;
  };

  if (loading && !status) {
    return (
      <div className="processing-status-display loading">
        <div className="status-header">
          <div className="source-info">
            {getSourceIcon()}
            <span className="source-name">Loading status...</span>
          </div>
          <Loader size={16} className="animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="processing-status-display error">
        <div className="status-header">
          <div className="source-info">
            {getSourceIcon()}
            <span className="source-name">Status Error</span>
          </div>
          <XCircle size={16} className="text-red-500" />
        </div>
        <div className="error-content">
          <p className="error-message">{error}</p>
          <button 
            className="retry-btn"
            onClick={fetchStatus}
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!status) return null;

  const progressPercentage = getProgressPercentage();
  const isTerminal = status.status === 'completed' || status.status === 'failed';

  return (
    <div className={`processing-status-display ${getStatusColor()}`}>
      <div className="status-header">
        <div className="source-info">
          {getSourceIcon()}
          <div className="source-details">
            <span className="source-name">{getSourceDisplayName(sourceIdentifier)}</span>
            <span className="source-type">{sourceType}</span>
          </div>
        </div>
        
        <div className="status-info">
          {getStatusIcon()}
          <span className="status-text">{status.status}</span>
          {onClose && (
            <button 
              className="close-btn"
              onClick={onClose}
              aria-label="Close status"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="progress-section">
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <span className="progress-text">{progressPercentage}%</span>
      </div>

      <div className="status-message">
        <p>{status.message}</p>
      </div>

      {status.progress && (
        <div className="progress-details">
          <div className="progress-stats">
            {status.progress.documents_processed > 0 && (
              <div className="stat">
                <span className="stat-label">Documents:</span>
                <span className="stat-value">{status.progress.documents_processed}</span>
              </div>
            )}
            {status.progress.chunks_created > 0 && (
              <div className="stat">
                <span className="stat-label">Chunks:</span>
                <span className="stat-value">{status.progress.chunks_created}</span>
              </div>
            )}
            {status.progress.vector_embeddings > 0 && (
              <div className="stat">
                <span className="stat-label">Embeddings:</span>
                <span className="stat-value">{status.progress.vector_embeddings}</span>
              </div>
            )}
            {status.progress.memory_items_stored > 0 && (
              <div className="stat">
                <span className="stat-label">Memory Items:</span>
                <span className="stat-value">{status.progress.memory_items_stored}</span>
              </div>
            )}
          </div>
          
          {status.progress.processing_time > 0 && (
            <div className="processing-time">
              <Clock size={14} />
              <span>{formatProcessingTime(status.progress.processing_time)}</span>
            </div>
          )}
        </div>
      )}

      {status.status === 'failed' && status.result?.errors && (
        <div className="error-details">
          <h4>Processing Errors:</h4>
          {status.result.errors.map((error, index) => (
            <div key={index} className="error-item">
              <div className="error-message">
                <AlertCircle size={14} />
                <span>{error.message}</span>
              </div>
              {error.suggested_action && (
                <div className="suggested-action">
                  <strong>Suggestion:</strong> {error.suggested_action}
                </div>
              )}
            </div>
          ))}
          
          {onRetry && (
            <button 
              className="retry-btn"
              onClick={onRetry}
            >
              <RefreshCw size={14} />
              Retry Processing
            </button>
          )}
        </div>
      )}

      {status.status === 'completed' && status.result && (
        <div className="completion-summary">
          <div className="summary-stats">
            <div className="summary-stat">
              <span className="stat-number">{status.result.documents_processed}</span>
              <span className="stat-label">Documents Processed</span>
            </div>
            <div className="summary-stat">
              <span className="stat-number">{status.result.chunks_created}</span>
              <span className="stat-label">Chunks Created</span>
            </div>
            <div className="summary-stat">
              <span className="stat-number">{status.result.vector_embeddings}</span>
              <span className="stat-label">Vector Embeddings</span>
            </div>
          </div>
          
          <div className="completion-time">
            <CheckCircle size={14} className="text-green-500" />
            <span>Completed in {formatProcessingTime(status.result.processing_time)}</span>
          </div>
        </div>
      )}

      {!isTerminal && (
        <div className="processing-indicator">
          <div className="pulse-dot" />
          <span>Processing...</span>
        </div>
      )}
    </div>
  );
};