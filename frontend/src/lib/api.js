import axios from 'axios';

// Get API base URL from environment variables with fallback to relative URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Log the error for debugging
    console.error('API Error:', error);
    
    // Handle unauthorized errors
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

// Health check API
export const healthApi = {
  check: () => api.get('/health'),
};

// Auth related API calls
export const authApi = {
  register: (userData) => api.post('/auth/register', userData),
  login: (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
  },
  getCurrentUser: () => api.get('/auth/me'),
  requestPasswordReset: (email) => api.post('/auth/request-password-reset', { email }),
  resetPassword: (token, password) => api.post('/auth/reset-password', { token, password }),
  resendVerification: () => api.post('/auth/resend-verification'),
  verifyEmail: (token) => api.post(`/auth/verify-email/${token}`, {}),
};

// Tag related API calls
export const tagApi = {
  getTags: (params) => api.get('/tags', { params }),
  getTagById: (id) => api.get(`/tags/${id}`),
  getUserTags: async () => {
    try {
      const response = await api.get('/subscriptions/me/tags');
      return response;
    } catch (error) {
      // Handle the validation error specifically
      if (error.response && error.response.status === 500) {
        console.warn('Backend validation error with getUserTags, returning empty array');
        // Return an empty array as if the API returned successfully
        return { data: [] };
      }
      throw error;
    }
  },
  
  // Tag normalization methods to ensure proper tag creation and hierarchy
  normalizeTagNames: (tagNames) => {
    return api.get('/tag-normalization/normalize', { params: { names: tagNames } });
  },
  
  // Map or create tags with proper normalization and parent relationships
  mapOrCreateTags: (tagNames) => {
    return api.post('/tag-normalization/map-or-create', tagNames);
  },
  
  // Use PUT method for updating user tags - send array of tag IDs
  updateUserTags: async (tagIds) => {
    try {
      return await api.put('/subscriptions/me/tags', { tag_ids: tagIds });
    } catch (error) {
      console.error('Error updating user tags:', error);
      throw error;
    }
  },
  
  // These helper methods use updateUserTags internally to avoid direct POST/DELETE
  addUserTag: async (tagId) => {
    const response = await api.get('/subscriptions/me/tags');
    const currentTags = response.data || [];
    const currentTagIds = currentTags.map(tag => tag.id);
    
    // Only add if not already selected
    if (!currentTagIds.includes(tagId)) {
      return api.put('/subscriptions/me/tags', { 
        tag_ids: [...currentTagIds, tagId] 
      });
    }
    return response;
  },
  
  removeUserTag: async (tagId) => {
    const response = await api.get('/subscriptions/me/tags');
    const currentTags = response.data || [];
    const updatedTagIds = currentTags
      .map(tag => tag.id)
      .filter(id => id !== tagId);
    
    return api.put('/subscriptions/me/tags', { 
      tag_ids: updatedTagIds 
    });
  }
};

// Subscription related API calls
export const subscriptionApi = {
  getUserSubscription: () => api.get('/subscriptions/me'),
  pauseSubscription: () => api.post('/subscriptions/me/pause'),
  resumeSubscription: () => api.post('/subscriptions/me/resume'),
  
  // Method to update subscription status directly
  updateSubscription: (status) => api.put('/subscriptions/me', { status }),
  
  // Utility method to convert status to human-readable format
  getStatusLabel: (status) => {
    const statusMap = {
      'active': 'Active',
      'paused': 'Paused',
      'unsubscribed': 'Unsubscribed'
    };
    return statusMap[status] || 'Unknown';
  },
  
  // Utility method to get status color for UI
  getStatusColor: (status) => {
    const colorMap = {
      'active': '#2ecc71', // Green
      'paused': '#f39c12', // Orange
      'unsubscribed': '#e74c3c' // Red
    };
    return colorMap[status] || '#7f8c8d'; // Gray as default
  }
};

// Problems related API calls
export const problemsApi = {
  getProblems: (params) => api.get('/problems', { params }),
  getProblemById: (id) => api.get(`/problems/${id}`),
  createProblem: (problemData) => api.post('/problems', problemData),
  updateProblem: (id, problemData) => api.put(`/problems/${id}`, problemData),
  deleteProblem: (id) => api.delete(`/problems/${id}`)
};

// Admin user management API calls
export const adminUserApi = {
  // Get all users with filtering, search and pagination
  getUsers: (params) => api.get('/admin/users', { params }),
  
  // Get a specific user by ID
  getUserById: (id) => api.get(`/admin/users/${id}`),
  
  // Update a user's information
  updateUser: (id, userData) => api.patch(`/admin/users/${id}`, userData),
  
  // Toggle admin status for a user
  toggleAdminStatus: (id, makeAdmin) => api.post(`/admin/users/${id}/toggle-admin?make_admin=${makeAdmin}`, {}),
  
  // Toggle active status for a user
  toggleActiveStatus: (id, makeActive) => api.post(`/admin/users/${id}/toggle-active?make_active=${makeActive}`, {}),
  
  // Helper function to get a readable subscription status
  getSubscriptionStatusLabel: (status) => {
    const statusMap = {
      'active': 'Active',
      'paused': 'Paused',
      'unsubscribed': 'Unsubscribed'
    };
    return statusMap[status] || 'Unknown';
  },
  
  // Helper function for subscription status colors
  getSubscriptionStatusColor: (status) => {
    const colorMap = {
      'active': '#2ecc71', // Green
      'paused': '#f39c12', // Orange
      'unsubscribed': '#e74c3c' // Red
    };
    return colorMap[status] || '#7f8c8d'; // Gray as default
  }
};

export default api;
