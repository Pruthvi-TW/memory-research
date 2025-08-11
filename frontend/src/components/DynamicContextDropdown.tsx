import React, { useState } from 'react';
import { Upload, Link, Github, ChevronDown } from 'lucide-react';

export interface ContextSource {
  type: 'upload' | 'url' | 'github';
  label: string;
  icon: React.ReactNode;
  description: string;
}

interface DynamicContextDropdownProps {
  onSourceSelect: (source: ContextSource) => void;
  isProcessing: boolean;
  disabled?: boolean;
}

const CONTEXT_SOURCES: ContextSource[] = [
  {
    type: 'upload',
    label: 'Upload Files',
    icon: <Upload size={16} />,
    description: 'Upload PDF, DOCX, TXT, or MD files'
  },
  {
    type: 'url',
    label: 'Enter URL',
    icon: <Link size={16} />,
    description: 'Extract content from web pages'
  },
  {
    type: 'github',
    label: 'GitHub Repository',
    icon: <Github size={16} />,
    description: 'Process documentation from GitHub repos'
  }
];

export const DynamicContextDropdown: React.FC<DynamicContextDropdownProps> = ({
  onSourceSelect,
  isProcessing,
  disabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<ContextSource | null>(null);

  const handleSourceSelect = (source: ContextSource) => {
    setSelectedSource(source);
    setIsOpen(false);
    onSourceSelect(source);
  };

  const toggleDropdown = () => {
    if (!disabled && !isProcessing) {
      setIsOpen(!isOpen);
    }
  };

  return (
    <div className="dynamic-context-dropdown">
      <button
        className={`dropdown-trigger ${isOpen ? 'open' : ''} ${disabled || isProcessing ? 'disabled' : ''}`}
        onClick={toggleDropdown}
        disabled={disabled || isProcessing}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <div className="dropdown-content">
          {selectedSource ? (
            <div className="selected-source">
              {selectedSource.icon}
              <span>{selectedSource.label}</span>
            </div>
          ) : (
            <div className="placeholder">
              <Upload size={16} />
              <span>Add Dynamic Context</span>
            </div>
          )}
        </div>
        <ChevronDown 
          size={16} 
          className={`dropdown-arrow ${isOpen ? 'rotated' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="dropdown-menu" role="listbox">
          {CONTEXT_SOURCES.map((source) => (
            <button
              key={source.type}
              className="dropdown-item"
              onClick={() => handleSourceSelect(source)}
              role="option"
              aria-selected={selectedSource?.type === source.type}
            >
              <div className="item-icon">
                {source.icon}
              </div>
              <div className="item-content">
                <div className="item-label">{source.label}</div>
                <div className="item-description">{source.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {isOpen && (
        <div 
          className="dropdown-overlay" 
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};