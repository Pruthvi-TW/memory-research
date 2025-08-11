import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, File, AlertCircle, CheckCircle } from 'lucide-react';

interface FileData {
  filename: string;
  content_type: string;
  content: string; // base64 encoded
  size: number;
}

interface FileUploadInterfaceProps {
  acceptedTypes: string[];
  maxFiles: number;
  maxFileSize: number; // in bytes
  onFilesSelected: (files: FileData[]) => void;
  onUpload: () => Promise<void>;
  isUploading: boolean;
  disabled?: boolean;
}

interface FileWithPreview extends File {
  id: string;
  preview?: string;
  error?: string;
}

export const FileUploadInterface: React.FC<FileUploadInterfaceProps> = ({
  acceptedTypes,
  maxFiles,
  maxFileSize,
  onFilesSelected,
  onUpload,
  isUploading,
  disabled = false
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > maxFileSize) {
      return `File size exceeds ${Math.round(maxFileSize / 1024 / 1024)}MB limit`;
    }

    // Check file type
    if (!acceptedTypes.includes(file.type)) {
      return `File type ${file.type} is not supported`;
    }

    return null;
  };

  const processFiles = useCallback(async (fileList: FileList) => {
    const newFiles: FileWithPreview[] = [];
    const errors: string[] = [];

    // Check total file count
    if (files.length + fileList.length > maxFiles) {
      errors.push(`Maximum ${maxFiles} files allowed`);
      setValidationErrors(errors);
      return;
    }

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const fileWithId = Object.assign(file, { id: `${Date.now()}-${i}` });
      
      // Validate file
      const error = validateFile(file);
      if (error) {
        fileWithId.error = error;
        errors.push(`${file.name}: ${error}`);
      }

      newFiles.push(fileWithId);
    }

    setFiles(prev => [...prev, ...newFiles]);
    setValidationErrors(errors);

    // Convert valid files to FileData format
    const validFiles = newFiles.filter(f => !f.error);
    if (validFiles.length > 0) {
      const fileDataPromises = validFiles.map(async (file): Promise<FileData> => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const base64 = (reader.result as string).split(',')[1]; // Remove data:type;base64, prefix
            resolve({
              filename: file.name,
              content_type: file.type,
              content: base64,
              size: file.size
            });
          };
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
      });

      try {
        const fileData = await Promise.all(fileDataPromises);
        onFilesSelected(fileData);
      } catch (error) {
        console.error('Error processing files:', error);
        setValidationErrors(prev => [...prev, 'Error processing files']);
      }
    }
  }, [files.length, maxFiles, maxFileSize, acceptedTypes, onFilesSelected]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled || isUploading) return;

    const { files: droppedFiles } = e.dataTransfer;
    if (droppedFiles && droppedFiles.length > 0) {
      processFiles(droppedFiles);
    }
  }, [disabled, isUploading, processFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { files: selectedFiles } = e.target;
    if (selectedFiles && selectedFiles.length > 0) {
      processFiles(selectedFiles);
    }
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [processFiles]);

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
    // Update file data
    const remainingFiles = files.filter(f => f.id !== fileId && !f.error);
    if (remainingFiles.length === 0) {
      onFilesSelected([]);
    }
  };

  const clearAllFiles = () => {
    setFiles([]);
    setValidationErrors([]);
    onFilesSelected([]);
  };

  const openFileDialog = () => {
    if (!disabled && !isUploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) {
      return '🖼️';
    } else if (file.type.includes('pdf')) {
      return '📄';
    } else if (file.type.includes('word') || file.type.includes('document')) {
      return '📝';
    } else if (file.type.includes('text')) {
      return '📄';
    }
    return '📎';
  };

  const validFiles = files.filter(f => !f.error);
  const hasValidFiles = validFiles.length > 0;

  return (
    <div className="file-upload-interface">
      <div
        className={`upload-area ${dragActive ? 'drag-active' : ''} ${disabled ? 'disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInput}
          style={{ display: 'none' }}
          disabled={disabled || isUploading}
        />

        <div className="upload-content">
          <Upload size={48} className="upload-icon" />
          <div className="upload-text">
            <p className="primary-text">
              {dragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="secondary-text">
              or <span className="browse-link">browse files</span>
            </p>
          </div>
          <div className="upload-info">
            <p>Supported: {acceptedTypes.map(type => {
              const ext = type.split('/')[1];
              return ext.toUpperCase();
            }).join(', ')}</p>
            <p>Max {maxFiles} files, {Math.round(maxFileSize / 1024 / 1024)}MB each</p>
          </div>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <div className="validation-errors">
          {validationErrors.map((error, index) => (
            <div key={index} className="error-message">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className="file-list">
          <div className="file-list-header">
            <h4>Selected Files ({files.length})</h4>
            <button
              className="clear-all-btn"
              onClick={clearAllFiles}
              disabled={disabled || isUploading}
            >
              Clear All
            </button>
          </div>

          <div className="files">
            {files.map((file) => (
              <div key={file.id} className={`file-item ${file.error ? 'error' : 'valid'}`}>
                <div className="file-info">
                  <div className="file-icon">
                    {file.error ? (
                      <AlertCircle size={20} className="error-icon" />
                    ) : (
                      <span>{getFileIcon(file)}</span>
                    )}
                  </div>
                  <div className="file-details">
                    <div className="file-name">{file.name}</div>
                    <div className="file-meta">
                      {formatFileSize(file.size)} • {file.type}
                    </div>
                    {file.error && (
                      <div className="file-error">{file.error}</div>
                    )}
                  </div>
                </div>
                <button
                  className="remove-file-btn"
                  onClick={() => removeFile(file.id)}
                  disabled={disabled || isUploading}
                  aria-label={`Remove ${file.name}`}
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasValidFiles && (
        <div className="upload-actions">
          <button
            className="upload-btn"
            onClick={onUpload}
            disabled={disabled || isUploading || !hasValidFiles}
          >
            {isUploading ? (
              <>
                <div className="spinner" />
                Processing Files...
              </>
            ) : (
              <>
                <Upload size={16} />
                Upload {validFiles.length} File{validFiles.length !== 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};