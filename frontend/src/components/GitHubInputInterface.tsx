import React, { useState, useEffect } from 'react';
import { Github, AlertCircle, CheckCircle, ExternalLink, Star, GitBranch } from 'lucide-react';

interface GitHubInputInterfaceProps {
  placeholder: string;
  onRepoSubmit: (repoUrl: string) => Promise<void>;
  supportedFormats: string[];
  isProcessing: boolean;
  disabled?: boolean;
}

interface RepoInfo {
  owner: string;
  repo: string;
  fullName: string;
}

export const GitHubInputInterface: React.FC<GitHubInputInterfaceProps> = ({
  placeholder,
  onRepoSubmit,
  supportedFormats,
  isProcessing,
  disabled = false
}) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isValid, setIsValid] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [repoInfo, setRepoInfo] = useState<RepoInfo | null>(null);

  const parseRepoURL = (url: string): RepoInfo | null => {
    try {
      // Handle different GitHub URL formats
      let cleanUrl = url.trim();
      
      // Remove .git suffix if present
      if (cleanUrl.endsWith('.git')) {
        cleanUrl = cleanUrl.slice(0, -4);
      }
      
      // Extract path from different URL formats
      let path = '';
      if (cleanUrl.startsWith('https://github.com/')) {
        path = cleanUrl.replace('https://github.com/', '');
      } else if (cleanUrl.startsWith('github.com/')) {
        path = cleanUrl.replace('github.com/', '');
      } else if (cleanUrl.startsWith('www.github.com/')) {
        path = cleanUrl.replace('www.github.com/', '');
      } else {
        return null;
      }
      
      // Split owner/repo
      const parts = path.split('/');
      if (parts.length < 2) {
        return null;
      }
      
      const owner = parts[0];
      const repo = parts[1];
      
      // Validate owner and repo names
      if (!owner || !repo || owner.length === 0 || repo.length === 0) {
        return null;
      }
      
      // Basic validation for GitHub username/repo name format
      const validNameRegex = /^[a-zA-Z0-9._-]+$/;
      if (!validNameRegex.test(owner) || !validNameRegex.test(repo)) {
        return null;
      }
      
      return {
        owner,
        repo,
        fullName: `${owner}/${repo}`
      };
    } catch {
      return null;
    }
  };

  const validateRepoURL = (inputUrl: string) => {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!inputUrl) {
      errors.push('Repository URL is required');
      setValidationErrors(errors);
      setValidationWarnings(warnings);
      setIsValid(false);
      setRepoInfo(null);
      return;
    }

    if (inputUrl.length > 1024) {
      errors.push('Repository URL is too long');
    }

    // Parse repository info
    const parsedRepo = parseRepoURL(inputUrl);
    if (!parsedRepo) {
      errors.push('Invalid GitHub repository URL format');
      setRepoInfo(null);
    } else {
      setRepoInfo(parsedRepo);
      
      // Check for common issues
      if (parsedRepo.owner.toLowerCase() === 'github') {
        warnings.push('This appears to be a GitHub organization repository');
      }
      
      if (parsedRepo.repo.includes('.')) {
        warnings.push('Repository name contains dots - ensure this is correct');
      }
    }

    // Check if URL starts with proper protocol
    if (!inputUrl.startsWith('https://github.com/') && 
        !inputUrl.startsWith('github.com/') && 
        !inputUrl.startsWith('www.github.com/')) {
      errors.push('URL must be a valid GitHub repository URL');
    }

    setValidationErrors(errors);
    setValidationWarnings(warnings);
    setIsValid(errors.length === 0 && inputUrl.length > 0);
  };

  useEffect(() => {
    if (hasInteracted) {
      validateRepoURL(repoUrl);
    }
  }, [repoUrl, hasInteracted]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setRepoUrl(newUrl);
    
    if (!hasInteracted && newUrl.length > 0) {
      setHasInteracted(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!hasInteracted) {
      setHasInteracted(true);
      validateRepoURL(repoUrl);
    }

    if (isValid && !isProcessing && !disabled) {
      try {
        // Ensure URL has proper format
        let submitUrl = repoUrl.trim();
        if (!submitUrl.startsWith('https://')) {
          if (submitUrl.startsWith('github.com/') || submitUrl.startsWith('www.github.com/')) {
            submitUrl = `https://${submitUrl}`;
          } else {
            submitUrl = `https://github.com/${submitUrl}`;
          }
        }
        
        await onRepoSubmit(submitUrl);
      } catch (error) {
        console.error('Repository submission error:', error);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit(e as any);
    }
  };

  const clearInput = () => {
    setRepoUrl('');
    setValidationErrors([]);
    setValidationWarnings([]);
    setIsValid(false);
    setHasInteracted(false);
    setRepoInfo(null);
  };

  const getInputStatus = () => {
    if (!hasInteracted) return 'neutral';
    if (validationErrors.length > 0) return 'error';
    if (isValid) return 'valid';
    return 'neutral';
  };

  const inputStatus = getInputStatus();

  return (
    <div className="github-input-interface">
      <form onSubmit={handleSubmit} className="github-form">
        <div className={`github-input-container ${inputStatus}`}>
          <div className="input-icon">
            <Github size={20} />
          </div>
          
          <input
            type="url"
            value={repoUrl}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled || isProcessing}
            className="github-input"
            autoComplete="url"
            spellCheck={false}
          />

          {repoUrl && (
            <button
              type="button"
              className="clear-input-btn"
              onClick={clearInput}
              disabled={disabled || isProcessing}
              aria-label="Clear repository URL"
            >
              ×
            </button>
          )}

          <div className="input-status-icon">
            {inputStatus === 'valid' && <CheckCircle size={16} className="valid-icon" />}
            {inputStatus === 'error' && <AlertCircle size={16} className="error-icon" />}
          </div>
        </div>

        {repoInfo && isValid && (
          <div className="repo-preview">
            <div className="repo-info">
              <Github size={16} />
              <span className="repo-name">{repoInfo.fullName}</span>
              <ExternalLink 
                size={14} 
                className="external-link"
                onClick={() => window.open(`https://github.com/${repoInfo.fullName}`, '_blank')}
              />
            </div>
            <div className="repo-details">
              <span className="owner">Owner: {repoInfo.owner}</span>
              <span className="separator">•</span>
              <span className="repo">Repository: {repoInfo.repo}</span>
            </div>
          </div>
        )}

        <button
          type="submit"
          className="submit-btn"
          disabled={!isValid || isProcessing || disabled}
        >
          {isProcessing ? (
            <>
              <div className="spinner" />
              Processing Repository...
            </>
          ) : (
            <>
              <Github size={16} />
              Process Repository
            </>
          )}
        </button>
      </form>

      {hasInteracted && validationErrors.length > 0 && (
        <div className="validation-messages errors">
          {validationErrors.map((error, index) => (
            <div key={index} className="validation-message error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          ))}
        </div>
      )}

      {hasInteracted && validationWarnings.length > 0 && (
        <div className="validation-messages warnings">
          {validationWarnings.map((warning, index) => (
            <div key={index} className="validation-message warning">
              <AlertCircle size={16} />
              <span>{warning}</span>
            </div>
          ))}
        </div>
      )}

      <div className="github-help">
        <h4>Supported File Types:</h4>
        <div className="supported-formats">
          {supportedFormats.map((format, index) => (
            <span key={index} className="format-tag">
              {format}
            </span>
          ))}
        </div>
        
        <div className="github-tips">
          <p><strong>What gets processed:</strong></p>
          <ul>
            <li>📄 README files and documentation</li>
            <li>📁 Files in /docs, /documentation directories</li>
            <li>💻 Source code files with comments</li>
            <li>⚙️ Configuration files (JSON, YAML)</li>
          </ul>
          
          <p><strong>Tips:</strong></p>
          <ul>
            <li>Only public repositories are supported</li>
            <li>Large repositories may take longer to process</li>
            <li>Priority given to documentation files</li>
            <li>Files larger than 1MB are skipped</li>
          </ul>
        </div>

        <div className="example-urls">
          <p><strong>Example URLs:</strong></p>
          <ul>
            <li><code>https://github.com/owner/repository</code></li>
            <li><code>github.com/owner/repository</code></li>
            <li><code>owner/repository</code></li>
          </ul>
        </div>
      </div>
    </div>
  );
};