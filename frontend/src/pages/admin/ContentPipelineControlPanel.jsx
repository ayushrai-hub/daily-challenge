import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './admin.css';
import './content-pipeline.css';

// API base URL from environment variable or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const ContentPipelineControlPanel = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [pipelineHistory, setPipelineHistory] = useState([]);
  const [taskStatus, setTaskStatus] = useState(null);
  const [formData, setFormData] = useState({
    ai_provider: 'claude',
    num_problems: 1,
    auto_approve: false,
    github_params: {
      repo: 'microsoft/vscode',
      content_type: 'code',
      max_items: 5
    },
    stackoverflow_params: {
      tags: ['python', 'fastapi'],
      content_type: 'questions',
      sort: 'votes',
      max_items: 5
    }
  });
  
  // Source selection state
  const [useSources, setUseSources] = useState({
    github: true,
    stackoverflow: true
  });
  const [formErrors, setFormErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Pre-defined suggestions for Stack Overflow tags
  const suggestedTags = [
    'python', 'javascript', 'java', 'c#', 'php', 'android', 'html', 'jquery', 'css',
    'ios', 'mysql', 'sql', 'node.js', 'arrays', 'c++', 'reactjs', 'ruby-on-rails',
    'swift', 'django', 'angular', 'excel', 'regex', 'pandas', 'ruby', 'json',
    'iphone', 'google-cloud', 'amazon-web-services', 'docker', 'mongodb', 'react-native',
    'typescript', 'linux', 'spring', 'git', 'firebase', 'flutter', 'fastapi', 'go', 'rust'
  ];

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name.includes('.')) {
      // Handle nested properties like github_params.repo
      const [parent, child] = name.split('.');
      setFormData({
        ...formData,
        [parent]: {
          ...formData[parent],
          [child]: type === 'number' ? Number(value) : value
        }
      });
    } else if (type === 'checkbox') {
      setFormData({
        ...formData,
        [name]: checked
      });
    } else if (type === 'number') {
      setFormData({
        ...formData,
        [name]: Number(value)
      });
    } else {
      setFormData({
        ...formData,
        [name]: value
      });
    }
  };

  // Handle tag selection
  const handleTagSelection = (tag) => {
    // Get current tags
    const currentTags = [...formData.stackoverflow_params.tags];
    
    // If tag is already selected, remove it
    if (currentTags.includes(tag)) {
      const updatedTags = currentTags.filter(t => t !== tag);
      setFormData({
        ...formData,
        stackoverflow_params: {
          ...formData.stackoverflow_params,
          tags: updatedTags
        }
      });
    } else {
      // Add the tag
      setFormData({
        ...formData,
        stackoverflow_params: {
          ...formData.stackoverflow_params,
          tags: [...currentTags, tag]
        }
      });
    }
  };
  
  // Handle tag input
  const handleTagInput = (e) => {
    if (e.key === 'Enter' && e.target.value.trim() !== '') {
      e.preventDefault();
      const newTag = e.target.value.trim().toLowerCase();
      
      if (!formData.stackoverflow_params.tags.includes(newTag)) {
        setFormData({
          ...formData,
          stackoverflow_params: {
            ...formData.stackoverflow_params,
            tags: [...formData.stackoverflow_params.tags, newTag]
          }
        });
      }
      
      e.target.value = '';
    }
  };

  // Handle source toggle
  const handleSourceToggle = (source) => {
    const newSourceState = !useSources[source];
    
    // If trying to disable and this would leave no sources enabled
    if (!newSourceState && Object.keys(useSources).filter(key => key !== source && useSources[key]).length === 0) {
      setErrorMessage('At least one source (GitHub or Stack Overflow) must be selected');
      setTimeout(() => setErrorMessage(''), 3000);
      return;
    }

    setUseSources({
      ...useSources,
      [source]: newSourceState
    });

    // Clear errors when enabling a source
    if (newSourceState) {
      const newErrors = {...formErrors};
      if (source === 'github') {
        delete newErrors.github_repo;
      } else if (source === 'stackoverflow') {
        delete newErrors.tags;
      }
      setFormErrors(newErrors);
    }
  };

  // Validate form before submission
  const validateForm = () => {
    const errors = {};
    
    if (!formData.ai_provider) {
      errors.ai_provider = 'AI provider is required';
    }
    
    if (formData.num_problems < 1 || formData.num_problems > 10) {
      errors.num_problems = 'Number of problems must be between 1 and 10';
    }
    
    // Make sure at least one source is enabled
    if (!useSources.github && !useSources.stackoverflow) {
      errors.sources = 'At least one source (GitHub or Stack Overflow) must be selected';
    }

    // Validate GitHub params if enabled
    if (useSources.github) {
      if (!formData.github_params.repo) {
        errors.github_repo = 'GitHub repository is required';
      }
      
      if (formData.github_params.max_items < 1 || formData.github_params.max_items > 20) {
        errors.github_max_items = 'Max items must be between 1 and 20';
      }
    }
    
    // Validate Stack Overflow params if enabled
    if (useSources.stackoverflow) {
      if (formData.stackoverflow_params.tags.length === 0) {
        errors.tags = 'At least one Stack Overflow tag is required';
      }
      
      if (formData.stackoverflow_params.max_items < 1 || formData.stackoverflow_params.max_items > 20) {
        errors.stackoverflow_max_items = 'Max items must be between 1 and 20';
      }
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Function to poll task status
  const pollTaskStatus = async (taskId) => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.error('No auth token found');
        return;
      }

      const response = await axios.get(`${API_BASE_URL}/admin/content/pipeline/task/${taskId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const taskData = response.data;
      const status = taskData.status.toLowerCase();

      // Update task status in component state
      if (status === 'success') {
        // Task completed successfully
        setTaskStatus({
          id: taskId,
          status: 'completed',
          message: `Task completed! Generated ${taskData.result?.problems_saved || 0} problems.`,
          result: taskData.result
        });

        // Update task in history
        setPipelineHistory(prevHistory => 
          prevHistory.map(item => 
            item.id === taskId 
              ? { ...item, status: 'completed' } 
              : item
          )
        );

        return true; // Signal polling can stop
      } 
      else if (status === 'failure' || status === 'failed') {
        // Task failed
        setTaskStatus({
          id: taskId,
          status: 'failed',
          message: `Task failed: ${taskData.error || 'Unknown error'}.`,
          error: taskData.error
        });

        // Update task in history
        setPipelineHistory(prevHistory => 
          prevHistory.map(item => 
            item.id === taskId 
              ? { ...item, status: 'failed' } 
              : item
          )
        );

        return true; // Signal polling can stop
      }
      
      // Task still running
      return false; // Continue polling
    } catch (error) {
      console.error(`Error polling task ${taskId} status:`, error);
      return false; // Continue polling in case of transient error
    }
  };

  // Set up polling for active tasks
  useEffect(() => {
    // Don't poll if no active task
    if (!taskStatus || taskStatus.status !== 'pending') return;
    
    const taskId = taskStatus.id;
    let pollInterval;
    
    const startPolling = async () => {
      // Check immediately first
      const shouldStop = await pollTaskStatus(taskId);
      
      // If task completed or failed, don't set up interval
      if (shouldStop) return;
      
      // Otherwise poll every 5 seconds
      pollInterval = setInterval(async () => {
        const shouldStop = await pollTaskStatus(taskId);
        if (shouldStop) {
          clearInterval(pollInterval);
        }
      }, 5000);
    };
    
    startPolling();
    
    // Clean up interval on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [taskStatus?.id, taskStatus?.status]);

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Clear previous messages
    setSuccessMessage('');
    setErrorMessage('');
    
    // Validate form
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        navigate('/login', { replace: true });
        return;
      }
      
      // Create request payload with only enabled sources
      const requestPayload = {
        ai_provider: formData.ai_provider,
        num_problems: formData.num_problems,
        auto_approve: formData.auto_approve
      };
      
      // Only include GitHub params if that source is enabled
      if (useSources.github) {
        requestPayload.github_params = formData.github_params;
      }
      
      // Only include Stack Overflow params if that source is enabled
      if (useSources.stackoverflow) {
        requestPayload.stackoverflow_params = formData.stackoverflow_params;
      }
      
      const response = await axios.post(
        `${API_BASE_URL}/admin/content/pipeline/trigger`,
        requestPayload,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.data.success) {
        const taskId = response.data.task_id;
        setSuccessMessage('Content pipeline triggered successfully! Task ID: ' + taskId);
        setTaskStatus({
          id: taskId,
          status: 'pending',
          message: 'Task submitted and processing. This may take several minutes.'
        });
        
        // Determine which tags to show in history
        let tagsString = '';
        if (useSources.stackoverflow && requestPayload.stackoverflow_params?.tags) {
          tagsString = requestPayload.stackoverflow_params.tags.join(', ');
        }
        
        // Add to history
        setPipelineHistory([
          {
            id: taskId,
            timestamp: new Date().toISOString(),
            aiProvider: formData.ai_provider,
            numProblems: formData.num_problems,
            autoApprove: formData.auto_approve,
            tags: tagsString,
            status: 'pending'
          },
          ...pipelineHistory
        ]);
      } else {
        setErrorMessage('Failed to trigger content pipeline: ' + (response.data.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error triggering content pipeline:', error);
      setErrorMessage('Error: ' + (error.response?.data?.detail || error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  if (loading && !taskStatus) {
    return <div className="loading">Loading content pipeline control panel...</div>;
  }


  return (
    <div className="admin-panel content-pipeline-panel">
      <div className="admin-header">
        <h1>Content Pipeline Control Panel</h1>
        <p className="panel-description">
          Manually trigger the content generation pipeline to create new coding problems from GitHub and Stack Overflow sources.
        </p>
      </div>

      {taskStatus && (
        <div className={`task-status task-status-${taskStatus.status}`}>
          <h3>Task Status</h3>
          <p><strong>Task ID:</strong> {taskStatus.id}</p>
          <p>
            <strong>Status:</strong> 
            <span className={`status-badge status-${taskStatus.status}`}>
              {taskStatus.status === 'pending' ? 'Pending' : 
               taskStatus.status === 'completed' ? 'Completed' : 'Failed'}
            </span>
          </p>
          <p>{taskStatus.message}</p>
          
          {taskStatus.status === 'completed' && taskStatus.result && (
            <div className="task-result">
              <p><strong>Results:</strong></p>
              <ul>
                <li>Problems generated: {taskStatus.result.problems_generated}</li>
                <li>Problems saved: {taskStatus.result.problems_saved}</li>
                {taskStatus.result.saved_problem_ids && taskStatus.result.saved_problem_ids.length > 0 && (
                  <li>
                    Problem IDs: 
                    <ul>
                      {taskStatus.result.saved_problem_ids.map(id => (
                        <li key={id}><code>{id}</code></li>
                      ))}
                    </ul>
                  </li>
                )}
              </ul>
            </div>
          )}
          
          {taskStatus.status === 'failed' && taskStatus.error && (
            <div className="task-error">
              <p><strong>Error:</strong> {taskStatus.error}</p>
            </div>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
        </div>
      )}

      <div className="form-container">
        <form onSubmit={handleSubmit} className="pipeline-form">
          <div className="form-section">
            <h3>AI Configuration</h3>
            
            <div className="form-group">
              <label htmlFor="ai_provider">AI Provider</label>
              <select
                id="ai_provider"
                name="ai_provider"
                value={formData.ai_provider}
                onChange={handleInputChange}
                className={formErrors.ai_provider ? 'error' : ''}
              >
                <option value="claude">Claude</option>
                <option value="gemini">Gemini</option>
              </select>
              {formErrors.ai_provider && <div className="error-text">{formErrors.ai_provider}</div>}
            </div>
            
            <div className="form-group">
              <label htmlFor="num_problems">Number of Problems to Generate</label>
              <input
                type="number"
                id="num_problems"
                name="num_problems"
                min="1"
                max="10"
                value={formData.num_problems}
                onChange={handleInputChange}
                className={formErrors.num_problems ? 'error' : ''}
              />
              {formErrors.num_problems && <div className="error-text">{formErrors.num_problems}</div>}
            </div>
            
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  id="auto_approve"
                  name="auto_approve"
                  checked={formData.auto_approve}
                  onChange={handleInputChange}
                />
                Auto-approve generated problems
              </label>
              <div className="help-text">
                If checked, problems will be automatically published without manual review.
              </div>
            </div>
          </div>

          <div className="form-section sources-section">
            <h3>Content Sources</h3>
            
            <div className="source-toggles">
              <div className="source-toggle-group">
                <label>
                  <input
                    type="checkbox"
                    checked={useSources.github}
                    onChange={() => handleSourceToggle('github')}
                  />
                  GitHub Source
                </label>
              </div>
              
              <div className="source-toggle-group">
                <label>
                  <input
                    type="checkbox"
                    checked={useSources.stackoverflow}
                    onChange={() => handleSourceToggle('stackoverflow')}
                  />
                  Stack Overflow Source
                </label>
              </div>
            </div>
            
            {formErrors.sources && <div className="error-text sources-error">{formErrors.sources}</div>}
            
            <div className="source-info">
              At least one source must be selected. You can use both sources together or just one.
            </div>
          </div>

          {useSources.github && (
            <div className="form-section">
              <h3>GitHub Source Configuration</h3>
              
              <div className="form-group">
                <label htmlFor="github_params.repo">GitHub Repository</label>
                <input
                  type="text"
                  id="github_params.repo"
                  name="github_params.repo"
                  value={formData.github_params.repo}
                  onChange={handleInputChange}
                  placeholder="e.g., microsoft/vscode"
                  className={formErrors.github_repo ? 'error' : ''}
                />
                {formErrors.github_repo && <div className="error-text">{formErrors.github_repo}</div>}
              </div>
              
              <div className="form-group">
                <label htmlFor="github_params.content_type">Content Type</label>
                <select
                  id="github_params.content_type"
                  name="github_params.content_type"
                  value={formData.github_params.content_type}
                  onChange={handleInputChange}
                >
                  <option value="code">Code</option>
                  <option value="issues">Issues</option>
                  <option value="pull_requests">Pull Requests</option>
                </select>
              </div>
              
              <div className="form-group">
                <label htmlFor="github_params.max_items">Max Items</label>
                <input
                  type="number"
                  id="github_params.max_items"
                  name="github_params.max_items"
                  min="1"
                  max="20"
                  value={formData.github_params.max_items}
                  onChange={handleInputChange}
                  className={formErrors.github_max_items ? 'error' : ''}
                />
                {formErrors.github_max_items && <div className="error-text">{formErrors.github_max_items}</div>}
              </div>
            </div>
          )}

          {useSources.stackoverflow && (
            <div className="form-section">
              <h3>Stack Overflow Source Configuration</h3>
              
              <div className="form-group">
                <label>Tags</label>
                <div className="tag-input-container">
                  <input
                    type="text"
                    placeholder="Type a tag and press Enter"
                    onKeyDown={handleTagInput}
                    className="tag-input"
                  />
                  <div className="tag-help">Popular tags are suggested below, or type your own and press Enter</div>
                </div>
                
                <div className="selected-tags-container">
                  {formData.stackoverflow_params.tags.map(tag => (
                    <div key={tag} className="selected-tag">
                      {tag}
                      <button 
                        type="button" 
                        className="remove-tag" 
                        onClick={() => handleTagSelection(tag)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                
                <div className="tag-selector">
                  {suggestedTags.map(tag => (
                    <div 
                      key={tag} 
                      className={`tag-option ${formData.stackoverflow_params.tags.includes(tag) ? 'selected' : ''}`}
                      onClick={() => handleTagSelection(tag)}
                    >
                      {tag}
                    </div>
                  ))}
                </div>
                {formErrors.tags && <div className="error-text">{formErrors.tags}</div>}
              </div>
              
              <div className="form-group">
                <label htmlFor="stackoverflow_params.content_type">Content Type</label>
                <select
                  id="stackoverflow_params.content_type"
                  name="stackoverflow_params.content_type"
                  value={formData.stackoverflow_params.content_type}
                  onChange={handleInputChange}
                >
                  <option value="questions">Questions</option>
                  <option value="answers">Answers</option>
                </select>
              </div>
              
              <div className="form-group">
                <label htmlFor="stackoverflow_params.sort">Sort Method</label>
                <select
                  id="stackoverflow_params.sort"
                  name="stackoverflow_params.sort"
                  value={formData.stackoverflow_params.sort}
                  onChange={handleInputChange}
                >
                  <option value="votes">Votes</option>
                  <option value="creation">Creation Date</option>
                  <option value="activity">Activity</option>
                </select>
              </div>
              
              <div className="form-group">
                <label htmlFor="stackoverflow_params.max_items">Max Items</label>
                <input
                  type="number"
                  id="stackoverflow_params.max_items"
                  name="stackoverflow_params.max_items"
                  min="1"
                  max="20"
                  value={formData.stackoverflow_params.max_items}
                  onChange={handleInputChange}
                  className={formErrors.stackoverflow_max_items ? 'error' : ''}
                />
                {formErrors.stackoverflow_max_items && <div className="error-text">{formErrors.stackoverflow_max_items}</div>}
              </div>
            </div>
          )}

          <div className="form-actions">
            <button 
              type="submit" 
              className="trigger-button" 
              disabled={loading}
            >
              {loading ? 'Triggering...' : 'Trigger Content Pipeline'}
            </button>
          </div>
        </form>
      </div>

      {pipelineHistory.length > 0 && (
        <div className="history-section">
          <h3>Pipeline Trigger History</h3>
          <div className="history-table-container">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Task ID</th>
                  <th>AI Provider</th>
                  <th>Problems</th>
                  <th>Auto-Approve</th>
                  <th>Tags</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {pipelineHistory.map(entry => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.timestamp).toLocaleString()}</td>
                    <td>{entry.id}</td>
                    <td>{entry.aiProvider}</td>
                    <td>{entry.numProblems}</td>
                    <td>{entry.autoApprove ? 'Yes' : 'No'}</td>
                    <td>{entry.tags}</td>
                    <td>
                      <span className={`status-badge ${entry.status}`}>
                        {entry.status.charAt(0).toUpperCase() + entry.status.slice(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentPipelineControlPanel;
