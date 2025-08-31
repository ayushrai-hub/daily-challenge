import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// Direct API URL to avoid process.env reference error
const API_BASE_URL = '/api'; // This will use the relative path to the current host

function Problems() {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const problemsPerPage = 10;
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
  const [hideTestProblems, setHideTestProblems] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchProblems();
    fetchTagHierarchy();
    fetchUserSubscribedTags();
    
    // For debugging purposes, directly print the problems we have
    console.log('EFFECT: Starting debug logging');
  }, []);
  
  // Add a debug function to show problem details
  const debugProblems = () => {
    console.log('==== DEBUG PROBLEMS ====');
    console.log('Total problems:', problems.length);
    const approved = problems.filter(p => p.status === 'approved');
    console.log('Approved problems:', approved.length);
    approved.forEach(p => console.log('Approved:', p.id, p.title));
    
    // Log a few of the latest problems
    console.log('Latest problems:');
    const latest = [...problems].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);
    latest.forEach(p => console.log('Latest:', p.id, p.title, p.status, p.created_at));
    
    // Count test problems
    const testProblems = problems.filter(p => {
      const titleLower = (p.title || '').toLowerCase();
      return titleLower.includes('test problem') || 
        titleLower.includes('test delivery') ||
        titleLower.includes('integration test') ||
        (titleLower.startsWith('new problem') && titleLower.length > 12) ||
        (titleLower.startsWith('read problem') && titleLower.length > 13);
    });
    console.log('Test problems:', testProblems.length);
  };
  
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
      // Add cache-busting timestamp to prevent cached responses
      const timestamp = Date.now();
      
      // Regular users should only see approved problems
      const approvedResponse = await fetch(`/api/problems?include_tags=true&status=approved&t=${timestamp}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      // Check if response was successful
      if (!approvedResponse.ok) {
        console.error(`Approved problems API error: ${approvedResponse.status} ${approvedResponse.statusText}`);
        throw new Error(`API error for approved problems: ${approvedResponse.status}`);
      }
      
      // Parse the JSON response
      const approvedData = await approvedResponse.json();
      
      // Add detailed logging to help debug issues
      console.log('Approved Problems API response:', approvedData);
      
      // Only use approved problems
      const data = Array.isArray(approvedData) ? approvedData : [];
      
      // Process the combined data
      let array = data;
      console.log('Combined problems array length:', array.length);
      if (array.length > 0) {
        // Normalize the problem data to ensure tag information is consistent
        const normalizedProblems = array.map(problem => {
          // Make sure tags is always an array, even if it's missing or null
          return {
            ...problem,
            tags: Array.isArray(problem.tags) ? problem.tags : []
          };
        });
        
        // Sort by creation date (newest first)
        // No need to prioritize by status since all should be approved
        normalizedProblems.sort((a, b) => {
          return new Date(b.created_at) - new Date(a.created_at);
        });
        
        console.log('Problems after sorting:', normalizedProblems.map(p => ({ id: p.id, title: p.title, status: p.status, created_at: p.created_at })));
        
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
    
    console.log('Total problems before filtering:', problems.length);
    
    // Start with all problems
    let result = [...problems];
    
    // Step 1: Filter out test problems if the toggle is enabled
    if (hideTestProblems) {
      result = result.filter(problem => {
        const titleLower = (problem.title || '').toLowerCase();
        return !(
          titleLower.includes('test problem') || 
          titleLower.includes('test delivery') ||
          titleLower.includes('integration test') ||
          (titleLower.startsWith('new problem') && titleLower.match(/new problem [a-f0-9]{8}/i)) ||
          (titleLower.startsWith('read problem') && titleLower.match(/read problem [a-f0-9]{8}/i))
        );
      });
      console.log(`After filtering test problems: ${result.length} problems left`);
    }
    
    // Step 2: Filter for subscribed tags if needed
    if (showOnlySubscribed) {
      result = result.filter(problem => {
        if (!Array.isArray(problem.tags)) return false;
        return problem.tags.some(tag => subscribedTags.includes(tag.name));
      });
      console.log(`After filtering for subscribed tags: ${result.length} problems left`);
    }
    
    // Step 3: Filter for selected tags
    if (selectedTags.length > 0) {
      // First convert selectedTags to lowercase for case-insensitive comparison
      const selectedTagsLower = selectedTags.map(tag => tag.toLowerCase());
      
      result = result.filter(problem => {
        if (!Array.isArray(problem.tags)) return false;
        
        // Check if any of this problem's tags match any selected tag
        return problem.tags.some(tag => {
          if (!tag || !tag.name) return false;
          return selectedTagsLower.includes(tag.name.toLowerCase());
        });
      });
      console.log(`After filtering for selected tags: ${result.length} problems left`);
    }
    
    // Step 4: Always log approved problems for debugging
    const approved = result.filter(p => p.status === 'approved');
    console.log('Approved problems in filtered set:', approved.length);
    if (approved.length > 0) {
      approved.forEach(p => console.log('- Approved problem in results:', p.id, p.title));
    }
    
    // Step 5: Sort problems by creation date (newest first)
    // No need to prioritize by status since all should be approved
    result.sort((a, b) => {
      return new Date(b.created_at) - new Date(a.created_at);
    });
    
    return result;
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

  // Handle pagination change
  const handlePageChange = (event, value) => {
    setPage(value);
    window.scrollTo(0, 0); // Scroll to top when changing pages
  };

  // Get current problems for pagination
  const getCurrentProblems = () => {
    const indexOfLastProblem = page * problemsPerPage;
    const indexOfFirstProblem = indexOfLastProblem - problemsPerPage;
    return filteredProblems().slice(indexOfFirstProblem, indexOfLastProblem);
  };
  
  const renderPagination = () => {
    const pageCount = Math.ceil(filteredProblems().length / problemsPerPage);
    if (pageCount <= 1) return null;
    
    const renderPageButton = (pageNum) => {
      return (
        <button
          key={pageNum}
          onClick={() => handlePageChange(null, pageNum)}
          style={{
            margin: '0 5px',
            padding: '5px 10px',
            backgroundColor: page === pageNum ? '#3498db' : '#f0f0f0',
            color: page === pageNum ? 'white' : 'black',
            border: 'none',
            borderRadius: '3px',
            cursor: 'pointer'
          }}
        >
          {pageNum}
        </button>
      );
    };
    
    // Create array of page buttons to show
    const getPageButtons = () => {
      const buttons = [];
      const maxButtonsToShow = 5;
      
      if (pageCount <= maxButtonsToShow) {
        // Show all buttons if we have 5 or fewer pages
        for (let i = 1; i <= pageCount; i++) {
          buttons.push(renderPageButton(i));
        }
      } else {
        // Always show first page
        buttons.push(renderPageButton(1));
        
        // Add ellipsis if needed
        if (page > 3) {
          buttons.push(<span key="ellipsis1">...</span>);
        }
        
        // Add pages around current page
        const startPage = Math.max(2, page - 1);
        const endPage = Math.min(pageCount - 1, page + 1);
        
        for (let i = startPage; i <= endPage; i++) {
          buttons.push(renderPageButton(i));
        }
        
        // Add ellipsis if needed
        if (page < pageCount - 2) {
          buttons.push(<span key="ellipsis2">...</span>);
        }
        
        // Always show last page
        buttons.push(renderPageButton(pageCount));
      }
      
      return buttons;
    };
    
    return (
      <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
        <button
          onClick={() => handlePageChange(null, 1)}
          disabled={page === 1}
          style={{
            margin: '0 5px',
            padding: '5px 10px',
            backgroundColor: page === 1 ? '#f0f0f0' : '#3498db',
            color: page === 1 ? '#999' : 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: page === 1 ? 'default' : 'pointer'
          }}
        >
          First
        </button>
        
        <button
          onClick={() => handlePageChange(null, page - 1)}
          disabled={page === 1}
          style={{
            margin: '0 5px',
            padding: '5px 10px',
            backgroundColor: page === 1 ? '#f0f0f0' : '#3498db',
            color: page === 1 ? '#999' : 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: page === 1 ? 'default' : 'pointer'
          }}
        >
          &lt; Prev
        </button>
        
        {getPageButtons()}
        
        <button
          onClick={() => handlePageChange(null, page + 1)}
          disabled={page === pageCount}
          style={{
            margin: '0 5px',
            padding: '5px 10px',
            backgroundColor: page === pageCount ? '#f0f0f0' : '#3498db',
            color: page === pageCount ? '#999' : 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: page === pageCount ? 'default' : 'pointer'
          }}
        >
          Next &gt;
        </button>
        
        <button
          onClick={() => handlePageChange(null, pageCount)}
          disabled={page === pageCount}
          style={{
            margin: '0 5px',
            padding: '5px 10px',
            backgroundColor: page === pageCount ? '#f0f0f0' : '#3498db',
            color: page === pageCount ? '#999' : 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: page === pageCount ? 'default' : 'pointer'
          }}
        >
          Last
        </button>
      </div>
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
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={showOnlySubscribed}
                  onChange={() => setShowOnlySubscribed(!showOnlySubscribed)}
                  style={{
                    marginRight: '8px'
                  }}
                />
                Show only problems with subscribed tags
                {subscribedTags.length > 0 && (
                  <span style={{ 
                    marginLeft: '5px', 
                    fontSize: '12px', 
                    color: '#666',
                    fontStyle: 'italic' 
                  }}>({subscribedTags.length})</span>
                )}
              </label>
            </div>
            
            <div style={{ marginTop: '10px' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={hideTestProblems}
                  onChange={() => setHideTestProblems(!hideTestProblems)}
                  style={{
                    marginRight: '8px'
                  }}
                />
                Hide test problems
              </label>
            </div>
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
            <>
              {getCurrentProblems().map(problem => (
              <div 
                key={problem.id} 
                style={{
                  border: '1px solid #e0e0e0',
                  borderRadius: '5px',
                  padding: '20px',
                  marginBottom: '20px',
                  backgroundColor: problem.tags.some(tag => subscribedTags.includes(tag.name)) ? '#f9fffa' : '#e3f2fd',
                  borderLeft: problem.tags.some(tag => subscribedTags.includes(tag.name)) ? '4px solid #4caf50' : '4px solid #2196f3'
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
            ))}
              {filteredProblems().length > 0 && renderPagination()}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Problems;
