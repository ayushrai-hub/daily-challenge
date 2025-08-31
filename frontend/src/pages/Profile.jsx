import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { subscriptionApi } from '../lib/api';
import { Link } from 'react-router-dom';
import ChangePasswordModal from '../components/ChangePasswordModal';
import EditProfileModal from '../components/EditProfileModal';

// API base URL from environment variable or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [isEditProfileModalOpen, setIsEditProfileModalOpen] = useState(false);
  
  useEffect(() => {
    fetchUserProfile();
  }, []);
  
  async function fetchUserProfile() {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');
      
      // Use direct axios call instead of authApi
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setUser(response.data);
      
      // Also store user data in localStorage for fallback
      try {
        localStorage.setItem('user_name', response.data.full_name || response.data.name || 'User');
        localStorage.setItem('user_email', response.data.email || '');
        // Set admin status if available
        if (response.data.is_admin !== undefined) {
          localStorage.setItem('is_admin', response.data.is_admin.toString());
        }
      } catch (storageErr) {
        console.warn('Failed to store user data in localStorage:', storageErr);
      }
      
      setError('');
    } catch (err) {
      console.error('Error fetching user profile:', err);
      setError('Failed to load profile data. Please try again later.');
    } finally {
      setLoading(false);
    }
  }
  
  if (loading) {
    return (
      <div className="container">
        <div style={{padding: '20px', textAlign: 'center', marginTop: '50px'}}>
          <h2>Loading your profile...</h2>
          <div style={{width: '50px', height: '50px', border: '5px solid #f3f3f3', borderTop: '5px solid #3498db', borderRadius: '50%', margin: '20px auto', animation: 'spin 1s linear infinite'}}></div>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="container">
        <div style={{padding: '15px', backgroundColor: '#ffeeee', color: '#e74c3c', borderRadius: '5px', marginTop: '20px'}}>
          <h2>Error</h2>
          <p>{error}</p>
          <button
            onClick={fetchUserProfile}
            style={{
              padding: '8px 15px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
              marginTop: '10px'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  
  // Get the formatted subscription status
  const subscriptionStatus = subscriptionApi.getStatusLabel(user?.subscription_status || 'unsubscribed');
  const statusColor = subscriptionApi.getStatusColor(user?.subscription_status || 'unsubscribed');
  
  return (
    <div className="container">
      <h1>Your Profile</h1>
      
      <div style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', marginBottom: '30px', backgroundColor: 'white'}}>
        <div style={{display: 'flex', flexDirection: 'row', alignItems: 'center', marginBottom: '20px'}}>
          <div style={{
            width: '60px', 
            height: '60px', 
            backgroundColor: '#3498db', 
            color: 'white', 
            borderRadius: '50%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            fontSize: '24px',
            marginRight: '20px'
          }}>
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div>
            <h2 style={{margin: '0 0 5px 0'}}>{user?.full_name || 'User'}</h2>
            <p style={{margin: '0 0 5px 0', color: '#666'}}>{user?.email}</p>
            <p style={{margin: '0'}}>
              <strong>Subscription:</strong> 
              <span style={{
                color: statusColor,
                fontWeight: 'bold',
                marginLeft: '5px'
              }}>
                {subscriptionStatus}
              </span>
            </p>
          </div>
        </div>
        
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px'}}>
          <div style={{borderTop: '1px solid #eee', paddingTop: '10px'}}>
            <div style={{color: '#666', fontSize: '14px'}}>Account Created</div>
            <div>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</div>
          </div>
          
          <div style={{borderTop: '1px solid #eee', paddingTop: '10px'}}>
            <div style={{color: '#666', fontSize: '14px'}}>Last Login</div>
            <div>{user?.last_login ? new Date(user.last_login).toLocaleDateString() : 'N/A'}</div>
          </div>
          
          <div style={{borderTop: '1px solid #eee', paddingTop: '10px'}}>
            <div style={{color: '#666', fontSize: '14px'}}>Account Status</div>
            <div style={{color: user?.is_active ? '#2ecc71' : '#e74c3c', fontWeight: 'bold'}}>
              {user?.is_active ? 'Active' : 'Inactive'}
            </div>
          </div>
          
          {user?.is_admin && (
            <div style={{borderTop: '1px solid #eee', paddingTop: '10px'}}>
              <div style={{color: '#666', fontSize: '14px'}}>Admin Access</div>
              <div style={{
                display: 'inline-block', 
                backgroundColor: '#8e44ad', 
                color: 'white', 
                padding: '2px 8px', 
                borderRadius: '3px',
                fontSize: '14px'
              }}>
                Yes
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', marginBottom: '30px', backgroundColor: 'white'}}>
        <h2 style={{marginTop: '0'}}>Account Settings</h2>
        <div style={{display: 'flex', gap: '10px', flexWrap: 'wrap'}}>
          <button 
            onClick={() => setIsChangePasswordModalOpen(true)}
            style={{
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              padding: '10px 15px',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Change Password
          </button>
          <button 
            onClick={() => setIsEditProfileModalOpen(true)}
            style={{
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              padding: '10px 15px',
              borderRadius: '5px',
              cursor: 'pointer'
            }}>
            Edit Profile
          </button>
          <Link 
            to="/manage-subscription" 
            style={{
              backgroundColor: '#3498db',
              color: 'white',
              padding: '10px 15px',
              textDecoration: 'none',
              borderRadius: '5px',
              display: 'inline-block'
            }}
          >
            Manage Subscription
          </Link>
        </div>
      </div>
      
      <div style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', backgroundColor: 'white'}}>
        <h2 style={{marginTop: '0'}}>Tag Preferences</h2>
        {user?.tags && user.tags.length > 0 ? (
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px'}}>
            {user.tags.map(tag => (
              <div 
                key={tag.id} 
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: '#e3f2fd',
                  borderRadius: '15px',
                  padding: '5px 12px'
                }}
              >
                {tag.name}
              </div>
            ))}
          </div>
        ) : (
          <p style={{color: '#666'}}>No tag preferences set. Adding tags will help us personalize your daily challenges.</p>
        )}
        <Link 
          to="/manage-tags" 
          style={{
            backgroundColor: '#3498db',
            color: 'white',
            padding: '10px 15px',
            textDecoration: 'none',
            borderRadius: '5px',
            display: 'inline-block'
          }}
        >
          Manage Tags
        </Link>
      </div>

      {/* Change Password Modal */}
      <ChangePasswordModal 
        isOpen={isChangePasswordModalOpen} 
        onClose={() => setIsChangePasswordModalOpen(false)} 
      />

      {/* Edit Profile Modal */}
      <EditProfileModal 
        isOpen={isEditProfileModalOpen} 
        onClose={() => setIsEditProfileModalOpen(false)}
        user={user}
        onProfileUpdated={(updatedUser) => {
          setUser(updatedUser);
          // Also update localStorage
          localStorage.setItem('user_name', updatedUser.full_name || updatedUser.name || 'User');
        }}
      />
    </div>
  );
}

export default Profile;
