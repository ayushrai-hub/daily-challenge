import React, { useState, useEffect } from 'react';
import axios from 'axios';

// API base URL from environment variable or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function EditProfileModal({ isOpen, onClose, user, onProfileUpdated }) {
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Initialize form fields with current user data when modal is opened
  useEffect(() => {
    if (isOpen && user) {
      setFullName(user.full_name || '');
      setError('');
      setSuccess('');
    }
  }, [isOpen, user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Form validation - fullName is the only field that needs validation for now
    if (!fullName.trim()) {
      setError('Full name cannot be empty');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const token = localStorage.getItem('auth_token');
      
      // Send request to update profile
      const response = await axios.put(
        `${API_BASE_URL}/profile`,
        {
          full_name: fullName
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      setSuccess('Profile updated successfully');
      
      // Call callback function to update parent component's state
      if (onProfileUpdated) {
        onProfileUpdated(response.data);
      }
      
      // Close modal after delay
      setTimeout(() => {
        onClose();
        setSuccess('');
      }, 2000);
      
    } catch (err) {
      console.error('Error updating profile:', err);
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to update profile. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="modal-content" style={{
        backgroundColor: 'white',
        padding: '25px',
        borderRadius: '5px',
        maxWidth: '500px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0 }}>Edit Profile</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer'
            }}
          >
            &times;
          </button>
        </div>

        {error && (
          <div style={{
            padding: '10px',
            marginBottom: '15px',
            backgroundColor: '#ffeeee',
            color: '#e74c3c',
            borderRadius: '3px'
          }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{
            padding: '10px',
            marginBottom: '15px',
            backgroundColor: '#eeffee',
            color: '#2ecc71',
            borderRadius: '3px'
          }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '15px' }}>
            <label htmlFor="full-name" style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Full Name
            </label>
            <input
              id="full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '3px',
                border: '1px solid #ddd'
              }}
              disabled={loading}
            />
          </div>



          <button
            type="submit"
            disabled={loading}
            style={{
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              padding: '10px 15px',
              borderRadius: '5px',
              cursor: loading ? 'not-allowed' : 'pointer',
              width: '100%'
            }}
          >
            {loading ? 'Updating Profile...' : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default EditProfileModal;
