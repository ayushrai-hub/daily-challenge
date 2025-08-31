import React, { useState, useEffect } from 'react';
import { adminUserApi } from '../../lib/api';
import './admin.css';

const UserManagement = () => {
  // State for users data
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for current user being edited
  const [selectedUser, setSelectedUser] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  // State for filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [adminFilter, setAdminFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [verifiedFilter, setVerifiedFilter] = useState('');

  // State for pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Load users on component mount and when filters change
  useEffect(() => {
    fetchUsers();
  }, [page, pageSize, statusFilter, adminFilter, activeFilter, verifiedFilter]);

  // Function to fetch users with current filters
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      // Build query parameters from state
      const params = {
        page,
        page_size: pageSize,
      };

      // Add filters if they are set
      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.subscription_status = statusFilter;
      if (adminFilter !== '') params.is_admin = adminFilter === 'true';
      if (activeFilter !== '') params.is_active = activeFilter === 'true';
      if (verifiedFilter !== '') params.is_email_verified = verifiedFilter === 'true';

      const response = await adminUserApi.getUsers(params);
      setUsers(response.data);
      
      // Get total count from headers if available
      const totalCount = response.headers['x-total-count'];
      if (totalCount) {
        setTotalUsers(parseInt(totalCount, 10));
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching users:', err);
      setError('Failed to fetch users. Please try again later.');
      setLoading(false);
    }
  };

  // Function to handle search submission
  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1); // Reset to first page on new search
    fetchUsers();
  };

  // Function to reset all filters
  const resetFilters = () => {
    setSearchTerm('');
    setStatusFilter('');
    setAdminFilter('');
    setActiveFilter('');
    setVerifiedFilter('');
    setPage(1);
    // Fetch users will be triggered by the useEffect dependencies
  };

  // Function to handle toggling user admin status
  const handleToggleAdmin = async (userId, currentStatus) => {
    try {
      await adminUserApi.toggleAdminStatus(userId, !currentStatus);
      // Refresh user list after toggle
      fetchUsers();
    } catch (err) {
      console.error('Error toggling admin status:', err);
      setError('Failed to update admin status. Please try again.');
    }
  };

  // Function to handle toggling user active status
  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await adminUserApi.toggleActiveStatus(userId, !currentStatus);
      // Refresh user list after toggle
      fetchUsers();
    } catch (err) {
      console.error('Error toggling active status:', err);
      setError('Failed to update active status. Please try again.');
    }
  };

  // Function to handle user update
  const handleUpdateUser = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;

    try {
      // Only send fields that were actually changed
      const changes = {};
      if (selectedUser.full_name !== undefined) changes.full_name = selectedUser.full_name;
      // Email verification status can no longer be changed manually
      if (selectedUser.subscription_status !== undefined) changes.subscription_status = selectedUser.subscription_status;
      
      // Log the admin action for audit purposes
      console.log('Admin update for user:', selectedUser.id, 'Changes:', changes);

      await adminUserApi.updateUser(selectedUser.id, changes);
      setIsEditing(false);
      setSelectedUser(null);
      // Refresh the user list
      fetchUsers();
    } catch (err) {
      console.error('Error updating user:', err);
      setError('Failed to update user. Please try again.');
    }
  };

  // Calculate total pages for pagination
  const totalPages = Math.ceil(totalUsers / pageSize);

  return (
    <div className="admin-container">
      <h1>User Management</h1>
      <p className="description">
        Manage user accounts, permissions, and subscription status.
      </p>
      
      {/* Search and filter panel */}
      <div className="filter-panel">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-button">Search</button>
        </form>
        
        <div className="filter-controls">
          <div className="filter-group">
            <label>Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1); // Reset to first page when filter changes
              }}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="unsubscribed">Unsubscribed</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Admin:</label>
            <select
              value={adminFilter}
              onChange={(e) => {
                setAdminFilter(e.target.value);
                setPage(1); // Reset to first page when filter changes
              }}
            >
              <option value="">All Users</option>
              <option value="true">Admins Only</option>
              <option value="false">Non-Admins Only</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Status:</label>
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value);
                setPage(1); // Reset to first page when filter changes
              }}
            >
              <option value="">All Accounts</option>
              <option value="true">Active Accounts</option>
              <option value="false">Inactive Accounts</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Verification:</label>
            <select
              value={verifiedFilter}
              onChange={(e) => {
                setVerifiedFilter(e.target.value);
                setPage(1); // Reset to first page when filter changes
              }}
            >
              <option value="">All Users</option>
              <option value="true">Verified</option>
              <option value="false">Unverified</option>
            </select>
          </div>
          
          <button onClick={resetFilters} className="reset-button">
            Reset Filters
          </button>
        </div>
      </div>
      
      {/* Error message */}
      {error && <div className="error-message">{error}</div>}
      
      {/* Loading indicator */}
      {loading ? (
        <div className="loading-indicator">Loading users...</div>
      ) : (
        <>
          {/* User table */}
          {users.length > 0 ? (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Name</th>
                    <th>Admin</th>
                    <th>Active</th>
                    <th>Verified</th>
                    <th>Subscription</th>
                    <th>Created</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(user => (
                    <tr key={user.id} className={!user.is_active ? 'inactive-row' : ''}>
                      <td>{user.email}</td>
                      <td>{user.full_name || '-'}</td>
                      <td>
                        <span className={user.is_admin ? 'badge success' : 'badge neutral'}>
                          {user.is_admin ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <span className={user.is_active ? 'badge success' : 'badge danger'}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <span className={user.is_email_verified ? 'badge success' : 'badge warning'}>
                          {user.is_email_verified ? 'Verified' : 'Unverified'}
                        </span>
                      </td>
                      <td>
                        <span 
                          className="badge" 
                          style={{ backgroundColor: adminUserApi.getSubscriptionStatusColor(user.subscription_status) }}
                        >
                          {adminUserApi.getSubscriptionStatusLabel(user.subscription_status)}
                        </span>
                      </td>
                      <td>{new Date(user.created_at).toLocaleDateString()}</td>
                      <td>{user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                      <td className="actions-cell">
                        <button 
                          onClick={() => {
                            setSelectedUser(user);
                            setIsEditing(true);
                          }} 
                          className="action-button edit"
                        >
                          Edit
                        </button>
                        <button 
                          onClick={() => handleToggleAdmin(user.id, user.is_admin)} 
                          className={`action-button ${user.is_admin ? 'danger' : 'success'}`}
                        >
                          {user.is_admin ? 'Remove Admin' : 'Make Admin'}
                        </button>
                        <button 
                          onClick={() => handleToggleActive(user.id, user.is_active)} 
                          className={`action-button ${user.is_active ? 'danger' : 'success'}`}
                        >
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              No users found matching the current filters.
            </div>
          )}
          
          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => setPage(prev => Math.max(prev - 1, 1))} 
                disabled={page === 1}
                className="pagination-button"
              >
                Previous
              </button>
              
              <span className="pagination-info">
                Page {page} of {totalPages} ({totalUsers} users)
              </span>
              
              <button 
                onClick={() => setPage(prev => Math.min(prev + 1, totalPages))} 
                disabled={page === totalPages}
                className="pagination-button"
              >
                Next
              </button>
              
              <select 
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1); // Reset to page 1 when changing page size
                }}
                className="page-size-select"
              >
                <option value="10">10 per page</option>
                <option value="25">25 per page</option>
                <option value="50">50 per page</option>
                <option value="100">100 per page</option>
              </select>
            </div>
          )}
        </>
      )}
      
      {/* Edit User Modal */}
      {isEditing && selectedUser && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Edit User</h2>
            <form onSubmit={handleUpdateUser}>
              <div className="form-group">
                <label>Email:</label>
                <input type="text" value={selectedUser.email} disabled />
                <p className="field-help">Email cannot be changed</p>
              </div>
              
              <div className="form-group">
                <label>Full Name:</label>
                <input 
                  type="text" 
                  value={selectedUser.full_name || ''} 
                  onChange={(e) => setSelectedUser({...selectedUser, full_name: e.target.value})}
                />
              </div>
              
              <div className="form-group">
                <label>Email Verified:</label>
                <div className="verification-status">
                  {selectedUser.is_email_verified ? 
                    <span className="status-verified">Verified</span> : 
                    <span className="status-unverified">Not Verified</span>
                  }
                </div>
                <p className="field-help">Email verification status cannot be manually changed for security reasons</p>
                {!selectedUser.is_email_verified && (
                  <button 
                    type="button"
                    className="action-button primary small"
                    onClick={() => {
                      // This would trigger resending the verification email
                      alert('Verification email resend functionality would be implemented here');
                      console.log('Admin requested resend verification email for user:', selectedUser.id);
                    }}
                  >
                    Resend Verification Email
                  </button>
                )}
              </div>
              
              <div className="form-group">
                <label>Subscription Status:</label>
                <select 
                  value={selectedUser.subscription_status} 
                  onChange={(e) => setSelectedUser({
                    ...selectedUser, 
                    subscription_status: e.target.value
                  })}
                >
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="unsubscribed">Unsubscribed</option>
                </select>
              </div>
              
              <div className="form-actions">
                <button type="submit" className="action-button success">
                  Save Changes
                </button>
                <button 
                  type="button" 
                  className="action-button danger"
                  onClick={() => {
                    setIsEditing(false);
                    setSelectedUser(null);
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
