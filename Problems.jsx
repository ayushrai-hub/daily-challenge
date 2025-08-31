import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// Direct API URL to avoid process.env reference error
const API_BASE_URL = '/api'; // This will use the relative path to the current host

function Problems() {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [categoryExpanded, setCategoryExpanded] = useState({
    'Languages': true,
    'Algorithms': true,
    'Data Structures': true,
    'Code Quality': true
  });
  const [tagCategories, setTagCategories] = useState({});
  const [subscribedTags, setSubscribedTags] = useState([]);
  const [showOnlySubscribed, setShowOnlySubscribed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchProblems();
    fetchTagHierarchy();
    fetchUserSubscribedTags();
  }, []);
  
  // Fetch tags the user has subscribed to
  const fetchUserSubscribedTags = async () => {
    try {
      const response = await fetch('/api/subscriptions/me/tags', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        console.error(`Subscriptions API error: ${response.status} ${response.statusText}`);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('User subscribed tags:', data);
      
      if (data && Array.isArray(data)) {
        setSubscribedTags(data.map(tag => tag.name));
      }
    } catch (err) {
      console.error('Error fetching user tags:', err);
      setSubscribedTags([]);
    }
  };

  const fetchProblems = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Using a direct fetch call with include_tags parameter
      const response = await fetch('/api/problems?include_tags=true', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Check if response was successful
      if (!response.ok) {
        console.error(`Problems API error: ${response.status} ${response.statusText}`);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      // Parse the JSON response
      const data = await response.json();
      
      // Add detailed logging to help debug issues
      console.log('Problems API response:', data);
      
      if (data && Array.isArray(data)) {
        // Normalize the problem data to ensure tag information is consistent
        const normalizedProblems = data.map(problem => {
          // Make sure tags is always an array, even if it's missing or null
          return {
            ...problem,
            tags: Array.isArray(problem.tags) ? problem.tags : []
          };
        });
        
        setProblems(normalizedProblems);
        setError('');
      } else {
        // Handle unexpected data format
        console.error('Problems API returned unexpected format:', data);
        setProblems([]);
        setError('Received unexpected data format from server. Please contact support.');
      }
    } catch (err) {
      console.error('Error fetching problems:', err);
      // Log specific error details to help debug
      if (err.response) {
        console.error('Response error data:', err.response.data);
        console.error('Response error status:', err.response.status);
      }
      setProblems([]);
      setError('Failed to load problems. The server may be down or you may not have access to view problems.');
    } finally {
      setLoading(false);
    }
  };

  const fetchTagHierarchy = async () => {
    try {
      // Use the regular tags endpoint with include_parent parameter 
      // instead of the problematic hierarchy endpoint that returns 422 error
      const response = await fetch('/api/tags?include_parent=true', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        console.error(`Tags API error: ${response.status} ${response.statusText}`);
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      // Parse the JSON response
      const data = await response.json();
      console.log('Tag data response:', data);
      
      // Process tags to organize by category
      if (data && Array.isArray(data)) {
        // Group tags by their category
        const categories = {};
        
        data.forEach(tag => {
          if (tag.category) {
            // Initialize the category array if it doesn't exist
            if (!categories[tag.category]) {
              categories[tag.category] = [];
            }
            // Add the tag to its category
            categories[tag.category].push(tag);
          } else {
            // For tags without a category, place in "Other"
            if (!categories['Other']) {
              categories['Other'] = [];
            }
            categories['Other'].push(tag);
          }
        });
        
        // Add default categories if they don't exist in the data
        const defaultCategories = ['Languages', 'Algorithms', 'Data Structures', 'Code Quality'];
        defaultCategories.forEach(category => {
          if (!categories[category]) {
            categories[category] = [];
          }
        });
        
        console.log('Processed tag categories:', categories);
        setTagCategories(categories);
      } else {
        console.error('Tags API returned unexpected format:', data);
        setTagCategories({
          'Languages': [],
          'Algorithms': [],
          'Data Structures': [],
          'Code Quality': []
        });
        setError(error => error || 'Error loading tag categories. Some features may be limited.');
      }
    } catch (err) {
      console.error('Error in fetchTagHierarchy:', err);
      setTagCategories({
        'Languages': [],
        'Algorithms': [],
        'Data Structures': [],
        'Code Quality': []
      });
      setError(prev => prev || 'Error loading tag categories. Some features may be limited.');
    }
  };

  // Test API connectivity to help diagnose issues
  const testAPIs = async () => {
    console.log('Testing API connectivity...');
    setError('Testing API connections...');
    
    try {
      // Test direct API access
      const tagsResponse = await fetch('/api/tags', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        }
      });
      
      console.log('Tags API status:', tagsResponse.status);
      const tagsData = await tagsResponse.json();
      console.log('Tags API response data:', tagsData);
      
      const problemsResponse = await fetch('/api/problems', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        }
      });
      
      console.log('Problems API status:', problemsResponse.status);
      const problemsData = await problemsResponse.json();
      console.log('Problems API response data:', problemsData);
      
      setError(`API test results - Tags: ${tagsResponse.status}, Problems: ${problemsResponse.status}`);
    } catch (err) {
      console.error('API test error:', err);
      setError(`API test error: ${err.message}`);
    }
  };

  const toggleTagSelection = (tagName) => {
    if (selectedTags.includes(tagName)) {
      setSelectedTags(prev => prev.filter(t => t !== tagName));
    } else {
      setSelectedTags(prev => [...prev, tagName]);
    }
  };

  const toggleCategoryExpansion = (category) => {
    setCategoryExpanded(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  // Normalize tag names for case-insensitive comparison
  const normalizeTagName = (name) => {
    return name ? name.toLowerCase() : '';
  };

  // Case-insensitive tag comparison
  const tagsMatch = (tag1, tag2) => {
    return normalizeTagName(tag1) === normalizeTagName(tag2);
  };

  // Format the difficulty level for display
  const formatDifficulty = (level) => {
    if (!level) return '';
    return level.charAt(0).toUpperCase() + level.slice(1).toLowerCase();
  };

  // Filter and sort problems according to selected filters and tag preferences
  const filteredProblems = () => {
    // No filtering needed if no problems
    if (!problems || problems.length === 0) {
      return [];
    }
    
    console.log('Filtering problems with selected tags:', selectedTags);
    
    // Early return if no filtering is needed
    if (selectedTags.length === 0 && !showOnlySubscribed) {
      return problems;
    }
    
    // First build a comprehensive map of all tags and their relationships
    const tagMap = new Map(); // Map of tag ID -> tag object
    const tagsByName = new Map(); // Map of lowercase tag name -> tag object
    const childrenMap = new Map(); // Map of parent ID -> array of child tags
    
    // Process all tags to build relationship maps
    Object.values(tagCategories).forEach(categoryTags => {
      categoryTags.forEach(tag => {
        if (tag && tag.id) {
          // Store in ID map
          tagMap.set(tag.id, tag);
          
          // Store in name map (case insensitive)
          if (tag.name) {
            tagsByName.set(tag.name.toLowerCase(), tag);
          }
          
          // Track parent-child relationships
          if (tag.parent_tag_id) {
            if (!childrenMap.has(tag.parent_tag_id)) {
              childrenMap.set(tag.parent_tag_id, []);
            }
            childrenMap.get(tag.parent_tag_id).push(tag);
          }
          // Also track by parent_name for backward compatibility
          else if (tag.parent_name) {
            const parentTagByName = Array.from(tagMap.values()).find(
              t => t.name && t.name.toLowerCase() === tag.parent_name.toLowerCase()
            );
            if (parentTagByName) {
              if (!childrenMap.has(parentTagByName.id)) {
                childrenMap.set(parentTagByName.id, []);
              }
              childrenMap.get(parentTagByName.id).push(tag);
            }
          }
        }
      });
    });
    
    console.log('Tag relationships built: ', 
      `${tagMap.size} total tags, `,
      `${childrenMap.size} parent tags with children`);
    
    // Create an expanded set of tags including children of selected parents
    const expandedTags = new Set();
    
    // Add all selected tags to the expanded set (lowercase for case-insensitive matching)
    selectedTags.forEach(tagName => {
      const normalizedName = tagName.toLowerCase();
      expandedTags.add(normalizedName);
      
      // Find the tag object by name
      const tagObj = tagsByName.get(normalizedName);
      
      if (tagObj && tagObj.id) {
        // If this tag has children, add all of them to the expanded set
        if (childrenMap.has(tagObj.id)) {
          const children = childrenMap.get(tagObj.id);
          console.log(`Adding ${children.length} child tags for parent: ${tagName}`);
          
          children.forEach(childTag => {
            if (childTag.name) {
              console.log(`- Adding child tag: ${childTag.name}`);
              expandedTags.add(childTag.name.toLowerCase());
            }
          });
        } else {
          console.log(`No children found for tag: ${tagName}`);
        }
      } else {
        console.log(`Tag object not found for: ${tagName}`);
      }
    });
    
    console.log('Expanded tag selection:', Array.from(expandedTags));
    
    // Filter problems based on expanded tags
    let filteredProbs = problems.filter(problem => {
      // Skip problems without tags
      if (!Array.isArray(problem.tags) || problem.tags.length === 0) {
        return false;
      }
      
      // If showing only subscribed problems is enabled, filter accordingly
      if (showOnlySubscribed) {
        const hasSubscribedTag = problem.tags.some(tag => 
          subscribedTags.includes(tag.name)
        );
        
        if (!hasSubscribedTag) {
          return false;
        }
      }
      
      // Only include problems that match our expanded tag set if tags are selected
      if (selectedTags.length > 0) {
        return problem.tags.some(tag => {
          const tagNameLower = tag.name?.toLowerCase();
          return tagNameLower && expandedTags.has(tagNameLower);
        });
      }
      
      // If no tags are selected, include the problem (already filtered by subscription if needed)
      return true;
    });
    
    // Sort problems by subscription status (subscribed ones first)
    return filteredProbs.sort((a, b) => {
      const aHasSubscribedTag = a.tags.some(tag => subscribedTags.includes(tag.name));
      const bHasSubscribedTag = b.tags.some(tag => subscribedTags.includes(tag.name));
      
      if (aHasSubscribedTag && !bHasSubscribedTag) return -1;
      if (!aHasSubscribedTag && bHasSubscribedTag) return 1;
      
      // Then sort by difficulty level (easier ones first)
      const difficultyOrder = { 'easy': 1, 'medium': 2, 'hard': 3 };
      const aDiff = a.difficulty_level?.toLowerCase() || 'medium';
      const bDiff = b.difficulty_level?.toLowerCase() || 'medium';
      
      return difficultyOrder[aDiff] - difficultyOrder[bDiff];
    });
  };

  // Get color for difficulty badge
  const getDifficultyColor = (level) => {
    if (!level) return '#888';
    
    level = level.toLowerCase();
    if (level === 'easy') return '#4caf50';
    if (level === 'medium') return '#ff9800';
    if (level === 'hard') return '#f44336';
    
    return '#888'; // Default for unknown levels
  };

  // Render tag with appropriate color based on hierarchy
  const renderTag = (tag) => {
    // Default color for regular tags
    let color = '#3498db';
    let backgroundColor = '#e3f2fd';
    
    // If this is a subscribed tag, highlight it
    if (subscribedTags.includes(tag.name)) {
      color = '#2e7d32';
      backgroundColor = '#e8f5e9';
    }
    
    return (
      <span
        key={tag.id || tag.name}
        style={{
          display: 'inline-block',
          padding: '3px 8px',
          backgroundColor: backgroundColor,
          color: color,
          borderRadius: '12px',
          fontSize: '12px',
          marginRight: '5px',
          marginBottom: '5px',
          border: `1px solid ${color}`
        }}
      >
        {tag.name}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '50px 0' }}>
        <h2>Loading problems...</h2>
        <div className="loading-spinner" style={{ 
          width: '40px',
          height: '40px',
          margin: '0 auto',
          border: '4px solid #f3f3f3',
          borderTop: '4px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 2s linear infinite'
        }}></div>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Coding Problems</h1>
      
      {error && (
        <div style={{ 
          padding: '15px',
          backgroundColor: '#fff3cd',
          color: '#856404',
          borderRadius: '5px',
          marginBottom: '20px'
        }}>
          {error}
          <div style={{ marginTop: '10px' }}>
            <button
              onClick={fetchTagHierarchy}
              style={{
                padding: '5px 10px',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                marginRight: '10px'
              }}
            >
              Retry
            </button>
            <button
              onClick={testAPIs}
              style={{
                padding: '5px 10px',
                backgroundColor: '#0062cc',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer'
              }}
            >
              Test APIs
            </button>
          </div>
        </div>
      )}
      
      <div style={{ display: 'flex', marginTop: '20px', gap: '30px' }}>
        {/* Sidebar with filter options */}
        <div style={{ minWidth: '250px', maxWidth: '250px', borderRight: '1px solid #e0e0e0', paddingRight: '20px' }}>
          <h3>Filter by Tags</h3>
          
          {/* Subscription preference toggle */}
          <div style={{ 
            marginBottom: '20px', 
            padding: '10px', 
            backgroundColor: '#f5f5f5', 
            borderRadius: '5px'
          }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={showOnlySubscribed}
                onChange={(e) => setShowOnlySubscribed(e.target.checked)}
                style={{ marginRight: '8px' }}
              />
              <div>
                Show only subscribed
                {subscribedTags.length > 0 && (
                  <span style={{ 
                    marginLeft: '5px', 
                    fontSize: '12px', 
                    color: '#666',
                    fontStyle: 'italic' 
                  }}>({subscribedTags.length})</span>
                )}
              </div>
            </label>
          </div>
          
          {Object.keys(tagCategories).map(category => (
            <div key={category} style={{ marginBottom: '15px' }}>
              {/* Category heading with toggle */}
              <div 
                onClick={() => toggleCategoryExpansion(category)}
                style={{ 
                  padding: '8px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                <span>{category}</span>
                <span>{categoryExpanded[category] ? '▲' : '▼'}</span>
              </div>
              
              {/* Tags under this category */}
              {categoryExpanded[category] && (
                <div style={{ marginLeft: '10px', marginTop: '5px' }}>
                  {tagCategories[category] && tagCategories[category].length > 0 ? (
                    tagCategories[category].map(tag => (
                      <div 
                        key={tag.id} 
                        style={{ 
                          padding: '8px 10px',
                          marginBottom: '5px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          backgroundColor: selectedTags.includes(tag.name) ? '#e3f2fd' : 'transparent',
                          border: selectedTags.includes(tag.name) ? '1px solid #bbdefb' : '1px solid transparent',
                          transition: 'all 0.2s ease'
                        }}
                        onClick={() => toggleTagSelection(tag.name)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span 
                            style={{ 
                              fontWeight: tag.parent_tag_id || tag.parent_name ? 'normal' : 'medium',
                              paddingLeft: tag.parent_tag_id || tag.parent_name ? '15px' : '0',
                              borderLeft: tag.parent_tag_id || tag.parent_name ? '2px solid #e0e0e0' : 'none'
                            }}
                          >
                            {tag.name}
                          </span>
                          {subscribedTags.includes(tag.name) && (
                            <span style={{ color: '#4caf50', fontSize: '20px' }}>•</span>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '10px', color: '#888', fontStyle: 'italic' }}>
                      No tags in this category
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Main content area with problems */}
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: '20px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {selectedTags.length > 0 && (
              <div style={{ width: '100%', marginBottom: '10px' }}>
                <h4>Selected Tags:</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                  {selectedTags.map(tag => (
                    <div 
                      key={tag}
                      style={{ 
                        display: 'inline-flex',
                        alignItems: 'center',
                        backgroundColor: 'white',
                        border: '1px solid #3498db',
                        color: '#3498db',
                        borderRadius: '16px',
                        padding: '4px 12px',
                        margin: '2px',
                        fontSize: '14px'
                      }}
                    >
                      {tag}
                      <span 
                        onClick={() => toggleTagSelection(tag)}
                        style={{
                          marginLeft: '6px',
                          cursor: 'pointer',
                          fontWeight: 'bold'
                        }}
                      >×</span>
                    </div>
                  ))}
                  {selectedTags.length > 1 && (
                    <div 
                      style={{ 
                        display: 'inline-flex',
                        alignItems: 'center',
                        backgroundColor: 'white',
                        border: '1px solid #f44336',
                        color: '#f44336',
                        borderRadius: '16px',
                        padding: '4px 12px',
                        margin: '2px',
                        fontSize: '14px',
                        cursor: 'pointer'
                      }}
                      onClick={() => setSelectedTags([])}
                    >
                      Clear All
                      <span style={{ marginLeft: '6px', fontWeight: 'bold' }}>×</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {error && !problems.length && (
            <div style={{ textAlign: 'center', padding: '20px', marginTop: '20px' }}>
              <div style={{ fontSize: '48px', color: '#d32f2f', marginBottom: '20px' }}>
                ⚠️
              </div>
              <h3>Error Loading Problems</h3>
              <p>{error}</p>
              <div style={{ marginTop: '10px' }}>
                <button
                  onClick={fetchProblems}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: '#4caf50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    marginRight: '10px'
                  }}
                >
                  Retry
                </button>
                <button
                  onClick={testAPIs}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: '#0062cc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  Test APIs
                </button>
              </div>
            </div>
          )}
          
          {filteredProblems().length === 0 ? (
            <div style={{ textAlign: 'center', padding: '50px 0' }}>
              <h3>{error ? 'Error loading problems' : 'No problems match your selected filters'}</h3>
              {(selectedTags.length > 0 || showOnlySubscribed) && (
                <button 
                  onClick={() => {
                    setSelectedTags([]);
                    setShowOnlySubscribed(false);
                  }}
                  style={{
                    marginTop: '15px',
                    padding: '8px 15px',
                    backgroundColor: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  Clear All Filters
                </button>
              )}
            </div>
          ) : (
            filteredProblems().map(problem => (
              <div 
                key={problem.id} 
                style={{
                  border: '1px solid #e0e0e0',
                  borderRadius: '5px',
                  padding: '20px',
                  marginBottom: '20px',
                  backgroundColor: problem.tags.some(tag => subscribedTags.includes(tag.name)) ? '#f9fffa' : 'white',
                  borderLeft: problem.tags.some(tag => subscribedTags.includes(tag.name)) ? '4px solid #4caf50' : '1px solid #e0e0e0'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h3 style={{ margin: 0 }}>{problem.title}</h3>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '3px 10px',
                      backgroundColor: getDifficultyColor(problem.difficulty_level),
                      color: 'white',
                      borderRadius: '12px',
                      fontSize: '14px'
                    }}
                  >
                    {formatDifficulty(problem.difficulty_level)}
                  </span>
                </div>
                
                <p>{problem.description.substring(0, 200)}...</p>
                
                <div style={{ marginTop: '15px' }}>
                  {problem.tags && problem.tags.map(tag => renderTag(tag))}
                </div>
                
                <button
                  style={{
                    marginTop: '15px',
                    padding: '8px 15px',
                    backgroundColor: '#3498db',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                  onClick={() => {
                    console.log('Navigating to problem detail:', problem.id);
                    // Navigate to the problem detail page
                    navigate(`/problem/${problem.id}`, { 
                      state: { problem } // Pass problem data as state to avoid additional API call
                    });
                  }}
                >
                  View Problem
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Problems;
