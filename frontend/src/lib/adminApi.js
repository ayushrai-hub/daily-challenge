import axios from 'axios';

// When using Vite proxy, we use a relative URL instead of the full backend URL
const API_BASE_URL = '/api';

// Create axios instance with auth token
const createAdminApiInstance = () => {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  // Add auth token to each request
  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );
  
  // Handle response errors
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      // For 404 errors in development, we'll provide mock data for frontend-first development
      if (import.meta.env.DEV && 
          error.response && 
          (error.response.status === 404 || error.response.status === 500)) {
        console.warn(`API endpoint not implemented yet: ${error.config.url}`);
        // Let individual API methods handle the fallback
        return Promise.reject({ 
          isEndpointMissing: true, 
          originalError: error,
          config: error.config
        });
      }
      
      console.error('Admin API Error:', error);
      
      // Handle unauthorized errors
      if (error.response && error.response.status === 401) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
      
      return Promise.reject(error);
    }
  );
  
  return instance;
};

// Create admin API instance
const adminApi = createAdminApiInstance();

// Admin Dashboard API
export const dashboardApi = {
  // Get admin dashboard statistics
  getStats: () => {
    return adminApi.get('/admin/dashboard/stats').catch(error => {
      console.warn('Dashboard stats endpoint not available, returning default data');
      // Return mock data if the endpoint isn't implemented yet
      return Promise.resolve({
        data: {
          tags: {
            total: 25,
            pending: 10,
            categories: 5
          },
          problems: {
            total: 30,
            pending: 8,
            published: 22
          },
          users: {
            total: 15,
            active: 12,
            admins: 2
          }
        }
      });
    });
  },
};

// Admin Tag Management API
export const tagManagementApi = {
  // Tag Normalization Endpoints
  getNormalizations: (params = {}) => {
    const { status, page, page_size, search, source, min_confidence } = params;
    
    // Build query parameters
    const queryParams = new URLSearchParams();
    if (status) queryParams.append('status', status);
    if (page) queryParams.append('page', page);
    if (page_size) queryParams.append('page_size', page_size);
    if (search) queryParams.append('search', search);
    if (source) queryParams.append('source', source);
    if (min_confidence) queryParams.append('min_confidence', min_confidence);
    
    return adminApi.get(`/admin/tag-normalizations?${queryParams.toString()}`)
      .catch(error => {
        // Check if endpoint is missing and return mock data for development
        if (error.isEndpointMissing) {
          console.warn('Tag normalizations endpoint not implemented yet, returning mock data');
          return Promise.resolve({
            data: {
              items: Array(20).fill(null).map((_, i) => ({
                id: `mock-${i}`,
                original_name: `tag-${i}`,
                normalized_name: `Tag ${i}`,
                review_status: status || ['pending', 'approved', 'rejected'][Math.floor(Math.random() * 3)],
                source: 'ai_generated',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              })),
              total: 61,
              page: parseInt(page) || 1,
              page_size: parseInt(page_size) || 20,
              pages: 4
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  getNormalizationById: (id) => {
    return adminApi.get(`/admin/tag-normalizations/${id}`)
      .catch(error => {
        // Check if endpoint is missing and return mock data for development
        if (error.isEndpointMissing) {
          console.warn('Tag normalization detail endpoint not implemented yet, returning mock data');
          return Promise.resolve({
            data: {
              id: id,
              original_name: `original-tag-${id.substring(0,4)}`,
              normalized_name: `Normalized Tag ${id.substring(0,4)}`,
              review_status: 'pending',
              source: 'ai_generated',
              confidence_score: 0.85,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              description: 'This is a mock tag normalization for development testing.'
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  updateNormalization: (id, data) => {
    return adminApi.put(`/admin/tag-normalizations/${id}`, data)
      .catch(error => {
        if (error.isEndpointMissing) {
          console.warn('Update normalization endpoint not implemented yet, returning mock success');
          return Promise.resolve({
            data: {
              id: id,
              ...data,
              updated_at: new Date().toISOString()
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  approveNormalization: (id, approvalData) => {
    return adminApi.post(`/admin/tag-normalizations/${id}/approve`, approvalData)
      .catch(error => {
        if (error.isEndpointMissing) {
          console.warn('Approve normalization endpoint not implemented yet, returning mock success');
          return Promise.resolve({
            data: {
              id: id,
              original_name: approvalData.tag_name?.toLowerCase() || `tag-${id.substring(0, 4)}`,
              normalized_name: approvalData.tag_name || `Tag ${id.substring(0, 4)}`,
              description: approvalData.description || "Approved tag description",
              review_status: "approved",
              admin_notes: approvalData.admin_notes || "",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              approved_tag_id: approvalData.existing_tag_id || `${id}-approved`,
              approved_tag: {
                id: approvalData.existing_tag_id || `${id}-approved`,
                name: approvalData.tag_name || `Tag ${id.substring(0, 4)}`,
                description: approvalData.description || "Approved tag description"
              }
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  rejectNormalization: (id, adminNotes) => {
    return adminApi.post(`/admin/tag-normalizations/${id}/reject`, { admin_notes: adminNotes })
      .catch(error => {
        if (error.isEndpointMissing) {
          console.warn('Reject normalization endpoint not implemented yet, returning mock success');
          return Promise.resolve({
            data: {
              id: id,
              review_status: "rejected",
              admin_notes: adminNotes || "Rejected during testing",
              updated_at: new Date().toISOString()
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  // Batch operations
  bulkApproveNormalizations: (approvalDataList) => {
    return adminApi.post(`/admin/tag-normalizations/bulk-approve`, approvalDataList)
      .catch(error => {
        if (error.isEndpointMissing) {
          console.warn('Bulk approve endpoint not implemented yet, returning mock success');
          return Promise.resolve({
            data: approvalDataList.map(item => ({
              id: item.normalization_id,
              original_name: item.tag_name?.toLowerCase() || `original-tag`,
              normalized_name: item.tag_name || `Normalized Tag`,
              review_status: "approved",
              admin_notes: item.admin_notes || "",
              updated_at: new Date().toISOString()
            }))
          });
        }
        return Promise.reject(error);
      });
  },
  
  bulkRejectNormalizations: (normalizationIds, adminNotes) => {
    return adminApi.post(`/admin/tag-normalizations/bulk-reject`, {
      normalization_ids: normalizationIds,
      admin_notes: adminNotes
    }).catch(error => {
      if (error.isEndpointMissing) {
        console.warn('Bulk reject endpoint not implemented yet, returning mock success');
        return Promise.resolve({
          data: normalizationIds.map(id => ({
            id,
            review_status: "rejected",
            admin_notes: adminNotes || "Batch rejected during testing",
            updated_at: new Date().toISOString()
          }))
        });
      }
      return Promise.reject(error);
    });
  },
  // Get tag normalization statistics
  getNormalizationStats: () => {
    return adminApi.get('/admin/tag-normalizations/stats')
      .catch(error => {
        // Check if endpoint is missing and return mock data for development
        if (error.isEndpointMissing) {
          console.warn('Tag normalization stats endpoint not implemented yet, returning mock data');
          return Promise.resolve({
            data: {
              total: 61,
              pending: 41,
              approved: 15,
              rejected: 5,
              auto_approved: 12
            }
          });
        }
        return Promise.reject(error);
      });
  },
  
  // Find similar tags for mapping during normalization approval
  findSimilarTags: (tagName) => {
    return adminApi.get(`/admin/tag-normalizations/similar-tags/${encodeURIComponent(tagName)}`)
      .catch(error => {
        // Check if endpoint is missing and return mock data for development
        if (error.isEndpointMissing) {
          console.warn('Similar tags endpoint not implemented yet, returning mock data');
          // Generate mock similar tags
          const tagBase = tagName.toLowerCase().replace(/\s+/g, '-');
          return Promise.resolve({
            data: [
              {
                id: `${tagBase}-1`,
                name: tagName,
                description: `${tagName} is a programming concept or tool`,
                similarity: 1.0,
                match_type: 'exact'
              },
              {
                id: `${tagBase}-2`,
                name: `${tagName}s`,
                description: `${tagName}s is the plural form of ${tagName}`,
                similarity: 0.95
              },
              {
                id: `${tagBase}-3`,
                name: `${tagName.charAt(0).toUpperCase() + tagName.slice(1)}`,
                description: `Capitalized version of ${tagName}`,
                similarity: 0.9
              },
              {
                id: `${tagBase}-4`,
                name: `${tagName} Framework`,
                description: `A framework related to ${tagName}`,
                similarity: 0.75
              }
            ]
          });
        }
        return Promise.reject(error);
      });
  },
};

// Admin Tag Hierarchy Management API
export const tagHierarchyApi = {
  // Get all tag hierarchy relationships
  getTagHierarchy: () => {
    return adminApi.get('/admin/tag-hierarchy')
      .catch(error => {
        // Check if endpoint is missing and return mock data for development
        if (error.isEndpointMissing) {
          console.warn('Tag hierarchy endpoint not implemented yet, returning mock data');
          
          // Generate mock hierarchy relationships data
          // This follows the TagHierarchy model structure in the backend
          const generateMockHierarchy = () => {
            // We'll generate relationship records based on the tags we have
            // Since we don't have direct access to the tags here, we'll generate
            // relationships with placeholder IDs that the component will need to resolve
            
            const mockRelationships = [];
            
            // Generate 20 mock relationships
            for (let i = 0; i < 20; i++) {
              const parentTagId = `tag-${Math.floor(Math.random() * 7)}`; // Random parent from first few tags
              const childTagId = `tag-${Math.floor(Math.random() * 7) + 8}`; // Random child from later tags
              
              // Only add if not a duplicate
              if (!mockRelationships.some(r => 
                r.parent_tag_id === parentTagId && r.child_tag_id === childTagId
              )) {
                mockRelationships.push({
                  parent_tag_id: parentTagId,
                  child_tag_id: childTagId,
                  relationship_type: 'parent_child'
                });
              }
            }
            
            return mockRelationships;
          };

          return Promise.resolve({
            data: generateMockHierarchy()
          });
        }
        return Promise.reject(error);
      });
  },
  
  // Create a new parent-child relationship
  createHierarchyRelationship: (parentId, childId, relationshipType = 'parent_child') => {
    return adminApi.post('/admin/tag-hierarchy', {
      parent_tag_id: parentId,
      child_tag_id: childId,
      relationship_type: relationshipType
    }).catch(error => {
      // Check if endpoint is missing and return mock response for development
      if (error.isEndpointMissing) {
        console.warn('Tag relationship creation endpoint not implemented yet, returning mock success');
        return Promise.resolve({
          data: {
            status: 'success',
            message: 'Parent-child relationship created successfully (mock)',
            relationship: {
              parent_tag_id: parentId,
              parent_name: 'Parent Tag ' + parentId,
              child_tag_id: childId,
              child_name: 'Child Tag ' + childId,
              relationship_type: relationshipType
            }
          }
        });
      }
      return Promise.reject(error);
    });
  },
  
  // Remove a parent-child relationship
  removeHierarchyRelationship: (parentId, childId) => {
    return adminApi.delete(`/admin/tag-hierarchy/${parentId}/${childId}`);
  }
};

// Admin Problem Management API
export const problemManagementApi = {
  // Get all problems with admin details
  getProblems: (params = {}) => {
    return adminApi.get('/admin/problems', { params });
  },
  
  // Get problem details
  getProblemById: (id) => {
    return adminApi.get(`/admin/problems/${id}`);
  },
  
  // Update problem status (publish, unpublish, etc.)
  updateProblemStatus: (id, status) => {
    return adminApi.put(`/admin/problems/${id}/status`, { status });
  },
  
  // Delete a problem
  deleteProblem: (id) => {
    return adminApi.delete(`/admin/problems/${id}`);
  }
};

// Admin User Management API
export const userManagementApi = {
  // Get all users with admin details
  getUsers: (params = {}) => {
    return adminApi.get('/admin/users', { params });
  },
  
  // Get user details
  getUserById: (id) => {
    return adminApi.get(`/admin/users/${id}`);
  },
  
  // Update user information
  updateUser: (id, userData) => {
    console.log(`Updating user ${id} with data:`, userData);
    return adminApi.patch(`/admin/users/${id}`, userData).catch(error => {
      // Check if endpoint is missing and return mock response for development
      if (error.isEndpointMissing) {
        console.warn('User update endpoint not implemented yet, returning mock success');
        return Promise.resolve({
          data: {
            status: 'success',
            message: 'User updated successfully (mock)',
            user: {
              id: id,
              ...userData
            }
          }
        });
      }
      return Promise.reject(error);
    });
  },
  
  // Update user status (activate, deactivate, etc.)
  updateUserStatus: (id, status) => {
    return adminApi.put(`/admin/users/${id}/status`, { status });
  },
  
  // Grant or revoke admin privileges
  setAdminStatus: (id, isAdmin) => {
    return adminApi.put(`/admin/users/${id}/admin-status`, { is_admin: isAdmin });
  }
};

export default {
  dashboardApi,
  tagManagementApi,
  tagHierarchyApi,
  problemManagementApi,
  userManagementApi
};
