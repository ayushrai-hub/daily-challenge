import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import './admin.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const TagMetadataManagement = () => {
  // State variables
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTag, setSelectedTag] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tag_type: 'concept',
    is_featured: false,
    is_private: false,
    parent_tags: []
  });
  // Track original values for change detection
  const [originalFormData, setOriginalFormData] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [availableTags, setAvailableTags] = useState([]);
  const [message, setMessage] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [filterText, setFilterText] = useState('');
  const [showSuccessAnimation, setShowSuccessAnimation] = useState(false);

  // Fetch all tags on component mount
  useEffect(() => {
    fetchTags();
  }, []);

  // Fetch tags from API
  const fetchTags = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(`${API_BASE_URL}/tags`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setTags(response.data);
      setAvailableTags(response.data);
      setLoading(false);
    } catch (err) {
      setError('Error fetching tags: ' + (err.response?.data?.detail || err.message));
      setLoading(false);
    }
  };

  // Get tag hierarchy
  const fetchTagHierarchy = async (tagId) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(`${API_BASE_URL}/tags/${tagId}/hierarchy`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      return response.data;
    } catch (err) {
      // If 404, the endpoint doesn't exist yet - this is handled gracefully
      if (err.response && err.response.status === 404) {
        console.warn('Tag hierarchy endpoint not implemented yet');
      } else {
        console.error('Error fetching tag hierarchy:', err);
      }
      return { parents: [], children: [] };
    }
  };

  // Select a tag for editing
  const handleSelectTag = async (tag) => {
    // Clear any previous message
    setMessage('');
    setError(null);
    
    setSelectedTag(tag);
    
    // Get tag hierarchy to populate parent tags
    const hierarchy = await fetchTagHierarchy(tag.id);
    
    const newFormData = {
      name: tag.name,
      description: tag.description || '',
      tag_type: tag.tag_type || 'concept',
      is_featured: tag.is_featured || false,
      is_private: tag.is_private || false,
      parent_tags: hierarchy.parents.map(p => p.id)
    };
    
    setFormData(newFormData);
    
    // Store original values for change detection
    setOriginalFormData({
      ...newFormData,
      parent_tags: [...newFormData.parent_tags]
    });
    
    // Reset change tracking
    setHasChanges(false);
    
    setEditMode(true);
  };

  // Check if form data has changed from original values
  const checkForChanges = (currentData, originalData) => {
    if (!originalData) return false;
    
    // Compare basic properties
    if (currentData.name !== originalData.name) return true;
    if (currentData.description !== originalData.description) return true;
    if (currentData.tag_type !== originalData.tag_type) return true;
    if (currentData.is_featured !== originalData.is_featured) return true;
    if (currentData.is_private !== originalData.is_private) return true;
    
    // Compare arrays (parent tags)
    if (currentData.parent_tags.length !== originalData.parent_tags.length) return true;
    
    // Sort arrays to ensure consistent comparison
    const sortedCurrent = [...currentData.parent_tags].sort();
    const sortedOriginal = [...originalData.parent_tags].sort();
    
    for (let i = 0; i < sortedCurrent.length; i++) {
      if (sortedCurrent[i] !== sortedOriginal[i]) return true;
    }
    
    return false;
  };
  
  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    const updatedFormData = {...formData};
    
    if (type === 'checkbox') {
      updatedFormData[name] = checked;
    } else {
      updatedFormData[name] = value;
    }
    
    setFormData(updatedFormData);
    
    // Check if data has changed from original
    const changed = checkForChanges(updatedFormData, originalFormData);
    setHasChanges(changed);
  };

  // Handle parent tag selection
  const handleParentTagChange = (e) => {
    const selectedOptions = Array.from(e.target.selectedOptions, option => option.value);
    
    const updatedFormData = {
      ...formData,
      parent_tags: selectedOptions
    };
    
    setFormData(updatedFormData);
    
    // Check if data has changed from original
    const changed = checkForChanges(updatedFormData, originalFormData);
    setHasChanges(changed);
  };

  // Save tag changes
  const handleSaveTag = async (e) => {
    e.preventDefault();
    
    // If there are no changes, just cancel edit mode
    if (!hasChanges) {
      handleCancelEdit();
      return;
    }
    
    setLoading(true);
    
    try {
      const token = localStorage.getItem('auth_token');
      const tagName = formData.name;
      
      // Prepare data for API
      const tagData = {
        name: formData.name,
        description: formData.description,
        tag_type: formData.tag_type,
        is_featured: formData.is_featured,
        is_private: formData.is_private
      };
      
      // Update tag metadata - this will always be called
      await axios.put(`${API_BASE_URL}/tags/${selectedTag.id}`, tagData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Only attempt to update hierarchy if the backend supports it and we have parent tags
      if (formData.parent_tags && formData.parent_tags.length > 0) {
        try {
          // Update tag hierarchy (parent relationships)
          await axios.put(`${API_BASE_URL}/tags/${selectedTag.id}/hierarchy`, {
            parent_tag_ids: formData.parent_tags
          }, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
        } catch (hierarchyError) {
          console.warn('Hierarchy endpoint not available:', hierarchyError);
          // Don't treat hierarchy update failure as a fatal error
          // Just log a warning and continue with the flow
        }
      }
      
      // Show success message and reset form
      setMessage(`Successfully updated tag: ${tagName}`);
      setShowSuccessAnimation(true);
      setTimeout(() => setShowSuccessAnimation(false), 2000);
      
      // Reset form and state
      resetForm();
      fetchTags(); // Refresh tag list
      
    } catch (err) {
      setError('Error updating tag: ' + (err.response?.data?.detail || err.message));
    }
    
    setLoading(false);
  };
  
  // Reset form to initial state
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      tag_type: 'concept',
      is_featured: false,
      is_private: false,
      parent_tags: []
    });
    setOriginalFormData(null);
    setEditMode(false);
    setSelectedTag(null);
    setHasChanges(false);
  };

  // Cancel editing
  const handleCancelEdit = () => {
    // Clear messages
    setMessage('');
    setError(null);
    
    // Reset form and state
    resetForm();
  };

  // Create new tag
  const handleCreateTag = async (e) => {
    e.preventDefault();
    
    // Validate form
    if (!formData.name.trim()) {
      setError('Tag name is required');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const tagName = formData.name.trim(); // Store for message
      
      // Prepare data for API
      const tagData = {
        name: tagName,
        description: formData.description,
        tag_type: formData.tag_type,
        is_featured: formData.is_featured,
        is_private: formData.is_private
      };
      
      // Create new tag
      const response = await axios.post(`${API_BASE_URL}/tags`, tagData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      const newTagId = response.data.id;
      
      // If parent tags were selected, update hierarchy
      if (formData.parent_tags.length > 0) {
        try {
          await axios.put(`${API_BASE_URL}/tags/${newTagId}/hierarchy`, {
            parent_tag_ids: formData.parent_tags
          }, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
        } catch (hierarchyError) {
          console.warn('Hierarchy endpoint not available for new tag:', hierarchyError);
          // Non-fatal error, continue
        }
      }
      
      // Success feedback
      setMessage(`Successfully created tag: ${tagName}`);
      setShowSuccessAnimation(true);
      setTimeout(() => setShowSuccessAnimation(false), 2000);
      
      // Refresh tag list
      fetchTags(); 
      
      // Reset form completely
      resetForm();
      
    } catch (err) {
      setError('Error creating tag: ' + (err.response?.data?.detail || err.message));
    }
    
    setLoading(false);
  };

  // Handle sorting
  const handleSort = (field) => {
    if (sortBy === field) {
      // Toggle sort order if same field
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field and default to ascending
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  // Apply sorting and filtering
  const sortedAndFilteredTags = [...tags]
    .filter(tag => 
      tag.name.toLowerCase().includes(filterText.toLowerCase()) ||
      (tag.description && tag.description.toLowerCase().includes(filterText.toLowerCase())) ||
      (tag.tag_type && tag.tag_type.toLowerCase().includes(filterText.toLowerCase()))
    )
    .sort((a, b) => {
      let comparison = 0;
      
      if (sortBy === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortBy === 'type') {
        comparison = (a.tag_type || '').localeCompare(b.tag_type || '');
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>Tag Metadata Management</h1>
        <div className="breadcrumbs">
          <Link to="/admin">Admin Dashboard</Link> &gt; Tag Metadata Management
        </div>
      </div>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
      
      {/* Tag List and Form Container */}
      <div className="tag-metadata-container">
        {/* Left Column - Tag List */}
        <div className="tag-list-panel">
          <h2>Tags</h2>
          
          {/* Search and Filter */}
          <div className="tag-search">
            <input
              type="text"
              placeholder="Filter tags..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="filter-input"
            />
          </div>
          
          {/* Tag List */}
          <div className="tag-table-container">
            {loading ? <div className="loading">Loading tags...</div> : (
              <table className="tag-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('name')} className={sortBy === 'name' ? 'sorted-' + sortOrder : ''}>
                      Name {sortBy === 'name' && <span>{sortOrder === 'asc' ? '▲' : '▼'}</span>}
                    </th>
                    <th onClick={() => handleSort('type')} className={sortBy === 'type' ? 'sorted-' + sortOrder : ''}>
                      Type {sortBy === 'type' && <span>{sortOrder === 'asc' ? '▲' : '▼'}</span>}
                    </th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedAndFilteredTags.length > 0 ? (
                    sortedAndFilteredTags.map(tag => (
                      <tr 
                        key={tag.id} 
                        className={selectedTag?.id === tag.id ? 'selected-tag' : ''}
                        onClick={() => handleSelectTag(tag)}
                      >
                        <td>{tag.name}</td>
                        <td>{tag.tag_type || 'concept'}</td>
                        <td>
                          <button 
                            className="btn-edit"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectTag(tag);
                            }}
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3">No tags found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
          
          <div className="tag-count">
            <p>Total: {sortedAndFilteredTags.length} tags</p>
          </div>
        </div>
        
        {/* Right Column - Edit Form or Create Form */}
        <div className="tag-edit-panel">
          <div className="panel-header">
            <h2>{editMode ? 'Edit Tag' : 'Create New Tag'}</h2>
            {editMode && (
              <div className="edit-mode-indicator">Editing mode</div>
            )}
          </div>
          
          {showSuccessAnimation && (
            <div className="success-animation">
              <div className="checkmark">✓</div>
              <div className="pulse"></div>
            </div>
          )}
          
          <form onSubmit={editMode ? handleSaveTag : handleCreateTag}>
            <div className="form-group">
              <label htmlFor="name">Tag Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                placeholder="Enter tag name"
                className={`form-control ${editMode && originalFormData && formData.name !== originalFormData.name ? 'field-changed' : ''}`}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows="3"
                placeholder="Enter tag description"
                className={`form-control ${editMode && originalFormData && formData.description !== originalFormData.description ? 'field-changed' : ''}`}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="tag_type">Tag Type</label>
              <select
                id="tag_type"
                name="tag_type"
                value={formData.tag_type}
                onChange={handleInputChange}
                className={`form-control ${editMode && originalFormData && formData.tag_type !== originalFormData.tag_type ? 'field-changed' : ''}`}
              >
                <option value="concept">Concept</option>
                <option value="technology">Technology</option>
                <option value="language">Language</option>
                <option value="framework">Framework</option>
                <option value="difficulty">Difficulty</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="parent_tags">Parent Tags</label>
              {editMode && formData.parent_tags && formData.parent_tags.length > 0 && (
                <div className="current-parents-indicator">
                  <strong>Current Parents:</strong> 
                  {formData.parent_tags.map(tagId => {
                    const parentTag = availableTags.find(t => t.id === tagId);
                    return parentTag ? parentTag.name : null;
                  }).filter(Boolean).join(', ')}
                </div>
              )}
              <select
                id="parent_tags"
                name="parent_tags"
                multiple
                value={formData.parent_tags}
                onChange={handleParentTagChange}
                className={`form-control ${editMode && originalFormData && 
                  // Only check if parent_tags array has changed, not the entire form
                  JSON.stringify(formData.parent_tags) !== JSON.stringify(originalFormData.parent_tags) ? 'field-changed' : ''}`}
                size="6"
              >
                {availableTags
                  .filter(tag => !selectedTag || tag.id !== selectedTag.id)
                  .map(tag => {
                    const isCurrentParent = editMode && 
                      formData.parent_tags && 
                      formData.parent_tags.includes(tag.id);
                    return (
                      <option 
                        key={tag.id} 
                        value={tag.id} 
                        className={isCurrentParent ? 'current-parent-option' : ''}
                      >
                        {tag.name} {isCurrentParent ? '(Current Parent)' : ''}
                      </option>
                    );
                  })
                }
              </select>
              <small className="form-text">Hold Ctrl/Cmd to select multiple tags</small>
            </div>
            
            <div className="form-group checkbox-group">
              <div className="checkbox-item">
                <input
                  type="checkbox"
                  id="is_featured"
                  name="is_featured"
                  checked={formData.is_featured}
                  onChange={handleInputChange}
                  className={editMode && originalFormData && formData.is_featured !== originalFormData.is_featured ? 'field-changed' : ''}
                />
                <label htmlFor="is_featured"
                  className={editMode && originalFormData && formData.is_featured !== originalFormData.is_featured ? 'field-changed' : ''}
                >Featured Tag</label>
              </div>
              
              <div className="checkbox-item">
                <input
                  type="checkbox"
                  id="is_private"
                  name="is_private"
                  checked={formData.is_private}
                  onChange={handleInputChange}
                  className={editMode && originalFormData && formData.is_private !== originalFormData.is_private ? 'field-changed' : ''}
                />
                <label htmlFor="is_private"
                  className={editMode && originalFormData && formData.is_private !== originalFormData.is_private ? 'field-changed' : ''}
                >Private Tag</label>
              </div>
            </div>
            
            <div className="form-buttons">
              {editMode ? (
                <>
                  <button 
                    type="submit" 
                    className={`btn-save ${!hasChanges ? 'btn-disabled' : ''}`} 
                    disabled={loading || !hasChanges}
                  >
                    {loading ? 'Saving...' : hasChanges ? 'Save Changes' : 'No Changes'}
                  </button>
                  <button 
                    type="button" 
                    className="btn-cancel"
                    onClick={handleCancelEdit}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button 
                  type="submit" 
                  className="btn-create" 
                  disabled={loading || !formData.name.trim()}
                >
                  {loading ? 'Creating...' : 'Create Tag'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default TagMetadataManagement;
