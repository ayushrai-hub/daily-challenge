import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tagManagementApi } from '../../lib/adminApi';
import './admin.css';

const TagNormalizationDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  // State
  const [normalization, setNormalization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [editMode, setEditMode] = useState(false);
  
  // Edit form state
  const [formData, setFormData] = useState({
    normalized_name: '',
    description: '',
    admin_notes: '',
  });
  
  // Similar tags for mapping
  const [similarTags, setSimilarTags] = useState([]);
  const [loadingSimilarTags, setLoadingSimilarTags] = useState(false);
  const [selectedTagId, setSelectedTagId] = useState('');
  const [hasHighSimilarityTag, setHasHighSimilarityTag] = useState(false);
  
  // Approval form state
  const [showApprovalForm, setShowApprovalForm] = useState(false);
  const [approvalData, setApprovalData] = useState({
    tag_name: '',
    description: '',
    tag_type: 'concept',
    parent_tag_ids: [],
    admin_notes: '',
    existing_tag_id: ''
  });
  
  // Processing state
  const [processing, setProcessing] = useState(false);
  
  // Fetch tag normalization details
  const fetchNormalization = async () => {
    setLoading(true);
    try {
      const response = await tagManagementApi.getNormalizationById(id);
      
      const data = response.data;
      setNormalization(data);
      
      // Initialize form data with current values
      setFormData({
        normalized_name: data.normalized_name,
        description: data.description || '',
        admin_notes: data.admin_notes || '',
      });
      
      // Initialize approval data
      setApprovalData(prevData => ({
        ...prevData,
        tag_name: data.normalized_name,
        description: data.description || '',
      }));
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching tag normalization:', err);
      setError('Failed to load tag normalization details. Please try again later.');
      setLoading(false);
    }
  };
  
  // Fetch similar tags to help with mapping
  const fetchSimilarTags = async () => {
    if (!normalization) return;
    
    setLoadingSimilarTags(true);
    try {
      const response = await tagManagementApi.findSimilarTags(normalization.normalized_name);
      
      // Check if there are any high similarity tags (above 0.8)
      const highSimilarityExists = response.data.some(tag => tag.similarity > 0.8);
      setHasHighSimilarityTag(highSimilarityExists);
      
      // Sort by similarity (highest first)
      const sortedTags = [...response.data].sort((a, b) => b.similarity - a.similarity);
      setSimilarTags(sortedTags);
      
      // Auto-select the highest similarity tag if it's very similar (above 0.9)
      if (sortedTags.length > 0 && sortedTags[0].similarity > 0.9) {
        setSelectedTagId(sortedTags[0].id);
        setApprovalData(prevData => ({
          ...prevData,
          existing_tag_id: sortedTags[0].id,
          create_new_tag: false
        }));
      }
      
      setLoadingSimilarTags(false);
    } catch (err) {
      console.error('Error fetching similar tags:', err);
      setLoadingSimilarTags(false);
    }
  };
  
  // Load data on component mount
  useEffect(() => {
    fetchNormalization();
    
    // Check URL for edit parameter
    const searchParams = new URLSearchParams(window.location.search);
    const shouldEdit = searchParams.get('edit') === 'true';
    
    if (shouldEdit) {
      setEditMode(true);
      setShowApprovalForm(true);
    }
  }, [id]);
  
  // Load similar tags when normalization data is available
  useEffect(() => {
    if (normalization) {
      fetchSimilarTags();
    }
  }, [normalization]);
  
  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevData => ({
      ...prevData,
      [name]: value
    }));
  };
  
  // Handle approval form input changes
  const handleApprovalInputChange = (e) => {
    const { name, value } = e.target;
    setApprovalData(prevData => ({
      ...prevData,
      [name]: value
    }));
  };
  
  // Handle existing tag selection
  const handleExistingTagSelect = (e) => {
    const tagId = e.target.value;
    setSelectedTagId(tagId);
    
    if (tagId) {
      // Find the selected tag from similarTags
      const selectedTag = similarTags.find(tag => tag.id === tagId);
      if (selectedTag) {
        setApprovalData(prevData => ({
          ...prevData,
          existing_tag_id: tagId,
          // Clear the new tag fields since we're using existing
          tag_name: '',
          description: '',
          tag_type: 'concept',
          parent_tag_ids: []
        }));
      }
    } else {
      // Reset to creating a new tag
      setApprovalData(prevData => ({
        ...prevData,
        existing_tag_id: '',
        tag_name: normalization.normalized_name,
        description: normalization.description || ''
      }));
    }
  };
  
  // Save edited normalization
  const saveNormalization = async () => {
    try {
      const response = await tagManagementApi.updateNormalization(id, formData);
      
      // Update local state
      setNormalization(response.data);
      setEditMode(false);
      setMessage('Normalization updated successfully');
    } catch (err) {
      console.error('Error saving tag normalization:', err);
      setError('Failed to save changes. Please try again later.');
    }
  };
  
  // Approve normalization
  const approveNormalization = async () => {
    setProcessing(true);
    try {
      // Prepare data - either link to existing or create new
      const approvalParams = approvalData.existing_tag_id ?
        { existing_tag_id: approvalData.existing_tag_id, admin_notes: approvalData.admin_notes } :
        approvalData;
      
      await tagManagementApi.approveNormalization(id, approvalParams);
      
      // If we're reapproving, provide a specific message
      if (normalization.review_status === 'approved') {
        setMessage('Tag successfully reapproved! Associated with relevant problems.');
      } else {
        setMessage('Tag normalization approved successfully!');
      }
      
      setProcessing(false);
      
      // Refresh data
      fetchNormalization();
      setShowApprovalForm(false);
    } catch (err) {
      console.error('Error approving tag normalization:', err);
      setError('Failed to approve tag normalization. Please try again.');
      setProcessing(false);
    }
  };
  
  // Reject normalization
  const rejectNormalization = async () => {
    try {
      await tagManagementApi.rejectNormalization(id, approvalData.admin_notes || 'Rejected by admin');
      
      // Set success message
      setMessage('Tag normalization rejected successfully');
      
      // Navigate back to list after successful rejection
      navigate('/admin/tag-normalizations');
    } catch (err) {
      console.error('Error rejecting tag normalization:', err);
      setError('Failed to reject tag normalization. Please try again later.');
    }
  };
  
  // Confirmation dialog for rejection
  const confirmReject = () => {
    if (window.confirm('Are you sure you want to reject this tag normalization?')) {
      rejectNormalization();
    }
  };
  
  if (loading) {
    return <div className="loading">Loading tag normalization details...</div>;
  }
  
  if (error) {
    return <div className="error">{error}</div>;
  }
  
  if (!normalization) {
    return <div className="not-found">Tag normalization not found</div>;
  }
  
  return (
    <div className="tag-normalization-detail">
      <div className="header-actions">
        <button className="btn btn-secondary" onClick={() => navigate('/admin/tag-normalizations')}>
          Back to List
        </button>
        <div className="action-buttons">
          {normalization.review_status === 'pending' && !showApprovalForm && (
            <>
              <button 
                className="btn btn-success"
                onClick={() => setShowApprovalForm(true)}
                disabled={processing}
              >
                Approve Tag
              </button>
              <button 
                className="btn btn-danger"
                onClick={confirmReject}
                disabled={processing}
              >
                Reject Tag
              </button>
            </>
          )}
          {normalization.review_status === 'approved' && !showApprovalForm && !editMode && (
            <button 
              className="btn btn-primary"
              onClick={() => setShowApprovalForm(true)}
              disabled={processing}
            >
              Edit & Reapprove Tag
            </button>
          )}
          {normalization.review_status === 'pending' && !editMode && !showApprovalForm && (
            <button 
              className="btn btn-secondary" 
              onClick={() => setEditMode(true)}
              disabled={processing}
            >
              Edit Details
            </button>
          )}
          {editMode && (
            <>
              <button 
                className="btn btn-primary" 
                onClick={saveNormalization}
                disabled={processing}
              >
                Save Changes
              </button>
              <button 
                className="btn btn-secondary" 
                onClick={() => setEditMode(false)}
                disabled={processing}
              >
                Cancel
              </button>
            </>
          )}
          {showApprovalForm && (
            <>
              <button 
                className="btn btn-primary" 
                onClick={approveNormalization}
                disabled={processing}
              >
                Confirm Approval
              </button>
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowApprovalForm(false)}
                disabled={processing}
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>
      
      <h1>
        Tag Normalization Details
        <span className={`status-badge status-${normalization.review_status}`}>
          {normalization.review_status}
        </span>
      </h1>
      
      <div className="detail-section">
        <h2>Basic Information</h2>
        <div className="detail-grid">
          <div className="detail-item">
            <label>Original Name:</label>
            <div className="detail-value">{normalization.original_name}</div>
          </div>
          
          <div className="detail-item">
            <label>Normalized Name:</label>
            {editMode ? (
              <input 
                type="text" 
                name="normalized_name" 
                value={formData.normalized_name} 
                onChange={handleInputChange} 
              />
            ) : (
              <div className="detail-value">{normalization.normalized_name}</div>
            )}
          </div>
          
          <div className="detail-item">
            <label>Source:</label>
            <div className="detail-value">{normalization.source}</div>
          </div>
          
          <div className="detail-item">
            <label>Confidence Score:</label>
            <div className="detail-value">
              {normalization.confidence_score ? normalization.confidence_score.toFixed(2) : 'N/A'}
            </div>
          </div>
          
          <div className="detail-item">
            <label>Created At:</label>
            <div className="detail-value">
              {new Date(normalization.created_at).toLocaleString()}
            </div>
          </div>
          
          <div className="detail-item">
            <label>Status:</label>
            <div className="detail-value">{normalization.review_status}</div>
          </div>
        </div>
      </div>
      
      <div className="detail-section">
        <h2>Description</h2>
        {editMode ? (
          <textarea 
            name="description" 
            value={formData.description} 
            onChange={handleInputChange}
            rows={5}
          />
        ) : (
          <div className="description">
            {normalization.description || 'No description available'}
          </div>
        )}
      </div>
      
      <div className="detail-section">
        <h2>Admin Notes</h2>
        {editMode ? (
          <textarea 
            name="admin_notes" 
            value={formData.admin_notes} 
            onChange={handleInputChange}
            rows={5}
          />
        ) : (
          <div className="admin-notes">
            {normalization.admin_notes || 'No admin notes available'}
          </div>
        )}
      </div>
      
      {showApprovalForm && (
        <div className="approval-form">
          <h2>Approve Tag</h2>
          
          <div className="form-tabs">
            <button 
              className={!selectedTagId ? 'active' : ''} 
              onClick={() => handleExistingTagSelect({target: {value: ''}})}
            >
              Create New Tag
            </button>
            <button 
              className={selectedTagId ? 'active' : ''} 
              onClick={() => setSelectedTagId(similarTags.length > 0 ? similarTags[0].id : '')}
            >
              Map to Existing Tag
            </button>
          </div>
          
          {!selectedTagId ? (
            // Create new tag form
            <div className="create-tag-form">
              <div className="form-group">
                <label>Tag Name:</label>
                <input 
                  type="text" 
                  name="tag_name" 
                  value={approvalData.tag_name} 
                  onChange={handleApprovalInputChange} 
                />
              </div>
              
              <div className="form-group">
                <label>Description:</label>
                <textarea 
                  name="description" 
                  value={approvalData.description} 
                  onChange={handleApprovalInputChange}
                  rows={4}
                />
              </div>
              
              <div className="form-group">
                <label>Tag Type:</label>
                <select 
                  name="tag_type" 
                  value={approvalData.tag_type} 
                  onChange={handleApprovalInputChange}
                >
                  <option value="language">Language</option>
                  <option value="framework">Framework</option>
                  <option value="concept">Concept</option>
                  <option value="domain">Domain</option>
                  <option value="skill_level">Skill Level</option>
                  <option value="tool">Tool</option>
                  <option value="topic">Topic</option>
                </select>
              </div>
            </div>
          ) : (
            // Map to existing tag form
            <div className="map-tag-form">
              {hasHighSimilarityTag && (
                <div className="similar-tag-warning">
                  <div className="warning-icon">⚠️</div>
                  <div className="warning-text">
                    <strong>Similar tags detected!</strong> 
                    <p>To prevent duplicate tags, please consider using an existing tag from the list below.</p>
                  </div>
                </div>
              )}
              
              <div className="form-group">
                <label>Select Existing Tag:</label>
                <select 
                  value={selectedTagId} 
                  onChange={handleExistingTagSelect}
                  className={hasHighSimilarityTag ? 'highlight-select' : ''}
                >
                  <option value="">-- Select Tag --</option>
                  {similarTags.map(tag => {
                    // Determine tag similarity level for styling
                    let similarityClass = '';
                    if (tag.match_type === 'exact') {
                      similarityClass = 'exact-match';
                    } else if (tag.similarity > 0.9) {
                      similarityClass = 'very-high-similarity';
                    } else if (tag.similarity > 0.8) {
                      similarityClass = 'high-similarity';
                    } else if (tag.similarity > 0.6) {
                      similarityClass = 'medium-similarity';
                    }
                    
                    return (
                      <option key={tag.id} value={tag.id} className={similarityClass}>
                        {tag.name} {tag.match_type === 'exact' ? '(Exact Match)' : 
                          tag.similarity > 0.9 ? '(Very Similar)' :
                          tag.similarity > 0.8 ? '(Similar)' :
                          tag.similarity > 0.6 ? '(Somewhat Similar)' :
                          '(Low Similarity)'}
                      </option>
                    );
                  })}
                </select>
              </div>
              
              {loadingSimilarTags ? (
                <div className="loading">Loading similar tags...</div>
              ) : similarTags.length === 0 ? (
                <div className="no-similar-tags">No similar tags found</div>
              ) : (
                <div className="similar-tags-container">
                  <h4>Similar Tags:</h4>
                  <div className="similar-tags-list">
                    {similarTags.slice(0, 5).map(tag => {
                      // Color coding based on similarity
                      const getSimilarityColor = (similarity) => {
                        if (similarity > 0.9) return '#e74c3c'; // Very high - red
                        if (similarity > 0.8) return '#e67e22'; // High - orange
                        if (similarity > 0.6) return '#f1c40f'; // Medium - yellow
                        return '#3498db'; // Low - blue
                      };
                      
                      const isSelected = tag.id === selectedTagId;
                      
                      return (
                        <div 
                          key={tag.id} 
                          className={`similar-tag-card ${isSelected ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedTagId(tag.id);
                            handleExistingTagSelect({ target: { value: tag.id } });
                          }}
                        >
                          <div className="tag-name">{tag.name}</div>
                          <div className="tag-description">{tag.description || 'No description'}</div>
                          <div className="tag-similarity" style={{ 
                            backgroundColor: getSimilarityColor(tag.similarity),
                            padding: '2px 6px',
                            borderRadius: '4px',
                            display: 'inline-block',
                            color: '#fff',
                            fontWeight: 'bold'
                          }}>
                            {tag.match_type === 'exact' ? 'Exact Match' : 
                             `Similarity: ${(tag.similarity * 100).toFixed(0)}%`}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <div className="form-group">
            <label>Admin Notes:</label>
            <textarea 
              name="admin_notes" 
              value={approvalData.admin_notes} 
              onChange={handleApprovalInputChange}
              placeholder="Add notes about this approval (optional)"
              rows={4}
            />
          </div>
        </div>
      )}
      
      {normalization.approved_tag && (
        <div className="detail-section">
          <h2>Approved Tag Details</h2>
          <div className="approved-tag">
            <div className="tag-card">
              <h3>{normalization.approved_tag.name}</h3>
              <p>{normalization.approved_tag.description || 'No description'}</p>
              <div className="tag-id">ID: {normalization.approved_tag.id}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TagNormalizationDetail;
