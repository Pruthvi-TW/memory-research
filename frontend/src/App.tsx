import React, { useState, useEffect, useRef } from 'react';
import { Send, Database, Activity, AlertCircle, Plus, FileText, X, Upload, Link, Github } from 'lucide-react';
import './index.css';

// Import dynamic context components
import { DynamicContextDropdown, ContextSource } from './components/DynamicContextDropdown';
import { FileUploadInterface } from './components/FileUploadInterface';
import { URLInputInterface } from './components/URLInputInterface';
import { GitHubInputInterface } from './components/GitHubInputInterface';
import { ProcessingStatusDisplay, ProcessingStatus } from './components/ProcessingStatusDisplay';

interface Message {
  id: string;
  type: 'user' | 'bot' | 'loading';
  content: string;
  contextItems?: string[];
  processingInfo?: {
    memory_matches?: number;
    vector_matches?: number;
    graph_matches?: number;
    conversation_matches?: number;
    hybrid_matches?: number;
    total_context_items: number;
    enhanced_fusion?: boolean;
  };
}

interface SystemStatus {
  status: string;
  services: {
    neo4j: { connected: boolean; status: string };
    vector_store: { collection_count: number; status: string };
    anthropic: { configured: boolean; status: string };
  };
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Dynamic context state
  const [showDynamicContext, setShowDynamicContext] = useState(false);
  const [selectedSource, setSelectedSource] = useState<ContextSource | null>(null);
  const [processingTasks, setProcessingTasks] = useState<Map<string, ProcessingStatus>>(new Map());
  const [isProcessingContent, setIsProcessingContent] = useState(false);
  
  // Content tracking state
  const [uploadedContent, setUploadedContent] = useState<Array<{
    id: string;
    type: 'upload' | 'url' | 'github';
    name: string;
    status: 'processing' | 'completed' | 'failed';
    timestamp: string;
    details?: any;
  }>>([]);
  const [showContentSidebar, setShowContentSidebar] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkSystemHealth();
  }, []);

  const checkSystemHealth = async () => {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const initializeContext = async () => {
    setIsInitializing(true);
    try {
      const response = await fetch('/api/initialize-context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lending_path: './Lending' }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Context initialized:', data);
        await checkSystemHealth(); // Refresh status
        
        // Add a system message with enhanced statistics
        const memoryStats = data.stats.memory_layer || {};
        const vectorStats = data.stats.existing_layers?.vector_store || {};
        const graphStats = data.stats.existing_layers?.graph_database || {};
        
        const systemMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `✅ Context initialized successfully!\n\n**Enhanced Statistics:**\n- **Memory Layer**: ${memoryStats.total_stored || 0} items stored (${memoryStats.capability_prompts || 0} capability prompts, ${memoryStats.common_prompts || 0} common prompts)\n- **Vector Store**: ${vectorStats.documents_processed || vectorStats.chunks_created || 0} documents processed, ${vectorStats.vector_store_count || 0} embeddings\n- **Graph Database**: ${graphStats.documents || 0} documents, ${graphStats.concepts || 0} concepts, ${graphStats.business_flows || 0} business flows\n- **Total Capabilities**: ${data.stats.total_capabilities || 0}\n\n**System Status**: Enhanced multi-layer integration active\n\nYou can now ask questions about lending processes!`,
        };
        setMessages(prev => [...prev, systemMessage]);
      } else {
        throw new Error('Failed to initialize context');
      }
    } catch (error) {
      console.error('Context initialization failed:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'bot',
        content: '❌ Failed to initialize context. Please check the console for details.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsInitializing(false);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
    };

    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'loading',
      content: 'Searching context and generating response...',
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputValue,
          session_id: 'web_session_' + Date.now(),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const botMessage: Message = {
          id: (Date.now() + 2).toString(),
          type: 'bot',
          content: data.response,
          contextItems: data.context_items,
          processingInfo: data.processing_info,
        };

        setMessages(prev => prev.slice(0, -1).concat(botMessage));
      } else {
        throw new Error('Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        type: 'bot',
        content: '❌ Sorry, I encountered an error while processing your request. Please try again.',
      };
      setMessages(prev => prev.slice(0, -1).concat(errorMessage));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSampleQuestion = (question: string) => {
    setInputValue(question);
  };

  // Dynamic context handlers
  const handleSourceSelect = (source: ContextSource) => {
    setSelectedSource(source);
    setShowDynamicContext(true);
  };

  // State for selected files
  const [selectedFiles, setSelectedFiles] = useState<any[]>([]);

  const handleFilesSelected = (files: any[]) => {
    setSelectedFiles(files);
  };

  const handleFileUpload = async () => {
    if (selectedFiles.length === 0) return;
    
    setIsProcessingContent(true);
    
    // Add to uploaded content tracking
    const contentId = Date.now().toString();
    const newContent = {
      id: contentId,
      type: 'upload' as const,
      name: `${selectedFiles.length} files: ${selectedFiles.map(f => f.filename).join(', ')}`,
      status: 'processing' as const,
      timestamp: new Date().toLocaleString(),
      details: {
        files: selectedFiles.map(f => ({
          name: f.filename,
          type: f.content_type,
          size: f.size
        }))
      }
    };
    setUploadedContent(prev => [...prev, newContent]);
    
    try {
      const response = await fetch('/api/dynamic-context/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: selectedFiles }),
      });

      if (response.ok) {
        const data = await response.json();
        startTaskMonitoring(data.task_id, 'upload', `${selectedFiles.length} files`, contentId);
        
        // Add success message
        const successMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `✅ Started processing ${selectedFiles.length} uploaded files. You can continue chatting while processing completes in the background. Check the content sidebar to track progress.`,
        };
        setMessages(prev => [...prev, successMessage]);
      } else {
        const errorData = await response.json();
        // Update content status to failed
        setUploadedContent(prev => prev.map(item => 
          item.id === contentId ? { ...item, status: 'failed' } : item
        ));
        throw new Error(errorData.detail || 'Failed to upload files');
      }
    } catch (error) {
      console.error('File upload error:', error);
      // Update content status to failed
      setUploadedContent(prev => prev.map(item => 
        item.id === contentId ? { ...item, status: 'failed' } : item
      ));
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'bot',
        content: `❌ Failed to upload files: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessingContent(false);
      setShowDynamicContext(false);
      setSelectedSource(null);
      setSelectedFiles([]);
    }
  };

  const handleURLSubmit = async (url: string) => {
    setIsProcessingContent(true);
    
    // Add to uploaded content tracking
    const contentId = Date.now().toString();
    const newContent = {
      id: contentId,
      type: 'url' as const,
      name: url,
      status: 'processing' as const,
      timestamp: new Date().toLocaleString(),
      details: { url }
    };
    setUploadedContent(prev => [...prev, newContent]);
    
    try {
      const response = await fetch('/api/dynamic-context/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      if (response.ok) {
        const data = await response.json();
        startTaskMonitoring(data.task_id, 'url', url, contentId);
        
        // Add success message
        const successMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `✅ Started processing content from URL: ${url}. You can continue chatting while processing completes in the background. Check the content sidebar to track progress.`,
        };
        setMessages(prev => [...prev, successMessage]);
      } else {
        // Update content status to failed
        setUploadedContent(prev => prev.map(item => 
          item.id === contentId ? { ...item, status: 'failed' } : item
        ));
        throw new Error('Failed to process URL');
      }
    } catch (error) {
      console.error('URL processing error:', error);
      // Update content status to failed
      setUploadedContent(prev => prev.map(item => 
        item.id === contentId ? { ...item, status: 'failed' } : item
      ));
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'bot',
        content: '❌ Failed to process URL. Please check the URL and try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessingContent(false);
      setShowDynamicContext(false);
      setSelectedSource(null);
    }
  };

  const handleGitHubSubmit = async (repoUrl: string) => {
    setIsProcessingContent(true);
    
    // Add to uploaded content tracking
    const contentId = Date.now().toString();
    const newContent = {
      id: contentId,
      type: 'github' as const,
      name: repoUrl.replace('https://github.com/', ''),
      status: 'processing' as const,
      timestamp: new Date().toLocaleString(),
      details: { repoUrl }
    };
    setUploadedContent(prev => [...prev, newContent]);
    
    try {
      const response = await fetch('/api/dynamic-context/github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      if (response.ok) {
        const data = await response.json();
        startTaskMonitoring(data.task_id, 'github', repoUrl, contentId);
        
        // Add success message
        const successMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `✅ Started processing GitHub repository: ${repoUrl}. You can continue chatting while processing completes in the background. Check the content sidebar to track progress.`,
        };
        setMessages(prev => [...prev, successMessage]);
      } else {
        // Update content status to failed
        setUploadedContent(prev => prev.map(item => 
          item.id === contentId ? { ...item, status: 'failed' } : item
        ));
        throw new Error('Failed to process GitHub repository');
      }
    } catch (error) {
      console.error('GitHub processing error:', error);
      // Update content status to failed
      setUploadedContent(prev => prev.map(item => 
        item.id === contentId ? { ...item, status: 'failed' } : item
      ));
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'bot',
        content: '❌ Failed to process GitHub repository. Please check the URL and try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessingContent(false);
      setShowDynamicContext(false);
      setSelectedSource(null);
    }
  };

  const startTaskMonitoring = (taskId: string, sourceType: 'upload' | 'url' | 'github', sourceIdentifier: string, contentId?: string) => {
    console.log(`Started monitoring task ${taskId} for ${sourceType}: ${sourceIdentifier}`);
    
    // Poll for status updates
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/dynamic-context/status/${taskId}`);
        if (response.ok) {
          const statusData = await response.json();
          
          if (contentId) {
            // Update content status
            setUploadedContent(prev => prev.map(item => 
              item.id === contentId ? { 
                ...item, 
                status: statusData.status === 'completed' ? 'completed' : 
                       statusData.status === 'failed' ? 'failed' : 'processing'
              } : item
            ));
          }
          
          // If still processing, continue polling
          if (statusData.status === 'pending' || statusData.status === 'extracting' || 
              statusData.status === 'vectorizing' || statusData.status === 'storing') {
            setTimeout(pollStatus, 2000); // Poll every 2 seconds
          }
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    };
    
    // Start polling after a short delay
    setTimeout(pollStatus, 1000);
  };

  const closeDynamicContext = () => {
    setShowDynamicContext(false);
    setSelectedSource(null);
    setSelectedFiles([]);
  };

  const getStatusColor = () => {
    if (!systemStatus) return 'loading';
    if (systemStatus.status === 'healthy') return '';
    return 'error';
  };

  const getStatusText = () => {
    if (!systemStatus) return 'Checking...';
    if (systemStatus.status === 'healthy') return 'All systems operational';
    return 'System issues detected';
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🏦 Integrated Lending Chatbot</h1>
        <div className="header-actions">
          <div className="status-indicator">
            <div className={`status-dot ${getStatusColor()}`}></div>
            <span>{getStatusText()}</span>
          </div>
          
          <DynamicContextDropdown
            onSourceSelect={handleSourceSelect}
            isProcessing={isProcessingContent}
          />
          
          <button
            className={`content-sidebar-toggle ${showContentSidebar ? 'active' : ''}`}
            onClick={() => setShowContentSidebar(!showContentSidebar)}
            title="Toggle content sidebar"
          >
            <FileText size={16} />
            Content ({uploadedContent.length})
          </button>
          
          <button
            className="init-button"
            onClick={initializeContext}
            disabled={isInitializing}
          >
            <Database size={16} />
            {isInitializing ? 'Initializing...' : 'Initialize Context'}
          </button>
        </div>
      </header>

      {/* Dynamic Context Modal */}
      {showDynamicContext && selectedSource && (
        <div className="dynamic-context-modal">
          <div className="modal-overlay" onClick={closeDynamicContext} />
          <div className="modal-content">
            <div className="modal-header">
              <h2>{selectedSource.label}</h2>
              <button 
                className="close-modal-btn"
                onClick={closeDynamicContext}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            
            <div className="modal-body">
              {selectedSource.type === 'upload' && (
                <FileUploadInterface
                  acceptedTypes={['text/plain', 'text/markdown', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                  maxFiles={10}
                  maxFileSize={10 * 1024 * 1024} // 10MB
                  onFilesSelected={handleFilesSelected}
                  onUpload={handleFileUpload}
                  isUploading={isProcessingContent}
                />
              )}
              
              {selectedSource.type === 'url' && (
                <URLInputInterface
                  placeholder="Enter URL to extract content from..."
                  onURLSubmit={handleURLSubmit}
                  isProcessing={isProcessingContent}
                />
              )}
              
              {selectedSource.type === 'github' && (
                <GitHubInputInterface
                  placeholder="Enter GitHub repository URL..."
                  onRepoSubmit={handleGitHubSubmit}
                  supportedFormats={['.md', '.txt', '.py', '.js', '.json', '.yml']}
                  isProcessing={isProcessingContent}
                />
              )}
            </div>
          </div>
        </div>
      )}

      <div className={`main-layout ${showContentSidebar ? 'with-sidebar' : ''}`}>
        {/* Content Sidebar */}
        {showContentSidebar && (
          <div className="content-sidebar">
            <div className="sidebar-header">
              <h3>
                <FileText size={18} />
                Dynamic Content
              </h3>
              <button 
                className="close-sidebar-btn"
                onClick={() => setShowContentSidebar(false)}
                aria-label="Close sidebar"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="sidebar-content">
              {uploadedContent.length === 0 ? (
                <div className="empty-content">
                  <FileText size={48} className="empty-icon" />
                  <p>No dynamic content added yet</p>
                  <p className="empty-subtitle">
                    Use "Add Dynamic Context" to upload files, URLs, or GitHub repositories
                  </p>
                  <div className="content-stats">
                    <div className="stat-item">
                      <span className="stat-label">Ready to process:</span>
                      <span className="stat-value">Files, URLs, GitHub repos</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="content-stats">
                  <div className="stats-row">
                    <div className="stat-item">
                      <span className="stat-label">Total:</span>
                      <span className="stat-value">{uploadedContent.length}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Completed:</span>
                      <span className="stat-value">{uploadedContent.filter(c => c.status === 'completed').length}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Processing:</span>
                      <span className="stat-value">{uploadedContent.filter(c => c.status === 'processing').length}</span>
                    </div>
                  </div>
                </div>
                
                <div className="content-list">
                  {uploadedContent.map((content) => (
                    <div key={content.id} className={`content-item ${content.status}`}>
                      <div className="content-header">
                        <div className="content-type-icon">
                          {content.type === 'upload' && <Upload size={16} />}
                          {content.type === 'url' && <Link size={16} />}
                          {content.type === 'github' && <Github size={16} />}
                        </div>
                        <div className="content-info">
                          <div className="content-name" title={content.name}>
                            {content.name.length > 30 ? `${content.name.substring(0, 30)}...` : content.name}
                          </div>
                          <div className="content-meta">
                            <span className="content-timestamp">{content.timestamp}</span>
                            <span className={`content-status ${content.status}`}>
                              {content.status === 'processing' && '⏳ Processing'}
                              {content.status === 'completed' && '✅ Completed'}
                              {content.status === 'failed' && '❌ Failed'}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      {content.details && (
                        <div className="content-details">
                          {content.type === 'upload' && content.details.files && (
                            <div className="file-details">
                              <strong>Files ({content.details.files.length}):</strong>
                              {content.details.files.map((file: any, index: number) => (
                                <div key={index} className="file-item">
                                  <span className="file-name">{file.name}</span>
                                  <span className="file-type">({file.type})</span>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {content.type === 'url' && (
                            <div className="url-details">
                              <strong>URL:</strong>
                              <a href={content.details.url} target="_blank" rel="noopener noreferrer" className="url-link">
                                {content.details.url}
                              </a>
                            </div>
                          )}
                          
                          {content.type === 'github' && (
                            <div className="github-details">
                              <strong>Repository:</strong>
                              <a href={content.details.repoUrl} target="_blank" rel="noopener noreferrer" className="repo-link">
                                {content.details.repoUrl}
                              </a>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="chat-container">
          <div className="messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome to the Lending Assistant! 🏦</h2>
              <p>Your intelligent assistant for lending processes and documentation.</p>
              <br />
              <div className="welcome-features">
                <div className="feature-item">
                  <span className="feature-icon">🔍</span>
                  <span>Ask about eKYC verification processes</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">📋</span>
                  <span>Learn about PAN validation requirements</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⚡</span>
                  <span>Explore business flows and API endpoints</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">🛡️</span>
                  <span>Understand security and compliance standards</span>
                </div>
              </div>
              <br />
              <p className="welcome-cta">Click "Initialize Context" to get started, then ask me anything!</p>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              {message.type === 'loading' ? (
                <>
                  <Activity size={16} />
                  {message.content}
                  <div className="loading-dots">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </>
              ) : (
                <>
                  <div dangerouslySetInnerHTML={{ 
                    __html: message.content.replace(/\n/g, '<br />').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  }} />
                  
                  {message.processingInfo && (
                    <div className="processing-info">
                      {message.processingInfo.memory_matches !== undefined && (
                        <div className="processing-stat">
                          <div className="stat-icon memory-icon"></div>
                          Memory: {message.processingInfo.memory_matches}
                        </div>
                      )}
                      {message.processingInfo.vector_matches !== undefined && (
                        <div className="processing-stat">
                          <div className="stat-icon vector-icon"></div>
                          Vector: {message.processingInfo.vector_matches}
                        </div>
                      )}
                      {message.processingInfo.graph_matches !== undefined && (
                        <div className="processing-stat">
                          <div className="stat-icon graph-icon"></div>
                          Graph: {message.processingInfo.graph_matches}
                        </div>
                      )}
                      {message.processingInfo.conversation_matches !== undefined && message.processingInfo.conversation_matches > 0 && (
                        <div className="processing-stat">
                          <div className="stat-icon conversation-icon"></div>
                          Conversation: {message.processingInfo.conversation_matches}
                        </div>
                      )}
                      {message.processingInfo.hybrid_matches !== undefined && message.processingInfo.hybrid_matches > 0 && (
                        <div className="processing-stat">
                          <div className="stat-icon hybrid-icon"></div>
                          Hybrid: {message.processingInfo.hybrid_matches}
                        </div>
                      )}
                      <div className="processing-stat">
                        <div className="stat-icon fusion-icon"></div>
                        Total: {message.processingInfo.total_context_items}
                        {message.processingInfo.enhanced_fusion && <span className="enhanced-badge">Enhanced</span>}
                      </div>
                    </div>
                  )}
                  
                  {message.contextItems && message.contextItems.length > 0 && (
                    <div className="context-info">
                      <strong>Context Sources:</strong>
                      {message.contextItems.map((item, index) => (
                        <div key={index} className="context-item">
                          {item}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <div className="input-form">
            <div className="input-wrapper">
              <textarea
                className="message-input"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about lending processes, eKYC verification, PAN validation, business flows..."
                disabled={isLoading}
                rows={1}
              />
            </div>
            <button
              className="send-button"
              onClick={sendMessage}
              disabled={isLoading || !inputValue.trim()}
            >
              <Send size={16} />
              Send
            </button>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

export default App;