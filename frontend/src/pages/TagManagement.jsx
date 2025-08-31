import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { tagApi } from '../lib/api';

function TagManagement() {
  const [allTags, setAllTags] = useState([]);
  const [userTags, setUserTags] = useState([]);
  const [userTagIds, setUserTagIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  
  // Fetch tags data
  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      try {
        // First get all available tags
        const tagsResponse = await tagApi.getTags();
        if (isMounted) {
          console.log('All tags fetched:', tagsResponse.data);
          const tags = tagsResponse.data || [];
          setAllTags(tags);
          
          // Attempt to get user's tags, but handle error gracefully
          try {
            const userTagsResponse = await tagApi.getUserTags();
            if (isMounted) {
              console.log('User tags fetched:', userTagsResponse.data);
              setUserTags(userTagsResponse.data || []);
              setUserTagIds((userTagsResponse.data || []).map(tag => tag.id));
            }
          } catch (userTagError) {
            console.error('Error fetching user tags:', userTagError);
            if (isMounted) {
              // Don't show error to user, just use empty tag list
              setUserTags([]);
              setUserTagIds([]);
              console.log('Using empty user tags list due to API error');
            }
          }
        }
        
        if (isMounted) {
          setError('');
        }
      } catch (err) {
        console.error('Error fetching tags:', err);
        if (isMounted) {
          setError(`Failed to load tags: ${err.message}`);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchData();
    
    // Cleanup function to prevent state updates if component unmounts
    return () => {
      isMounted = false;
    };
  }, []);

  // Check if a tag is in user's selected tags
  const isTagSelected = (tagId) => {
    return userTagIds.includes(tagId);
  };
  
  // Handle tag selection
  const handleTagSelection = async (tagId, isSelected) => {
    // Prevent multiple simultaneous operations
    if (isUpdating) return;
    
    setIsUpdating(true);
    
    try {
      // Update local state immediately for better UX
      let newTagIds;
      
      if (isSelected) {
        // Remove tag locally
        newTagIds = userTagIds.filter(id => id !== tagId);
        // Also update the userTags array for display
        setUserTags(prevTags => prevTags.filter(tag => tag.id !== tagId));
      } else {
        // Add tag locally
        newTagIds = [...userTagIds, tagId];
        // Also add to userTags array for display
        const tagToAdd = allTags.find(tag => tag.id === tagId);
        if (tagToAdd) {
          setUserTags(prevTags => [...prevTags, tagToAdd]);
        }
      }
      
      // Update local state
      setUserTagIds(newTagIds);
      
      console.log(`${isSelected ? 'Removing' : 'Adding'} tag ID ${tagId}`);
      console.log('New tag IDs:', newTagIds);
      
      // Update tags on server
      await tagApi.updateUserTags(newTagIds);
      
      setActionMessage(`Tag ${isSelected ? 'removed' : 'added'} successfully`);
      setTimeout(() => setActionMessage(''), 3000);
    } catch (err) {
      console.error(`Error ${isSelected ? 'removing' : 'adding'} tag:`, err);
      let errorMsg = `Failed to ${isSelected ? 'remove' : 'add'} tag`;
      
      if (err.response) {
        console.log('Error response:', err.response);
        errorMsg += `: ${err.response.status} ${err.response.statusText}`;
        if (err.response.data && err.response.data.detail) {
          errorMsg += ` - ${err.response.data.detail}`;
        }
      } else {
        errorMsg += `: ${err.message}`;
      }
      
      setError(errorMsg);
      
      // Revert local changes on error
      try {
        const userTagsResponse = await tagApi.getUserTags();
        setUserTags(userTagsResponse.data || []);
        setUserTagIds((userTagsResponse.data || []).map(tag => tag.id));
      } catch (fetchErr) {
        // If we can't fetch the current state, we'll just leave the local state as is
        console.error('Error fetching user tags after failed update:', fetchErr);
      }
      
      setTimeout(() => setError(''), 5000);
    } finally {
      setIsUpdating(false);
    }
  };

  // Filter tags based on search query and type
  const filteredTags = allTags.filter(tag => {
    const matchesSearch = searchQuery 
      ? tag.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tag.description && tag.description.toLowerCase().includes(searchQuery.toLowerCase()))
      : true;
    
    const matchesType = filterType 
      ? tag.tag_type === filterType 
      : true;
    
    return matchesSearch && matchesType;
  });

  // Get unique tag types for the filter dropdown
  const uniqueTagTypes = [...new Set(allTags.map(tag => tag.tag_type))].filter(Boolean);

  return (
    <div className="container">
      <h1>Tag Management</h1>
      <p>Manage your tag preferences to customize your daily challenges</p>
      
      {loading && <div style={{padding: '10px', backgroundColor: '#f0f8ff', borderRadius: '5px', marginBottom: '15px'}}>Loading...</div>}
      {error && <div style={{color: 'red', padding: '10px', backgroundColor: '#ffeeee', borderRadius: '5px', marginBottom: '15px'}}>{error}</div>}
      {actionMessage && <div style={{color: 'green', padding: '10px', backgroundColor: '#eeffee', borderRadius: '5px', marginBottom: '15px'}}>{actionMessage}</div>}
      
      <div style={{marginBottom: '20px'}}>
        <h2>Your Selected Tags ({userTags.length})</h2>
        <div style={{display: 'flex', flexWrap: 'wrap', gap: '10px'}}>
          {userTags.length > 0 ? (
            userTags.map(tag => (
              <div 
                key={tag.id} 
                style={{
                  border: '1px solid #3498db', 
                  padding: '5px 10px', 
                  borderRadius: '15px',
                  backgroundColor: '#e3f2fd',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}
              >
                <span>{tag.name}</span>
                <button 
                  onClick={() => handleTagSelection(tag.id, true)}
                  disabled={isUpdating}
                  style={{
                    border: 'none',
                    background: 'none',
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    fontSize: '16px',
                    color: '#e74c3c',
                    opacity: isUpdating ? 0.5 : 1
                  }}
                >
                  ×
                </button>
              </div>
            ))
          ) : (
            <p>You haven't selected any tags yet.</p>
          )}
        </div>
      </div>
      
      <div>
        <h2>Available Tags ({filteredTags.length} of {allTags.length})</h2>
        
        {/* Filtering controls */}
        <div style={{
          display: 'flex', 
          justifyContent: 'space-between',
          marginBottom: '20px',
          padding: '15px',
          backgroundColor: '#f8f9fa',
          borderRadius: '5px'
        }}>
          <input
            type="text"
            placeholder="Search tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: '1px solid #ced4da',
              flexGrow: 1,
              marginRight: '10px'
            }}
          />
          
          <select 
            value={filterType} 
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: '1px solid #ced4da',
              backgroundColor: 'white'
            }}
          >
            <option value="">All Types</option>
            {uniqueTagTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
        
        <div style={{display: 'flex', flexWrap: 'wrap', gap: '15px'}}>
          {filteredTags.map(tag => {
            const selected = isTagSelected(tag.id);
            return (
              <div 
                key={tag.id} 
                style={{
                  border: '1px solid #ccc', 
                  padding: '15px', 
                  borderRadius: '5px',
                  backgroundColor: selected ? '#f0f8ff' : 'white',
                  minWidth: '200px',
                  flex: '1 0 200px'
                }}
              >
                <h3>{tag.name}</h3>
                <p style={{color: '#666'}}>{tag.description || 'No description'}</p>
                {tag.tag_type && (
                  <span style={{
                    display: 'inline-block',
                    backgroundColor: '#eee',
                    padding: '3px 8px',
                    borderRadius: '10px',
                    fontSize: '12px',
                    marginTop: '10px'
                  }}>
                    {tag.tag_type}
                  </span>
                )}
                <div style={{marginTop: '15px'}}>
                  <button 
                    onClick={() => handleTagSelection(tag.id, selected)}
                    disabled={isUpdating}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: selected ? '#e74c3c' : '#2ecc71',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: isUpdating ? 'not-allowed' : 'pointer',
                      opacity: isUpdating ? 0.5 : 1
                    }}
                  >
                    {selected ? 'Remove' : 'Add'}
                  </button>
                </div>
              </div>
            );
          })}
          
          {!loading && filteredTags.length === 0 && (
            <div style={{
              padding: '20px',
              textAlign: 'center',
              width: '100%',
              backgroundColor: '#f8f9fa',
              borderRadius: '5px'
            }}>
              <p>No tags match your search criteria.</p>
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    marginTop: '10px'
                  }}
                >
                  Clear Search
                </button>
              )}
            </div>
          )}
        </div>
      </div>
      
      <div style={{marginTop: '30px'}}>
        <Link 
          to="/dashboard" 
          style={{
            padding: '8px 15px',
            backgroundColor: '#3498db',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '5px'
          }}
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default TagManagement;
