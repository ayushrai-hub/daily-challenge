import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { tagApi } from '../lib/api';

function Tags() {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newTag, setNewTag] = useState({ name: '', description: '', tag_type: 'TOPIC', is_featured: false });
  const [createError, setCreateError] = useState('');
  const [searchName, setSearchName] = useState('');
  const [filterType, setFilterType] = useState('');

  // Fetch all tags
  useEffect(() => {
    fetchTags();
  }, []);

  // Fetch tags with optional filters
  const fetchTags = async (filters = {}) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await tagApi.getTags(filters);
      setTags(response.data);
    } catch (err) {
      console.error('Error fetching tags:', err);
      setError('Failed to load tags. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle tag creation
  const handleCreateTag = async (e) => {
    e.preventDefault();
    setCreateError('');
    
    try {
      const response = await tagApi.createTag(newTag);
      setTags([...tags, response.data]);
      setNewTag({ name: '', description: '', tag_type: 'TOPIC', is_featured: false });
    } catch (err) {
      console.error('Error creating tag:', err);
      setCreateError(err.response?.data?.detail || 'Failed to create tag. Please try again.');
    }
  };

  // Handle input change for new tag form
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setNewTag({
      ...newTag,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  // Handle search and filter
  const handleSearch = (e) => {
    e.preventDefault();
    const filters = {};
    if (searchName) filters.name = searchName;
    if (filterType) filters.tag_type = filterType;
    fetchTags(filters);
  };

  // Handle tag deletion
  const handleDeleteTag = async (id) => {
    if (!window.confirm('Are you sure you want to delete this tag?')) return;
    
    try {
      await tagApi.deleteTag(id);
      setTags(tags.filter(tag => tag.id !== id));
    } catch (err) {
      console.error('Error deleting tag:', err);
      alert('Failed to delete tag. Please try again.');
    }
  };

  return (
    <div className="container">
      <h1>Tags</h1>
      
      {/* Search and Filter Form */}
      <div className="search-filter-bar">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-inputs">
            <input
              type="text"
              placeholder="Search tags..."
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
            />
            
            <select 
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="TOPIC">Topic</option>
              <option value="DIFFICULTY">Difficulty</option>
              <option value="SOURCE">Source</option>
              <option value="LANGUAGE">Language</option>
            </select>
            
            <button type="submit">Search</button>
          </div>
        </form>
      </div>
      
      {/* Error Message */}
      {error && <div className="error">{error}</div>}
      
      {/* Tags List */}
      {loading ? (
        <p>Loading tags...</p>
      ) : (
        <div className="tags-container">
          {tags.length === 0 ? (
            <p>No tags found.</p>
          ) : (
            <div className="tags-grid">
              {tags.map(tag => (
                <div className="tag-card" key={tag.id}>
                  <h3>
                    <Link to={`/tags/${tag.id}`}>{tag.name}</Link>
                  </h3>
                  <p>{tag.description || 'No description provided.'}</p>
                  <div className="tag-meta">
                    <span className={`tag-type ${tag.tag_type.toLowerCase()}`}>
                      {tag.tag_type}
                    </span>
                    {tag.is_featured && <span className="featured">Featured</span>}
                    {tag.children && tag.children.length > 0 && (
                      <span className="children-count">{tag.children.length} subtags</span>
                    )}
                  </div>
                  <div className="tag-actions">
                    <Link to={`/tags/${tag.id}`} className="btn-small">Edit</Link>
                    <button 
                      onClick={() => handleDeleteTag(tag.id)} 
                      className="btn-small btn-danger"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Create New Tag Form */}
      <div className="create-tag-section">
        <h2>Create New Tag</h2>
        
        {createError && <div className="error">{createError}</div>}
        
        <form onSubmit={handleCreateTag} className="create-form">
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={newTag.name}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              name="description"
              value={newTag.description}
              onChange={handleInputChange}
              rows="3"
            ></textarea>
          </div>
          
          <div className="form-group">
            <label htmlFor="tag_type">Type</label>
            <select
              id="tag_type"
              name="tag_type"
              value={newTag.tag_type}
              onChange={handleInputChange}
              required
            >
              <option value="TOPIC">Topic</option>
              <option value="DIFFICULTY">Difficulty</option>
              <option value="SOURCE">Source</option>
              <option value="LANGUAGE">Language</option>
            </select>
          </div>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="is_featured"
              name="is_featured"
              checked={newTag.is_featured}
              onChange={handleInputChange}
            />
            <label htmlFor="is_featured">Featured Tag</label>
          </div>
          
          <button type="submit">Create Tag</button>
        </form>
      </div>
    </div>
  );
}

export default Tags;
