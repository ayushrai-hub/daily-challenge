import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tagApi } from '../lib/api';

function TagDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tag, setTag] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tag_type: '',
    is_featured: false
  });

  // Fetch tag details
  useEffect(() => {
    async function fetchTag() {
      try {
        const response = await tagApi.getTagById(id);
        setTag(response.data);
        setFormData({
          name: response.data.name,
          description: response.data.description || '',
          tag_type: response.data.tag_type,
          is_featured: response.data.is_featured,
          parent_tag_id: response.data.parent_tag_id || null
        });
      } catch (err) {
        console.error('Error fetching tag:', err);
        setError('Failed to load tag details. Please try again later.');
      } finally {
        setLoading(false);
      }
    }

    fetchTag();
  }, [id]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const response = await tagApi.updateTag(id, formData);
      setTag(response.data);
      setEditMode(false);
    } catch (err) {
      console.error('Error updating tag:', err);
      setError(err.response?.data?.detail || 'Failed to update tag. Please try again.');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this tag?')) return;
    
    try {
      await tagApi.deleteTag(id);
      navigate('/tags');
    } catch (err) {
      console.error('Error deleting tag:', err);
      setError('Failed to delete tag. Please try again.');
    }
  };

  if (loading) {
    return <div className="loading">Loading tag details...</div>;
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">{error}</div>
        <button onClick={() => navigate('/tags')}>Back to Tags</button>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="tag-detail-header">
        <h1>{tag.name}</h1>
        <div className="tag-actions">
          {!editMode && (
            <>
              <button onClick={() => setEditMode(true)}>Edit</button>
              <button className="btn-danger" onClick={handleDelete}>Delete</button>
            </>
          )}
        </div>
      </div>

      {editMode ? (
        <div className="edit-tag-form">
          <h2>Edit Tag</h2>
          {error && <div className="error">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
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
              ></textarea>
            </div>

            <div className="form-group">
              <label htmlFor="tag_type">Type</label>
              <select
                id="tag_type"
                name="tag_type"
                value={formData.tag_type}
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
                checked={formData.is_featured}
                onChange={handleInputChange}
              />
              <label htmlFor="is_featured">Featured Tag</label>
            </div>

            <div className="form-buttons">
              <button type="submit">Save Changes</button>
              <button 
                type="button" 
                onClick={() => setEditMode(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="tag-detail-content">
          <div className="tag-meta">
            <span className={`tag-type ${tag.tag_type.toLowerCase()}`}>
              {tag.tag_type}
            </span>
            {tag.is_featured && <span className="featured">Featured</span>}
          </div>

          <div className="tag-description">
            <h3>Description</h3>
            <p>{tag.description || 'No description provided.'}</p>
          </div>

          {tag.parent_tag_id && (
            <div className="tag-parent">
              <h3>Parent Tag</h3>
              <p>ID: {tag.parent_tag_id}</p>
            </div>
          )}

          {tag.children && tag.children.length > 0 && (
            <div className="tag-children">
              <h3>Child Tags</h3>
              <ul>
                {tag.children.map(childId => (
                  <li key={childId}>Tag ID: {childId}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <button onClick={() => navigate('/tags')} className="btn-back">
        Back to Tags
      </button>
    </div>
  );
}

export default TagDetail;
