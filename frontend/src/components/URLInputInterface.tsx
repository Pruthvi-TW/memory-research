import React, { useState, useEffect } from 'react';
import { Link, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';

interface URLInputInterfaceProps {
  placeholder: string;
  onURLSubmit: (url: string) => Promise<void>;
  isProcessing: boolean;
  disabled?: boolean;
}

interface URLValidationRule {
  test: (url: string) => boolean;
  message: string;
}

const URL_VALIDATION_RULES: URLValidationRule[] = [
  {
    test: (url) => url.length > 0,
    message: 'URL is required'
  },
  {
    test: (url) => /^https?:\/\/.+/.test(url),
    message: 'URL must start with http:// or https://'
  },
  {
    test: (url) => url.length <= 2048,
    message: 'URL is too long (max 2048 characters)'
  },
  {
    test: (url) => {
      try {
        new URL(url);
        return true;
      } catch {
        return false;
      }
    },
    message: 'URL format is invalid'
  }
];

const UNSAFE_DOMAINS = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.', '10.', '172.'];

export const URLInputInterface: React.FC<URLInputInterfaceProps> = ({
  placeholder,
  onURLSubmit,
  isProcessing,
  disabled = false
}) => {
  const [url, setUrl] = useState('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [isValid, setIsValid] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  const validateURL = (inputUrl: string) => {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Run validation rules
    for (const rule of URL_VALIDATION_RULES) {
      if (!rule.test(inputUrl)) {
        errors.push(rule.message);
      }
    }

    // Check for unsafe domains
    if (inputUrl && errors.length === 0) {
      const urlLower = inputUrl.toLowerCase();
      for (const domain of UNSAFE_DOMAINS) {
        if (urlLower.includes(domain)) {
          warnings.push(`URL contains potentially unsafe domain: ${domain}`);
          break;
        }
      }
    }

    // Check for common issues
    if (inputUrl && errors.length === 0) {
      if (inputUrl.includes(' ')) {
        errors.push('URL cannot contain spaces');
      }
      
      if (!inputUrl.includes('.')) {
        errors.push('URL must contain a valid domain');
      }
    }

    setValidationErrors(errors);
    setValidationWarnings(warnings);
    setIsValid(errors.length === 0 && inputUrl.length > 0);
  };

  useEffect(() => {
    if (hasInteracted) {
      validateURL(url);
    }
  }, [url, hasInteracted]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    
    if (!hasInteracted && newUrl.length > 0) {
      setHasInteracted(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!hasInteracted) {
      setHasInteracted(true);
      validateURL(url);
    }

    if (isValid && !isProcessing && !disabled) {
      try {
        await onURLSubmit(url);
      } catch (error) {
        console.error('URL submission error:', error);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit(e as any);
    }
  };

  const clearInput = () => {
    setUrl('');
    setValidationErrors([]);
    setValidationWarnings([]);
    setIsValid(false);
    setHasInteracted(false);
  };

  const getInputStatus = () => {
    if (!hasInteracted) return 'neutral';
    if (validationErrors.length > 0) return 'error';
    if (isValid) return 'valid';
    return 'neutral';
  };

  const getDomainFromURL = (inputUrl: string): string => {
    try {
      const urlObj = new URL(inputUrl);
      return urlObj.hostname;
    } catch {
      return '';
    }
  };

  const getURLPreview = (inputUrl: string): string => {
    if (!inputUrl) return '';
    
    try {
      const urlObj = new URL(inputUrl);
      const domain = urlObj.hostname;
      const path = urlObj.pathname;
      
      if (path === '/') {
        return domain;
      } else if (path.length > 30) {
        return `${domain}${path.substring(0, 27)}...`;
      } else {
        return `${domain}${path}`;
      }
    } catch {
      return inputUrl.length > 50 ? `${inputUrl.substring(0, 47)}...` : inputUrl;
    }
  };

  const inputStatus = getInputStatus();

  return (
    <div className="url-input-interface">
      <form onSubmit={handleSubmit} className="url-form">
        <div className={`url-input-container ${inputStatus}`}>
          <div className="input-icon">
            <Link size={20} />
          </div>
          
          <input
            type="url"
            value={url}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled || isProcessing}
            className="url-input"
            autoComplete="url"
            spellCheck={false}
          />

          {url && (
            <button
              type="button"
              className="clear-input-btn"
              onClick={clearInput}
              disabled={disabled || isProcessing}
              aria-label="Clear URL"
            >
              ×
            </button>
          )}

          <div className="input-status-icon">
            {inputStatus === 'valid' && <CheckCircle size={16} className="valid-icon" />}
            {inputStatus === 'error' && <AlertCircle size={16} className="error-icon" />}
          </div>
        </div>

        {url && isValid && (
          <div className="url-preview">
            <ExternalLink size={14} />
            <span className="preview-text">{getURLPreview(url)}</span>
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
              Processing URL...
            </>
          ) : (
            <>
              <Link size={16} />
              Process URL
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

      <div className="url-help">
        <h4>Supported Content Types:</h4>
        <ul>
          <li>📄 HTML web pages and articles</li>
          <li>📝 Plain text content</li>
          <li>📋 PDF documents (when accessible)</li>
          <li>📊 Documentation and blog posts</li>
        </ul>
        
        <div className="url-tips">
          <p><strong>Tips:</strong></p>
          <ul>
            <li>Use HTTPS URLs when possible for better security</li>
            <li>Ensure the content is publicly accessible</li>
            <li>Large pages may take longer to process</li>
          </ul>
        </div>
      </div>
    </div>
  );
};