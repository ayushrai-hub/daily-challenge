import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './admin.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const ProblemManagement = () => {
  const [problems, setProblems] = useState([]);
  const [filteredProblems, setFilteredProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({
    status: 'all',
    tier: 'all',
    difficulty: 'all',
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [currentProblem, setCurrentProblem] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState('view'); // 'view', 'approve', or 'reject'
  const [reviewComment, setReviewComment] = useState('');
  const [actionInProgress, setActionInProgress] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('approved');
  
  // Status options for dropdown
  const statusOptions = [
    { value: 'approved', label: 'Approved' },
    { value: 'pending', label: 'Pending Review' },
    { value: 'draft', label: 'Draft' },
    { value: 'archived', label: 'Archived' }
  ];

  const fetchProblems = async () => {
    // Use the current filter state
    fetchProblemsWithFilter(filter);
  };

  // Apply filters to problems
  const applyFilters = (data) => {
    let filtered = [...data];
    
    // Apply vetting tier filter (client-side)
    if (filter.tier !== 'all') {
      filtered = filtered.filter(problem => problem.vetting_tier === filter.tier);
      console.log(`After tier filtering: ${filtered.length} problems with tier ${filter.tier}`);
    }
    
    // Apply client-side difficulty filter as fallback if backend filter didn't work
    // We can detect this if the response contains problems with different difficulties
    if (filter.difficulty !== 'all') {
      const difficultyValues = new Set(filtered.map(p => p.difficulty_level));
      // If we have multiple difficulty values but a specific one was requested,
      // apply client-side filtering
      if (difficultyValues.size > 1) {
        console.log(`Applying client-side difficulty filter for: ${filter.difficulty}`);
        filtered = filtered.filter(problem => 
          String(problem.difficulty_level).toLowerCase() === filter.difficulty.toLowerCase()
        );
        console.log(`After difficulty filtering: ${filtered.length} problems`);
      }
    }
    
    // Apply search term filter if it exists
    if (searchTerm && searchTerm.trim() !== '') {
      const lowerSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(problem => 
        problem.title.toLowerCase().includes(lowerSearch) || 
        (problem.description && problem.description.toLowerCase().includes(lowerSearch))
      );
      console.log(`After search term filtering: ${filtered.length} problems`);
    }
    
    setFilteredProblems(filtered);
  };
  
  // Initial data fetch - load all problems on component mount
  useEffect(() => {
    // Set status to 'all' to ensure we get all problems initially
    const initialFilter = {
      ...filter,
      status: 'all'
    };
    setFilter(initialFilter);
    
    // Fetch all problems on initial load
    fetchProblemsWithFilter(initialFilter);
  }, []);
  
  // Re-apply filters when filter or search changes
  useEffect(() => {
    applyFilters(problems);
  }, [filter, searchTerm, problems]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    console.log(`Filter changed: ${name} = ${value}`);
    
    // Create the new filter state
    const newFilter = {
      ...filter,
      [name]: value
    };
    console.log('New filter state:', newFilter);
    
    // Update the filter state
    setFilter(newFilter);
    // No immediate API call, just update the filter state
  };
  
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };
  
  // Handle search button click
  const handleSearch = () => {
    // Make API call with combined filters
    console.log('Search button clicked with filters:', filter);
    fetchProblemsWithFilter(filter);
  };

  // This function fetches problems with a specific filter
  const fetchProblemsWithFilter = async (filterToUse) => {
    try {
      setLoading(true);
      
      // Build query parameters
      const params = new URLSearchParams();
      
      // Only add status parameter if it's not 'all'
      if (filterToUse.status !== 'all') {
        // Make sure to use the correct enum values the API expects
        const statusMap = {
          'approved': 'approved',
          'pending': 'pending',
          'draft': 'draft',
          'archived': 'archived'
        };
        
        const apiStatus = statusMap[filterToUse.status];
        if (apiStatus) {
          params.append('status', apiStatus);
        }
      }
      
      // Only add difficulty parameter if it's not 'all'
      if (filterToUse.difficulty !== 'all') {
        // Make sure to use the correct enum values the API expects
        const difficultyMap = {
          'easy': 'easy',
          'medium': 'medium',
          'hard': 'hard'
        };
        
        // Try different parameter names since the backend might be expecting a specific one
        // First try difficulty_level as that's what we see in the response data
        params.append('difficulty_level', difficultyMap[filterToUse.difficulty]);
        
        // Also add the standard difficulty parameter as a fallback
        params.append('difficulty', difficultyMap[filterToUse.difficulty]);
        
        console.log(`Adding difficulty filter: ${difficultyMap[filterToUse.difficulty]}`);
      }
      
      const token = localStorage.getItem('auth_token');
      
      // Debug log to check what parameters are being sent
      console.log(`API call with params: ${params.toString()}`);
      
      // Use the admin-specific endpoint instead of the general problems endpoint
      const response = await axios.get(`${API_BASE_URL}/admin/problems?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      // Debug log the response
      console.log('Total problems returned:', response.data.length);
      
      // Log sample problems to check their structure
      if (response.data.length > 0) {
        console.log('Sample problem data:', response.data[0]);
        console.log('Sample difficulty field:', response.data[0].difficulty_level);
        
        // Check if any problems actually have the requested difficulty
        if (filterToUse.difficulty !== 'all') {
          const matchingDifficulty = response.data.filter(p => 
            p.difficulty_level === filterToUse.difficulty || 
            p.difficulty === filterToUse.difficulty
          );
          
          console.log(`Problems with ${filterToUse.difficulty} difficulty: ${matchingDifficulty.length} out of ${response.data.length}`);
        }
      }
      
      setProblems(response.data);
      applyFilters(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching problems:', err);
      setError('Failed to load problems. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle opening the problem details modal
  const handleViewProblem = (problem) => {
    setCurrentProblem(problem);
    setReviewComment('');
    setModalType('view');
    setIsModalOpen(true);
  };

  // Handle opening the problem approval modal
  const handleApproveModal = (problem) => {
    setCurrentProblem(problem);
    setReviewComment('');
    setModalType('approve');
    setIsModalOpen(true);
  };

  // Handle opening the mark for review modal (changed from rejection)
  const handleRejectModal = (problem) => {
    setCurrentProblem(problem);
    setReviewComment('');
    setModalType('reject'); // Keep the same modal type to avoid changing too much code
    setIsModalOpen(true);
  };

  // Handle archiving a problem
  const handleArchive = async (problemId) => {
    if (window.confirm('Are you sure you want to archive this problem?')) {
      try {
        setActionInProgress(true);
        const token = localStorage.getItem('auth_token');
        await axios.put(`${API_BASE_URL}/problems/${problemId}/status`, {
          status: 'archived',
          reviewer_notes: 'Problem archived by administrator'
        }, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        setSuccessMessage('Problem archived successfully');
        // Refresh problems list
        fetchProblems();
      } catch (err) {
        console.error('Error archiving problem:', err);
        setError('Failed to archive problem. Please try again.');
      } finally {
        setActionInProgress(false);
      }
    }
  };

  // Handle problem approval submission
  const handleApprove = async () => {
    if (!currentProblem) return;
    
    try {
      setActionInProgress(true);
      const token = localStorage.getItem('auth_token');
      
      // Log the problem tags before approval for debugging
      if (currentProblem.tags && currentProblem.tags.length > 0) {
        console.log('Tags before approval:', currentProblem.tags);
      }
      
      // Make the approval API request
      const response = await axios.post(`${API_BASE_URL}/problems/${currentProblem.id}/approve`, {
        reviewer_notes: reviewComment,
        status: selectedStatus // Send the selected status to the API
      }, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      // Log the response which may contain updated tag information
      console.log('Approval response:', response.data);
      
      // Create a more informative success message based on the status
      let statusText = '';
      switch(selectedStatus) {
        case 'approved':
          statusText = 'approved';
          break;
        case 'pending':
          statusText = 'set to pending';
          break;
        case 'draft':
          statusText = 'moved to draft';
          break;
        case 'archived':
          statusText = 'archived';
          break;
        default:
          statusText = 'updated';
      }
      
      let message = `Problem ${statusText} successfully!`;
      
      // Add tag-related information to the success message if applicable
      if (selectedStatus === 'approved' && currentProblem.tags && currentProblem.tags.length > 0) {
        message += ` ${currentProblem.tags.length} associated tags have been updated to safe status.`;
      }
      
      setSuccessMessage(message);
      setIsModalOpen(false);
      
      // Reset the selected status back to approved for next time
      setSelectedStatus('approved');
      
      // Refresh problems list to show updated status
      fetchProblems();
    } catch (err) {
      console.error('Error updating problem:', err);
      setError(`Failed to update problem. ${err.response && err.response.data && err.response.data.detail ? err.response.data.detail : 'Please try again.'}`);
    } finally {
      setActionInProgress(false);
    }
  };

  // Handle marking problem for review (changed from rejection)
  const handleReject = async () => {
    if (!currentProblem) return;
    
    try {
      setActionInProgress(true);
      const token = localStorage.getItem('auth_token');
      await axios.put(`${API_BASE_URL}/problems/${currentProblem.id}/status`, {
        status: 'pending', // Changed from 'draft' to 'pending'
        reviewer_notes: reviewComment
      }, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      setSuccessMessage('Problem marked for review successfully');
      setIsModalOpen(false);
      fetchProblems();
    } catch (err) {
      console.error('Error marking problem for review:', err);
      setError('Failed to mark problem for review. Please try again.');
    } finally {
      setActionInProgress(false);
    }
  };
  
  // Handle modal close
  const handleModalClose = () => {
    setIsModalOpen(false);
    setCurrentProblem(null);
    setReviewComment('');
  };
  
  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const month = months[date.getMonth()];
    const day = date.getDate();
    const year = date.getFullYear();
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const formattedHours = hours % 12 || 12;
    
    return `${month} ${day}, ${year} ${formattedHours}:${minutes} ${ampm}`;
  };

  // Get status badge class
  const getStatusClass = (status) => {
    switch (status) {
      case 'approved': return 'status-badge approved';
      case 'draft': return 'status-badge draft';
      case 'archived': return 'status-badge archived';
      case 'pending': return 'status-badge pending';
      default: return 'status-badge';
    }
  };
  
  // Format status for display
  const formatStatus = (status) => {
    switch (status) {
      case 'approved': return 'Approved';
      case 'draft': return 'Draft';
      case 'archived': return 'Archived';
      case 'pending': return 'Pending Review';
      default: return status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
    }
  };

  // Get difficulty badge class
  const getDifficultyClass = (difficulty) => {
    // Normalize the difficulty value
    const difficultyValue = String(difficulty).toLowerCase();
    
    switch (difficultyValue) {
      case 'easy': return 'difficulty-badge easy';
      case 'medium': return 'difficulty-badge medium';
      case 'hard': return 'difficulty-badge hard';
      default: return 'difficulty-badge';
    }
  };
  
  // Format difficulty for display
  const formatDifficulty = (difficulty) => {
    if (!difficulty) return 'Unknown';
    
    const difficultyValue = String(difficulty).toLowerCase();
    
    switch (difficultyValue) {
      case 'easy': return 'Easy';
      case 'medium': return 'Medium';
      case 'hard': return 'Hard';
      default: return difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
    }
  };

  // Get vetting tier badge class
  const getVettingTierClass = (tier) => {
    // Handle both numerical and string representations of tiers
    const tierValue = String(tier).toLowerCase();
    
    switch (tierValue) {
      case '1':
      case 'tier1':
      case 'tier1_manual': 
        return 'vetting-badge tier1';
      case '2':
      case 'tier2':
      case 'tier2_ai': 
        return 'vetting-badge tier2';
      case '3':
      case 'tier3':
      case 'tier3_needs_review': 
        return 'vetting-badge tier3';
      default: 
        return 'vetting-badge';
    }
  };
  
  // Format vetting tier for display
  const formatVettingTier = (tier) => {
    // Handle both numerical and string representations of tiers
    const tierValue = String(tier).toLowerCase();
    
    switch (tierValue) {
      case '1':
      case 'tier1':
      case 'tier1_manual': 
        return 'Tier 1 (Manual)';
      case '2':
      case 'tier2':
      case 'tier2_ai': 
        return 'Tier 2 (AI)';
      case '3':
      case 'tier3':
      case 'tier3_needs_review': 
        return 'Tier 3 (Needs Review)';
      default: 
        return `Tier ${tier}`;
    }
  };
  // Render modal content based on type
  const renderModalContent = () => {
    if (!currentProblem) return null;

    return (
      <div className="problem-details-content">
        <h4>{currentProblem.title}</h4>
        
        <div className="problem-meta-row">
          <div className="meta-item">
            <strong>Status:</strong> <span className={getStatusClass(currentProblem.status)}>{formatStatus(currentProblem.status)}</span>
          </div>
          <div className="meta-item">
            <strong>Difficulty:</strong> <span className={getDifficultyClass(currentProblem.difficulty_level)}>{formatDifficulty(currentProblem.difficulty_level)}</span>
          </div>
          <div className="meta-item">
            <strong>Vetting Tier:</strong> <span className={getVettingTierClass(currentProblem.vetting_tier)}>{formatVettingTier(currentProblem.vetting_tier)}</span>
          </div>
          {currentProblem.approved_at && (
            <div className="meta-item">
              <strong>Approved:</strong> {formatDate(currentProblem.approved_at)}
            </div>
          )}
        </div>
        
        {/* Tags Section */}
        {currentProblem.tags && currentProblem.tags.length > 0 && (
          <div className="tags-container">
            <div className="tags-header">
              <strong>Associated Tags:</strong>
            </div>
            <div className="tags-list">
              {currentProblem.tags.map((tag, index) => (
                <span key={index} className="tag-badge">
                  {tag.name || tag}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {/* Problem Description */}
        <div className="content-section">
          <h3>Description</h3>
          <div className="content-box problem-description">
            <div dangerouslySetInnerHTML={{ __html: currentProblem.rendered_description || currentProblem.description }} />
          </div>
        </div>
        
        {currentProblem.solution && (
          <div className="content-section">
            <h3>Solution</h3>
            <div className="content-box problem-solution">
              <div dangerouslySetInnerHTML={{ __html: currentProblem.rendered_solution || currentProblem.solution }} />
            </div>
          </div>
        )}
        
        {/* Review Form */}
        {(modalType === 'approve' || modalType === 'reject') && (
          <div className="review-form">
            {/* Status Selection for Approve Modal */}
            {modalType === 'approve' && (
              <div className="form-group">
                <label>Set Status:</label>
                <select
                  className="form-control"
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                >
                  {statusOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small className="form-text text-muted">
                  When approved, all tags will be moved to safe status.
                </small>
              </div>
            )}
            
            <div className="form-group">
              <label>Reviewer Notes:</label>
              <textarea
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                placeholder="Add notes about this review..."
                rows={4}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="admin-container">
      <h1 className="admin-heading">Problem Management</h1>
      
      {loading && <div className="loading">Loading...</div>}
      
      {error && (
        <div className="error-message">
          {error}
          <button className="close-button" onClick={() => setError(null)}>
            &times;
          </button>
        </div>
      )}
      
      {successMessage && (
        <div className="success-message">
          {successMessage}
          <button className="close-button" onClick={() => setSuccessMessage('')}>
            &times;
          </button>
        </div>
      )}

      <div className="content-box filter-controls">
        <div className="row">
          <div className="col-md-3">
            <div className="form-group">
              <label>Status:</label>
              <select 
                name="status" 
                className="form-control" 
                value={filter.status} 
                onChange={handleFilterChange}
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="draft">Draft</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
          
          <div className="col-md-3">
            <div className="form-group">
              <label>Vetting Tier:</label>
              <select 
                name="tier" 
                className="form-control"
                value={filter.tier}
                onChange={handleFilterChange}
              >
                <option value="all">All Tiers</option>
                <option value="tier1_manual">Tier 1 (Manual)</option>
                <option value="tier2_ai">Tier 2 (AI)</option>
                <option value="tier3_needs_review">Tier 3 (Needs Review)</option>
              </select>
            </div>
          </div>
          
          <div className="col-md-3">
            <div className="form-group">
              <label>Difficulty:</label>
              <select 
                name="difficulty" 
                className="form-control" 
                value={filter.difficulty}
                onChange={handleFilterChange}
              >
                <option value="all">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>
          
          <div className="col-md-3">
            <div className="form-group">
              <label>Search:</label>
              <input 
                type="text" 
                className="form-control" 
                placeholder="Search problems..." 
                value={searchTerm}
                onChange={handleSearchChange}
              />
            </div>
          </div>
          
          <div className="col-md-12 text-center mt-3">
            <button 
              className="btn btn-primary btn-search" 
              onClick={handleSearch}
            >
              <i className="fa fa-search"></i> Search Problems
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">Loading problems...</div>
      ) : (
        <div className="table-responsive">
          <table className="table table-striped problem-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Difficulty</th>
                <th>Tier</th>
                <th>Last Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProblems.length > 0 ? (
                filteredProblems.map((problem) => (
                  <tr key={problem.id}>
                    <td>{problem.title}</td>
                    <td><span className={getStatusClass(problem.status)}>{formatStatus(problem.status)}</span></td>
                    <td><span className={getDifficultyClass(problem.difficulty_level)}>{formatDifficulty(problem.difficulty_level)}</span></td>
                    <td><span className={getVettingTierClass(problem.vetting_tier)}>{formatVettingTier(problem.vetting_tier)}</span></td>
                    <td>{formatDate(problem.updated_at)}</td>
                    <td>
                      <button 
                        className="action-btn view"
                        onClick={() => handleViewProblem(problem)}
                      >
                        View
                      </button>
                      
                      {problem.status !== 'approved' && (
                        <>
                          <button 
                            className="action-btn approve"
                            onClick={() => handleApproveModal(problem)}
                          >
                            Approve
                          </button>
                          {/* Only show Mark for Review button if not already pending */}
                          {problem.status !== 'pending' && (
                            <button 
                              className="action-btn review"
                              onClick={() => handleRejectModal(problem)}
                            >
                              Mark for Review
                            </button>
                          )}
                        </>
                      )}
                      
                      {problem.status !== 'archived' && (
                        <button 
                          className="action-btn archive"
                          onClick={() => handleArchive(problem.id)}
                        >
                          Archive
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="text-center py-3">
                    No problems found matching the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Custom Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={handleModalClose}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {modalType === 'view' && 'Problem Details'}
                {modalType === 'approve' && 'Approve Problem'}
                {modalType === 'reject' && 'Mark Problem for Review'}
              </h3>
              <button className="close-button" onClick={handleModalClose}>×</button>
            </div>
            
            <div className="modal-body">
              {renderModalContent()}
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={handleModalClose}
                disabled={actionInProgress}
              >
                Close
              </button>
              
              {modalType === 'approve' && (
                <button 
                  className="btn btn-success" 
                  onClick={handleApprove}
                  disabled={actionInProgress}
                >
                  {actionInProgress ? 'Processing...' : 'Approve Problem'}
                </button>
              )}
              
              {modalType === 'reject' && (
                <button 
                  className="btn btn-warning" 
                  onClick={handleReject}
                  disabled={actionInProgress}
                >
                  {actionInProgress ? 'Processing...' : 'Mark for Review'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProblemManagement;