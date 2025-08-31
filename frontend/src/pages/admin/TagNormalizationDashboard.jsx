import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './admin.css';

// Add search-specific CSS
const searchStyles = `
  .search-group {
    width: 100%;
    position: relative;
  }
  
  .search-input-container {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
  }
  
  .search-input-container input {
    width: 100%;
    padding: 10px 40px 10px 35px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    transition: all 0.2s ease;
  }
  
  .search-input-container input:focus {
    border-color: #4a8df8;
    box-shadow: 0 2px 8px rgba(74,141,248,0.15);
    outline: none;
  }
  
  .search-icon {
    position: absolute;
    left: 10px;
    pointer-events: none;
  }
  
  .clear-search {
    position: absolute;
    right: 10px;
    background: none;
    border: none;
    font-size: 16px;
    cursor: pointer;
    color: #666;
    transition: color 0.2s ease;
  }
  
  .clear-search:hover {
    color: #f44336;
  }
  
  .search-highlight {
    background-color: #ffeb3b;
    padding: 0 2px;
    border-radius: 2px;
    font-weight: bold;
  }
`;

// Add styles to document head
const styleElement = document.createElement('style');
styleElement.textContent = searchStyles;
document.head.appendChild(styleElement);

// API base URL from environment variable or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Helper component to highlight search matches
const HighlightText = ({ text, highlight }) => {
  if (!highlight.trim()) {
    return <span>{text}</span>;
  }
  
  const regex = new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  
  return (
    <span>
      {parts.map((part, i) => 
        regex.test(part) ? (
          <mark key={i} className="search-highlight">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
};

const TagNormalizationDashboard = () => {
  const navigate = useNavigate();
  // State management
  const [normalizations, setNormalizations] = useState([]);
  const [allNormalizations, setAllNormalizations] = useState([]); // Store all tags without pagination
  const [filteredNormalizations, setFilteredNormalizations] = useState([]); // Store filtered tags
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [stats, setStats] = useState({
    pending: 0,
    approved: 0,
    rejected: 0,
    total: 0
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [sourceFilter, setSourceFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0);
  const [isSearching, setIsSearching] = useState(false); // Track if search is active
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);
  const [processing, setProcessing] = useState(false);
  
  // Modal state for approval/rejection
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [showRejectionModal, setShowRejectionModal] = useState(false);
  const [adminNotes, setAdminNotes] = useState('');
  
  // State for similar tags warning and merging
  const [similarTags, setSimilarTags] = useState([]);
  const [checkingSimilarity, setCheckingSimilarity] = useState(false);
  const [mergeTags, setMergeTags] = useState(false);
  const [mergeTarget, setMergeTarget] = useState(null);
  
  // Fetch tag normalizations with pagination for display
  const fetchNormalizations = async () => {
    if (isSearching && searchQuery.trim()) {
      // If searching, we're using the frontend filtered tags
      return;
    }
    
    setLoading(true);
    try {
      // Build query parameters
      const params = {
        status: statusFilter,
        page: page,
        page_size: pageSize
      };
      
      if (sourceFilter) {
        params.source = sourceFilter;
      }
      
      if (confidenceThreshold > 0) {
        params.min_confidence = confidenceThreshold;
      }
      
      // Don't send search query to backend - we'll search client-side
      
      try {
        // Build query string
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            queryParams.append(key, value);
          }
        });
        
        // Get auth token
        const token = localStorage.getItem('auth_token');
        if (!token) {
          console.error('No auth token found');
          navigate('/login', { replace: true });
          return;
        }
        
        // Make direct API call - IMPORTANT: always use the endpoint WITH a trailing slash to avoid redirect issues
        const response = await axios.get(`${API_BASE_URL}/admin/tag-normalizations/?${queryParams.toString()}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        // If searching, use the filtered results
        if (isSearching && searchQuery.trim()) {
          const startIndex = (page - 1) * pageSize;
          const endIndex = startIndex + pageSize;
          const paginatedResults = filteredNormalizations.slice(startIndex, endIndex);
          setNormalizations(paginatedResults);
          setTotalPages(Math.ceil(filteredNormalizations.length / pageSize));
          setTotalItems(filteredNormalizations.length);
        } else {
          setNormalizations(response.data.items);
          setTotalPages(response.data.pages);
          setTotalItems(response.data.total);
        }
      } catch (apiError) {
        console.error('Error from API:', apiError);
        
        // Check for 401 Unauthorized errors (expired token or not authenticated)
        if (apiError.response && (apiError.response.status === 401 || apiError.response.status === 403)) {
          console.log('Session expired or unauthorized, redirecting to login');
          localStorage.removeItem('auth_token'); // Clear the invalid token
          navigate('/login', { replace: true });
          return;
        }
        
        console.warn('Using mock data instead');
        // Generate mock data for development
        const mockItems = Array(pageSize).fill(null).map((_, i) => ({
          id: `mock-${i}`,
          original_name: `tag-${i}`,
          normalized_name: `Tag ${i}`,
          review_status: statusFilter || ['pending', 'approved', 'rejected'][Math.floor(Math.random() * 3)],
          source: 'ai_generated',
          confidence_score: Math.random() * 0.5 + 0.5,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }));
        
        setNormalizations(mockItems);
        setTotalPages(5);
        setTotalItems(100);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching tag normalizations:', err);
      
      // Check for 401 Unauthorized errors in the outer catch block too
      if (err.response && (err.response.status === 401 || err.response.status === 403)) {
        console.log('Session expired or unauthorized, redirecting to login');
        localStorage.removeItem('auth_token'); // Clear the invalid token
        navigate('/login', { replace: true });
        return;
      }
      
      setError('Failed to load tag normalizations. Please try again later.');
      setLoading(false);
    }
  };
  
  // Fetch stats
  const fetchStats = async () => {
    try {
      try {
        // Get auth token
        const token = localStorage.getItem('auth_token');
        if (!token) {
          console.error('No auth token found');
          navigate('/login', { replace: true });
          return;
        }
        
        // Try to fetch stats from backend
        const response = await axios.get(`${API_BASE_URL}/admin/tag-normalizations/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        setStats(response.data);
      } catch (statsError) {
        console.error('Stats endpoint error:', statsError);
        
        // Check for 401 Unauthorized errors (expired token or not authenticated)
        if (statsError.response && (statsError.response.status === 401 || statsError.response.status === 403)) {
          console.log('Session expired or unauthorized, redirecting to login');
          localStorage.removeItem('auth_token'); // Clear the invalid token
          navigate('/login', { replace: true });
          return;
        }
        
        console.warn('Using default stats instead');
        // Default stats for development
        setStats({
          total: 100,
          pending: 45,
          approved: 35,
          rejected: 20,
          auto_approved: 10
        });
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
      
      // Check for authorization errors in the outer catch too
      if (err.response && (err.response.status === 401 || err.response.status === 403)) {
        console.log('Session expired or unauthorized, redirecting to login');
        localStorage.removeItem('auth_token');
        navigate('/login', { replace: true });
      }
    }
  };
  
  // Track operation type (single or batch)
  const [operationType, setOperationType] = useState('single');
  
  // Check for similar tags before approval
  const checkSimilarTags = async (tagName) => {
    setCheckingSimilarity(true);
    setSimilarTags([]);
    
    try {
      const token = localStorage.getItem('auth_token');
      
      // Call the similar-tags endpoint
      const response = await axios.get(
        `${API_BASE_URL}/admin/tag-normalizations/similar-tags/${encodeURIComponent(tagName)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response?.data) {
        setSimilarTags(response.data);
        return response.data;
      }
      
      return [];
    } catch (err) {
      console.error('Error checking similar tags:', err);
      return [];
    } finally {
      setCheckingSimilarity(false);
    }
  };
  
  // Check for similarities between multiple tags in the selection
  const checkInternalSimilarities = (selectedTags) => {
    if (selectedTags.length <= 1) return [];
    
    const internalSimilarities = [];
    
    // Compare each pair of tags for similarities
    for (let i = 0; i < selectedTags.length; i++) {
      for (let j = i + 1; j < selectedTags.length; j++) {
        const tag1 = selectedTags[i].normalized_name;
        const tag2 = selectedTags[j].normalized_name;
        const tag1Lower = tag1.toLowerCase();
        const tag2Lower = tag2.toLowerCase();
        
        // Skip identical tags (case-insensitive)
        if (tag1Lower === tag2Lower) {
          // If the tags are identical except for case, that's a very high similarity
          internalSimilarities.push({
            id: `internal-${i}-${j}`,
            name: tag2,
            description: `Same as "${tag1}" but with different capitalization`,
            match_type: 'very_similar',
            similarity: 0.99,
            originalName: tag1
          });
          continue;
        }
        
        // Check various similarity patterns
        let similarity = 0;
        let description = '';
        
        // Check if one contains the other
        if (tag1Lower.includes(tag2Lower) || tag2Lower.includes(tag1Lower)) {
          similarity = 0.8;
          description = 'One tag contains the other';
        }
        
        // Check if removing spaces/hyphens/underscores makes them similar
        const clean1 = tag1Lower.replace(/[-_\s]/g, '');
        const clean2 = tag2Lower.replace(/[-_\s]/g, '');
        
        if (clean1 === clean2) {
          similarity = 0.95;
          description = 'Same but with different formatting (spaces/hyphens)';
        }
        
        // Check for common patterns (plurals, acronyms, etc.)
        if (
          (tag1Lower.endsWith('s') && tag2Lower === tag1Lower.slice(0, -1)) ||
          (tag2Lower.endsWith('s') && tag1Lower === tag2Lower.slice(0, -1))
        ) {
          similarity = 0.9;
          description = 'One is the plural form of the other';
        }
        
        // Check for acronym patterns
        // e.g., "REST API" vs "rest-api"
        const words1 = tag1Lower.split(/[-_\s]/);
        const words2 = tag2Lower.split(/[-_\s]/);
        
        // Check if one could be an acronym of the other
        if (words1.length > 1 || words2.length > 1) {
          const possibleAcronym1 = words1.map(word => word[0]).join('');
          const possibleAcronym2 = words2.map(word => word[0]).join('');
          
          if (
            (words2.length === 1 && possibleAcronym1 === tag2Lower) ||
            (words1.length === 1 && possibleAcronym2 === tag1Lower)
          ) {
            similarity = 0.85;
            description = 'One appears to be an acronym of the other';
          }
        }
        
        // Check for API-specific patterns (case sensitive)
        if (
          (tag1.includes('API') && tag2.includes('Api')) ||
          (tag1.includes('Api') && tag2.includes('API'))
        ) {
          similarity = Math.max(similarity, 0.95);
          description = 'Different capitalization of API term';
        }
        
        // Create similarity record if significant similarity found
        if (similarity > 0.5) {
          internalSimilarities.push({
            id: `internal-${i}-${j}`,
            name: tag2,
            description: description || `Similar to "${tag1}" in this batch`,
            match_type: similarity > 0.9 ? 'very_similar' : 'similar',
            similarity: similarity,
            originalName: tag1
          });
        }
      }
    }
    
    return internalSimilarities;
  };
  
  // Individual tag approval handler
  const handleSingleApprove = async (normalizationId) => {
    setSelectedIds(new Set([normalizationId]));
    setOperationType('single');
    setShowRejectionModal(false); // Reset any rejection selection
    
    // Find the tag to be approved
    const normalization = normalizations.find(n => n.id === normalizationId);
    if (normalization) {
      // First check for similar tags
      await checkSimilarTags(normalization.normalized_name);
    }
    
    // Show the approval modal
    setShowApprovalModal(true);
  };
  
  // Individual tag rejection handler
  const handleSingleReject = (normalizationId) => {
    setSelectedIds(new Set([normalizationId]));
    setOperationType('single');
    setShowApprovalModal(false); // Reset any approval selection
    setShowRejectionModal(true);
  };
  
  // Execute single tag approval
  const executeSingleApproval = async (normalizationId, adminNotes) => {
    setProcessing(true);
    try {
      const token = localStorage.getItem('auth_token');
      
      // Prepare approval data
      const approvalData = {
        tag_name: normalizations.find(norm => norm.id === normalizationId)?.normalized_name || '',
        description: `Approved tag normalization`,
        admin_notes: adminNotes || 'Approved by admin'
      };
      
      await axios.post(`${API_BASE_URL}/admin/tag-normalizations/${normalizationId}/approve`, approvalData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      setMessage(`Successfully approved tag`);
      fetchNormalizations();
      fetchStats();
    } catch (err) {
      console.error('Error during tag approval:', err);
      setError('Failed to approve tag. Please try again.');
    } finally {
      setProcessing(false);
    }
  };
  
  // Execute single tag rejection 
  const executeSingleRejection = async (normalizationId, adminNotes) => {
    setProcessing(true);
    try {
      const token = localStorage.getItem('auth_token');
      
      // Prepare rejection data
      const rejectData = {
        admin_notes: adminNotes || 'Rejected by admin'
      };
      
      await axios.post(`${API_BASE_URL}/admin/tag-normalizations/${normalizationId}/reject`, rejectData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      setMessage(`Successfully rejected tag`);
      fetchNormalizations();
      fetchStats();
      
      // Clear any previous approval selection
      setShowApprovalModal(false);
      
      // Set operation type to batch for multiple items
      setOperationType(selectedIds.size > 1 ? 'batch' : 'single');
    } catch (err) {
      console.error('Error during tag rejection:', err);
      setError('Failed to reject tag. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  // Add debounce function for search
  const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        func(...args);
      }, delay);
    };
  };

  // Debounced search function
  const debouncedSearch = React.useCallback(
    debounce(() => {
      fetchNormalizations();
    }, 500),
    [] // Empty dependency array ensures this is only created once
  );

  // Function to fetch ALL tags (no pagination)
  const fetchAllNormalizations = async (forSearch = false) => {
    setError(null);
    
    try {
      // Get auth token
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.error('No auth token found');
        navigate('/login', { replace: true });
        return;
      }
      
      const params = new URLSearchParams();
      
      // If searching, don't apply status filter so we get ALL tags
      // Otherwise, apply the current status filter
      if (!forSearch) {
        params.append('status', statusFilter);
      }
      
      if (sourceFilter) params.append('source', sourceFilter);
      if (confidenceThreshold > 0) params.append('min_confidence', confidenceThreshold);
      
      // Use the maximum allowed page size (100 items per page)
      params.append('page_size', 100);
      params.append('page', 1);
      
      // Make direct API call to get first batch of tags
      const response = await axios.get(`${API_BASE_URL}/admin/tag-normalizations/?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Start collecting all items
      let allItems = [...response.data.items];
      console.log(`Fetched page 1 containing ${response.data.items.length} tags`);
      
      // If there are more pages, fetch them all
      const totalPages = response.data.pages;
      
      if (totalPages > 1) {
        // Fetch remaining pages
        for (let i = 2; i <= totalPages; i++) {
          params.set('page', i);
          try {
            const pageResponse = await axios.get(`${API_BASE_URL}/admin/tag-normalizations/?${params.toString()}`, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            allItems = [...allItems, ...pageResponse.data.items];
            console.log(`Fetched page ${i}/${totalPages} containing ${pageResponse.data.items.length} tags`);
          } catch (pageError) {
            console.error(`Error fetching page ${i}:`, pageError);
            // Continue with other pages even if one fails
          }
        }
      }
      
      // Update state with all fetched items
      setAllNormalizations(allItems);
      console.log(`Total tags fetched: ${allItems.length} across ${totalPages} pages`);
      
      // Show message if no tags found
      if (allItems.length === 0) {
        setError('No tags found matching the current filters.');
      }
    } catch (err) {
      console.error('Error fetching all normalizations:', err);
      setError('Failed to fetch complete tag dataset.');
    }
  };
  
  // Filter tags client-side when search query changes
  const performClientSideSearch = async () => {
    if (!searchQuery.trim()) {
      setIsSearching(false);
      fetchNormalizations(); // Revert to normal pagination
      return;
    }
    
    setIsSearching(true);
    setLoading(true);
    
    try {
      // Fetch ALL tags across ALL statuses when searching
      if (allNormalizations.length === 0) {
        await fetchAllNormalizations(true); // Pass true to indicate we're searching
      }
      
      // Case-insensitive search across both original and normalized names
      const query = searchQuery.trim().toLowerCase();
      const filtered = allNormalizations.filter(tag => 
        tag.original_name.toLowerCase().includes(query) || 
        tag.normalized_name.toLowerCase().includes(query)
      );
      
      // If status filter is active and not empty (all statuses), apply it after search
      const statusFiltered = statusFilter !== '' 
        ? filtered.filter(tag => tag.review_status === statusFilter)
        : filtered;
      
      // Apply confidence threshold filter if needed
      const confidenceFiltered = confidenceThreshold > 0 
        ? statusFiltered.filter(tag => (tag.confidence_score || 0) >= confidenceThreshold)
        : statusFiltered;
      
      setFilteredNormalizations(confidenceFiltered);
      
      // Update pagination for the filtered results
      const paginatedResults = confidenceFiltered.slice(0, pageSize);
      setNormalizations(paginatedResults);
      setTotalPages(Math.ceil(confidenceFiltered.length / pageSize));
      setTotalItems(confidenceFiltered.length);
      setPage(1); // Reset to first page when searching
      
      // Update the log to show filtered by status info if applicable
      if (statusFilter !== '') {
        console.log(`Found ${confidenceFiltered.length} ${statusFilter} tags matching "${searchQuery}"`);
      } else {
        console.log(`Found ${confidenceFiltered.length} tags (all statuses) matching "${searchQuery}"`);
      }
    } catch (err) {
      console.error('Error during client-side search:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Effect for search query changes - use client-side filtering
  useEffect(() => {
    // Make sure we have the full dataset before searching
    if (allNormalizations.length === 0 && searchQuery.trim() !== '') {
      // Fetch ALL tags across ALL statuses first, then search
      fetchAllNormalizations(true).then(() => performClientSideSearch());
    } else if (searchQuery.trim() !== '') {
      performClientSideSearch();
    }
  }, [searchQuery]);
  
  // Effect for filter changes (excluding search)
  useEffect(() => {
    // If search is active, update the client-side filters
    if (isSearching && searchQuery.trim()) {
      performClientSideSearch();
    } else {
      // Otherwise do a regular fetch with server-side filters
      fetchNormalizations();
    }
  }, [page, pageSize, statusFilter, sourceFilter, confidenceThreshold]);
  
  // Initial effect - fetch data and set up event listeners
  useEffect(() => {
    // Fetch initial data
    fetchNormalizations();
    fetchStats();
    
    // Also fetch all tags for instant search
    fetchAllNormalizations();
    
    // Add keyboard shortcut for search
    const handleKeyDown = (e) => {
      // Check for Ctrl+F or Cmd+F (Mac)
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault(); // Prevent browser's default search
        document.getElementById('tag-search-input').focus();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);
  
  // Handle selection
  const toggleSelectItem = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };
  
  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(normalizations.map(norm => norm.id)));
    }
    setSelectAll(!selectAll);
  };
  
  // Batch approve tags
  const handleBatchApprove = async () => {
    if (selectedIds.size === 0) {
      setError('No items selected for approval.');
      return;
    }
    
    // Clear any previous rejection selection
    setShowRejectionModal(false);
    
    // Set operation type to batch for multiple items
    setOperationType(selectedIds.size > 1 ? 'batch' : 'single');
    
    // Reset similar tags
    setSimilarTags([]);
    
    // Check for similar tags for each selected tag
    const selectedNormalizations = normalizations.filter(norm => selectedIds.has(norm.id));
    
    if (selectedNormalizations.length > 0) {
      // Check for internal similarities (between selected tags)
      const internalSimilarities = checkInternalSimilarities(selectedNormalizations);
      
      // If we found internal similarities, add them to the similar tags
      if (internalSimilarities.length > 0) {
        setSimilarTags(internalSimilarities);
      } else {
        // Only check external similarities if no internal ones were found
        // For efficiency, only check the first few tags if there are many
        const tagsToCheck = selectedNormalizations.length <= 5 ? 
          selectedNormalizations : 
          selectedNormalizations.slice(0, 5);
        
        // Check for similar tags for each normalized name
        for (const norm of tagsToCheck) {
          const similarResults = await checkSimilarTags(norm.normalized_name);
          
          // If we found similar tags, break early to avoid too many API calls
          if (similarResults.length > 0) {
            break;
          }
        }
      }
    }
    
    // Show approval modal
    setShowApprovalModal(true);
  };
  
  // Execute batch approval
  const executeBatchApproval = async () => {
    setProcessing(true);
    try {
      // Prepare data for approval
      const selectedNormalizations = normalizations.filter(norm => selectedIds.has(norm.id));
      
      // Get auth token
      const token = localStorage.getItem('auth_token');
      
      // Handle tag merging if selected
      if (mergeTags && mergeTarget && selectedIds.size > 1) {
        // Find which normalizations to merge
        const tagsToMerge = selectedNormalizations.filter(norm => 
          norm.normalized_name !== mergeTarget
        );
        const targetNorm = selectedNormalizations.find(norm => 
          norm.normalized_name === mergeTarget
        );
        
        if (targetNorm && tagsToMerge.length > 0) {
          // First approve the target tag
          const targetApprovalData = {
            tag_name: targetNorm.normalized_name,
            description: `Merged tag: ${targetNorm.normalized_name}`,
            admin_notes: adminNotes || `Selected as primary tag in merge operation`
          };
          
          await axios.post(
            `${API_BASE_URL}/admin/tag-normalizations/${targetNorm.id}/approve`, 
            targetApprovalData,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            }
          );
          
          // Then reject the other tags with a note about merging
          const rejectPromises = tagsToMerge.map(norm => {
            return axios.post(
              `${API_BASE_URL}/admin/tag-normalizations/${norm.id}/reject`,
              {
                admin_notes: `Merged into "${mergeTarget}" for consistency`
              },
              {
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                }
              }
            );
          });
          
          await Promise.all(rejectPromises);
          
          setMessage(`Successfully merged ${tagsToMerge.length + 1} tags into "${mergeTarget}"`);
        }
      }
      // Handle single tag approval
      else if (selectedIds.size === 1) {
        const normalizationId = Array.from(selectedIds)[0];
        const norm = normalizations.find(n => n.id === normalizationId);
        
        // Prepare approval data
        const approvalData = {
          tag_name: norm.normalized_name,
          description: `Approved tag: ${norm.normalized_name}`,
          admin_notes: adminNotes || 'Approved by admin'
        };
        
        await axios.post(`${API_BASE_URL}/admin/tag-normalizations/${normalizationId}/approve`, approvalData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        setMessage(`Successfully approved tag: ${norm.normalized_name}`);
      } 
      // Handle batch approval (multiple tags without merging)
      else {
        const approvalData = selectedNormalizations.map(norm => ({
          normalization_id: norm.id,
          tag_name: norm.normalized_name,
          description: `Batch approved tag: ${norm.normalized_name}`,
          admin_notes: adminNotes || 'Batch approved'
        }));
        
        await axios.post(`${API_BASE_URL}/admin/tag-normalizations/bulk-approve`, approvalData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        setMessage(`Successfully approved ${selectedIds.size} tags`);
      }
      
      // Reset state
      setShowApprovalModal(false);
      setSelectedIds(new Set());
      setSelectAll(false);
      setAdminNotes('');
      setMergeTags(false);
      setMergeTarget(null);
      setSimilarTags([]);
      fetchNormalizations();
      fetchStats();
    } catch (err) {
      console.error('Error during approval:', err);
      setError('Failed to approve tag(s). Please try again later.');
    } finally {
      setProcessing(false);
    }
  };
  
  // Batch reject tags
  const handleBatchReject = () => {
    if (selectedIds.size === 0) {
      setError('No items selected for rejection.');
      return;
    }
    
    // Clear any previous approval selection
    setShowApprovalModal(false);
    
    // Set operation type to batch for multiple items
    setOperationType(selectedIds.size > 1 ? 'batch' : 'single');
    
    // Show rejection modal
    setShowRejectionModal(true);
  };
  
  // Execute batch rejection
  const executeBatchRejection = async () => {
    setProcessing(true);
    try {
      // Get auth token
      const token = localStorage.getItem('auth_token');
      
      // Handle single tag rejection
      if (selectedIds.size === 1) {
        const normalizationId = Array.from(selectedIds)[0];
        const norm = normalizations.find(n => n.id === normalizationId);
        
        // Prepare rejection data
        const rejectData = {
          admin_notes: adminNotes || 'Rejected by admin'
        };
        
        await axios.post(`${API_BASE_URL}/admin/tag-normalizations/${normalizationId}/reject`, rejectData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        setMessage(`Successfully rejected tag: ${norm.normalized_name}`);
      } 
      // Handle batch rejection (multiple tags)
      else {
        const normalizationIds = Array.from(selectedIds);
        
        await axios.post(`${API_BASE_URL}/admin/tag-normalizations/bulk-reject`, {
          normalization_ids: normalizationIds,
          admin_notes: adminNotes || 'Batch rejected'
        }, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        setMessage(`Successfully rejected ${selectedIds.size} tags`);
      }
      
      // Reset state
      setShowRejectionModal(false);
      setSelectedIds(new Set());
      setSelectAll(false);
      setAdminNotes('');
      fetchNormalizations();
      fetchStats();
    } catch (err) {
      console.error('Error during rejection:', err);
      setError('Failed to reject tag(s). Please try again later.');
    } finally {
      setProcessing(false);
    }
  };
  
  // Render the approval modal
  const renderApprovalModal = () => {
    if (!showApprovalModal) return null;
    
    // Get selected normalizations
    const selectedTags = normalizations.filter(norm => selectedIds.has(norm.id));
    const title = operationType === 'single' ? 'Approve Tag' : 'Batch Approve Tags';
    
    // Generate warning message based on similar tags
    const hasSimilarTags = similarTags && similarTags.length > 0;
    
    // Check if there are internal similarities
    const hasInternalSimilarities = hasSimilarTags && similarTags.some(tag => tag.id && tag.id.toString().startsWith('internal-'));
    
    return (
      <div className="modal">
        <div className="modal-content">
          <h2>{title}</h2>
          <p>You are about to approve {selectedIds.size} tag {selectedIds.size > 1 ? 'normalizations' : 'normalization'}.</p>
          
          {/* Show warning for similar tags if any */}
          {hasSimilarTags && (
            <div className="similar-tag-warning">
              <div className="warning-icon">⚠️</div>
              <div className="warning-content">
                <h4>
                  {hasInternalSimilarities 
                    ? 'Similar Tags Within Selection!' 
                    : 'Similar Existing Tags Detected!'}
                </h4>
                <p>
                  {hasInternalSimilarities 
                    ? 'The following tags in your selection are very similar to each other:' 
                    : 'The following similar tags already exist in the database:'}
                </p>
                <div className="similar-tags-list">
                  {similarTags.map((tag, index) => (
                    <div key={index} className="similar-tag-item">
                      <span className="similar-tag-name">{tag.name}</span>
                      <span className="similar-tag-similarity">
                        {tag.match_type === 'exact' ? 'EXACT MATCH!' : 
                         tag.match_type === 'very_similar' ? 'NEARLY IDENTICAL!' :
                         `${Math.round(tag.similarity * 100)}% similar`}
                      </span>
                      {tag.originalName && (
                        <span className="similar-tag-description">
                          <strong>Similar to:</strong> {tag.originalName}
                        </span>
                      )}
                      {tag.description && (
                        <span className="similar-tag-description">{tag.description}</span>
                      )}
                    </div>
                  ))}
                </div>
                <p className="warning-advice">
                  {hasInternalSimilarities 
                    ? 'Consider consolidating these similar tags to avoid duplicates.' 
                    : 'Consider using an existing tag instead of creating a duplicate.'}
                </p>
                
                {/* Add merge option for internal similarities */}
                {hasInternalSimilarities && (
                  <div className="merge-options">
                    <label className="merge-checkbox">
                      <input 
                        type="checkbox" 
                        checked={mergeTags}
                        onChange={(e) => {
                          setMergeTags(e.target.checked);
                          if (e.target.checked && !mergeTarget && similarTags.length > 0) {
                            // Default to first tag as merge target
                            setMergeTarget(similarTags[0].originalName || similarTags[0].name);
                          }
                        }}
                      />
                      Merge similar tags
                    </label>
                    
                    {mergeTags && (
                      <div className="merge-target-selector">
                        <label>Keep this tag:</label>
                        <select 
                          value={mergeTarget || ''}
                          onChange={(e) => setMergeTarget(e.target.value)}
                        >
                          {selectedTags.map(tag => (
                            <option key={tag.id} value={tag.normalized_name}>
                              {tag.normalized_name}
                            </option>
                          ))}
                        </select>
                        <p className="merge-explanation">
                          Other similar tags will be consolidated into this one
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Show list of selected tags */}
          <div className="selected-tags-list">
            {selectedTags.map(tag => (
              <div key={tag.id} className="selected-tag">
                <span className="original-name">{tag.original_name}</span>
                <span className="arrow">→</span>
                <span className="normalized-name">{tag.normalized_name}</span>
                {/* Show exact match indicator if applicable */}
                {hasSimilarTags && similarTags.some(st => 
                  st.match_type === 'exact' && 
                  st.name.toLowerCase() === tag.normalized_name.toLowerCase()
                ) && (
                  <span className="exact-match-badge">DUPLICATE!</span>
                )}
              </div>
            ))}
          </div>
          
          <div className="form-group">
            <label>Admin Notes:</label>
            <textarea 
              value={adminNotes} 
              onChange={(e) => setAdminNotes(e.target.value)}
              placeholder="Add optional notes about this approval"
            />
          </div>
          
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setShowApprovalModal(false)}>Cancel</button>
            <button 
              className="btn btn-primary" 
              onClick={executeBatchApproval}
              disabled={processing}
            >
              {processing ? 'Processing...' : 'Approve ' + (selectedIds.size > 1 ? 'Tags' : 'Tag')}
            </button>
          </div>
        </div>
      </div>
    );
  };
  
  // Render the rejection modal
  const renderRejectionModal = () => {
    if (!showRejectionModal) return null;
    
    // Get selected normalizations
    const selectedTags = normalizations.filter(norm => selectedIds.has(norm.id));
    const title = operationType === 'single' ? 'Reject Tag' : 'Batch Reject Tags';
    
    return (
      <div className="modal">
        <div className="modal-content">
          <h2>{title}</h2>
          <p>You are about to reject {selectedIds.size} tag {selectedIds.size > 1 ? 'normalizations' : 'normalization'}.</p>
          
          {/* Show list of selected tags */}
          <div className="selected-tags-list">
            {selectedTags.map(tag => (
              <div key={tag.id} className="selected-tag">
                <span className="original-name">{tag.original_name}</span>
                <span className="arrow">→</span>
                <span className="normalized-name">{tag.normalized_name}</span>
              </div>
            ))}
          </div>
          
          <div className="form-group">
            <label>Rejection Reason:</label>
            <textarea 
              value={adminNotes} 
              onChange={(e) => setAdminNotes(e.target.value)}
              placeholder="Please provide a reason for rejection"
            />
          </div>
          
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={() => setShowRejectionModal(false)}>Cancel</button>
            <button 
              className="btn btn-danger" 
              onClick={executeBatchRejection}
              disabled={processing}
            >
              {processing ? 'Processing...' : 'Reject ' + (selectedIds.size > 1 ? 'Tags' : 'Tag')}
            </button>
          </div>
        </div>
      </div>
    );
  };
  
  return (
    <div className="tag-normalization-dashboard">
      <h1>Tag Normalization Dashboard</h1>
      
      {/* Stats Panel */}
      <div className="stats-panel">
        <div className="stat-card">
          <h3>Pending</h3>
          <p className="stat-value">{stats.pending}</p>
        </div>
        <div className="stat-card">
          <h3>Approved</h3>
          <p className="stat-value">{stats.approved}</p>
        </div>
        <div className="stat-card">
          <h3>Rejected</h3>
          <p className="stat-value">{stats.rejected}</p>
        </div>
        <div className="stat-card">
          <h3>Total</h3>
          <p className="stat-value">{stats.total}</p>
        </div>
      </div>
      
      {/* Filter Panel */}
      <div className="filter-panel">
        <div className="filter-row">
          <div className="filter-group">
            <label>Status:</label>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="modified">Modified</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Source:</label>
            <select 
              value={sourceFilter} 
              onChange={(e) => setSourceFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="ai_generated">AI Generated</option>
              <option value="user_created">User Created</option>
              <option value="admin_created">Admin Created</option>
              <option value="imported">Imported</option>
            </select>
          </div>
          
          <div className="filter-group confidence-filter">
            <label>Min Confidence:</label>
            <input 
              type="range" 
              min="0" 
              max="1" 
              step="0.1" 
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
            />
            <span>{confidenceThreshold}</span>
          </div>
        </div>
        
        <div className="filter-row">
          <div className="search-group">
            <div className="search-input-container">
              <i className="search-icon">🔍</i>
              <input 
                id="tag-search-input"
                type="text" 
                placeholder="Search all tags (Ctrl+F)..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search for tags by name"
                autoComplete="off"
              />
              {searchQuery && (
                <button 
                  className="clear-search" 
                  onClick={() => {
                    setSearchQuery('');
                    fetchNormalizations();
                  }}
                  aria-label="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Batch Actions - Only show when multiple items are selected */}
      {selectedIds.size > 1 && (
        <div className="batch-actions">
          <div className="selection-info">
            <label>
              <input 
                type="checkbox" 
                checked={selectAll} 
                onChange={toggleSelectAll} 
              />
              Select All
            </label>
            <span>{selectedIds.size} items selected</span>
          </div>
          
          <div className="action-buttons">
            <button 
              className="btn btn-primary" 
              onClick={handleBatchApprove}
            >
              Batch Approve ({selectedIds.size})
            </button>
            <button 
              className="btn btn-danger" 
              onClick={handleBatchReject}
            >
              Batch Reject ({selectedIds.size})
            </button>
          </div>
        </div>
      )}
      
      {/* Show checkbox selection UI even when no batch operations are available */}
      {selectedIds.size <= 1 && (
        <div className="selection-info">
          <label>
            <input 
              type="checkbox" 
              checked={selectAll} 
              onChange={toggleSelectAll} 
            />
            Select All
          </label>
          <span>{selectedIds.size} items selected</span>
        </div>
      )}
      
      {/* Tag List */}
      {loading ? (
        <div className="loading">Loading tag normalizations...</div>
      ) : error ? (
        <div className="error">{error}</div>
      ) : (
        <div className="tag-normalizations-table">
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Original</th>
                <th>Normalized</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {normalizations.map(norm => (
                <tr key={norm.id} className={`status-${norm.review_status}`}>
                  <td>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.has(norm.id)} 
                      onChange={() => toggleSelectItem(norm.id)} 
                    />
                  </td>
                  <td>
                    {searchQuery ? (
                      <HighlightText text={norm.original_name} highlight={searchQuery} />
                    ) : (
                      norm.original_name
                    )}
                  </td>
                  <td>
                    {searchQuery ? (
                      <HighlightText text={norm.normalized_name} highlight={searchQuery} />
                    ) : (
                      norm.normalized_name
                    )}
                  </td>
                  <td>{norm.source}</td>
                  <td>{norm.confidence_score ? norm.confidence_score.toFixed(2) : 'N/A'}</td>
                  <td>{norm.review_status}</td>
                  <td>{new Date(norm.created_at).toLocaleDateString()}</td>
                  <td className="action-buttons">
                    {norm.review_status === 'pending' && (
                      <>
                        <button 
                          className="btn btn-small btn-success" 
                          onClick={() => handleSingleApprove(norm.id)}
                        >
                          Approve
                        </button>
                        <button 
                          className="btn btn-small btn-danger" 
                          onClick={() => handleSingleReject(norm.id)}
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {norm.review_status === 'approved' && (
                      <button 
                        className="btn btn-small btn-primary" 
                        onClick={() => navigate(`/admin/tag-normalizations/${norm.id}?edit=true`)}
                      >
                        Edit & Reapprove
                      </button>
                    )}
                    <Link 
                      to={`/admin/tag-normalizations/${norm.id}`} 
                      className="btn btn-small btn-secondary"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
              {normalizations.length === 0 && (
                <tr>
                  <td colSpan="8" className="no-results">
                    {searchQuery.trim() ? 
                      `No tags matching "${searchQuery}" found` : 
                      "No tag normalizations found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Pagination */}
      <div className="pagination">
        <button 
          disabled={page === 1} 
          onClick={() => setPage(prev => Math.max(prev - 1, 1))}
        >
          Previous
        </button>
        
        <span>Page {page} of {totalPages}</span>
        
        <button 
          disabled={page === totalPages} 
          onClick={() => setPage(prev => Math.min(prev + 1, totalPages))}
        >
          Next
        </button>
        
        <select 
          value={pageSize} 
          onChange={(e) => {
            setPageSize(Number(e.target.value));
            setPage(1);
          }}
        >
          <option value={10}>10 per page</option>
          <option value={20}>20 per page</option>
          <option value={50}>50 per page</option>
          <option value={100}>100 per page</option>
        </select>
      </div>
      
      {/* Modals */}
      {renderApprovalModal()}
      {renderRejectionModal()}
    </div>
  );
};

export default TagNormalizationDashboard;
