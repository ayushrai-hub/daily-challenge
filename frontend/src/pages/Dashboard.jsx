import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import EmailVerificationBanner from '../components/EmailVerificationBanner';

// API base URL from environment variable or default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function Dashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [hasAttemptedRetry, setHasAttemptedRetry] = useState(false);

  useEffect(() => {
    // Make sure we can handle errors without crashing the app
    try {
      fetchUserData();
    } catch (err) {
      console.error('Unhandled error in Dashboard component:', err);
      setError('An unexpected error occurred. Please try refreshing the page.');
      setLoading(false);
    }
  }, []);

  async function fetchUserData() {
    try {
      setLoading(true);
      // Make direct API call instead of using authApi
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Make sure we got valid user data
      if (response && response.data) {
        setUser(response.data);
        
        // Also store key user data in localStorage for fallback
        try {
          localStorage.setItem('user_name', response.data.full_name || response.data.name || 'User');
          localStorage.setItem('user_email', response.data.email || '');
          // Also store admin status if present
          if (response.data.is_admin !== undefined) {
            localStorage.setItem('is_admin', response.data.is_admin.toString());
          }
        } catch (storageErr) {
          console.warn('Failed to store user data in localStorage:', storageErr);
        }
        
        setError('');
      } else {
        throw new Error('Invalid response data');
      }
    } catch (err) {
      console.error('Error fetching user data:', err);
      
      // Check if we've already attempted to retry with the fallback
      if (!hasAttemptedRetry) {
        // Try to construct a minimal user object with data from localStorage
        const token = localStorage.getItem('auth_token');
        if (token) {
          try {
            // Create a fallback user object
            const fallbackUser = {
              name: localStorage.getItem('user_name') || 'User',
              email: localStorage.getItem('user_email') || 'user@example.com',
              full_name: localStorage.getItem('user_name') || 'User',
              subscription_status: 'active',
              tags: [],
              is_active: true
            };
            
            setUser(fallbackUser);
            setHasAttemptedRetry(true);
            setError('Some user data could not be loaded. Limited functionality available.');
          } catch (fallbackErr) {
            console.error('Error creating fallback user:', fallbackErr);
            setError('Failed to load user data. Please try logging in again.');
          }
        } else {
          // If no token, can't create fallback
          setError('Your session has expired. Please log in again.');
          // Redirect to login after a delay
          setTimeout(() => {
            window.location.href = '/login';
          }, 3000);
        }
      } else {
        setError('Failed to load user data. Please refresh the page or try again later.');
      }
    } finally {
      setLoading(false);
    }
  }

  // Function to retry loading user data
  const handleRetry = () => {
    setError('');
    fetchUserData();
  };

  if (loading) {
    return (
      <div className="container">
        <div style={{padding: '20px', textAlign: 'center', marginTop: '50px'}}>
          <h2>Loading your dashboard...</h2>
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

  if (error && !user) {
    return (
      <div className="container">
        <div style={{padding: '20px', backgroundColor: '#ffeeee', borderRadius: '5px', margin: '50px auto', maxWidth: '500px', textAlign: 'center'}}>
          <h2>Error</h2>
          <p>{error}</p>
          <button 
            onClick={handleRetry}
            style={{
              padding: '8px 15px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
              marginTop: '15px'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Display email verification banner if user exists and email is not verified */}
      {user && user.email && user.is_email_verified === false && (
        <EmailVerificationBanner email={user.email} />
      )}
      
      {error && (
        <div style={{padding: '10px', backgroundColor: '#fff3cd', color: '#856404', borderRadius: '5px', marginBottom: '15px'}}>
          {error}
        </div>
      )}
      
      <h1>Welcome, {user?.full_name || user?.name || 'User'}!</h1>
      
      <div className="dashboard-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px', marginTop: '20px'}}>
        <div className="dashboard-card" style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', backgroundColor: 'white'}}>
          <h2>Your Tags</h2>
          {user?.tags && user.tags.length > 0 ? (
            <ul className="tag-list" style={{listStyle: 'none', padding: 0}}>
              {user.tags.map(tag => (
                <li key={tag.id} style={{display: 'inline-block', margin: '3px', padding: '5px 10px', backgroundColor: '#e3f2fd', borderRadius: '15px', fontSize: '14px'}}>{tag.name}</li>
              ))}
            </ul>
          ) : (
            <p>No tags selected yet. Visit the Tags page to select your interests.</p>
          )}
          <Link 
            to="/manage-tags" 
            style={{
              display: 'inline-block',
              marginTop: '15px',
              padding: '8px 15px',
              backgroundColor: '#3498db',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '5px'
            }}
          >
            Manage Tags
          </Link>
        </div>

        <div className="dashboard-card" style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', backgroundColor: 'white'}}>
          <h2>Your Subscription</h2>
          <p>Status: <span style={{
            fontWeight: 'bold', 
            color: user?.subscription_status === 'active' ? '#2ecc71' : '#e74c3c'
          }}>
            {user?.subscription_status || 'Inactive'}
          </span></p>
          {user?.subscription_status !== 'active' && (
            <button 
              style={{
                padding: '8px 15px',
                backgroundColor: '#2ecc71',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                marginRight: '10px'
              }}
            >
              Upgrade Subscription
            </button>
          )}
          <Link 
            to="/manage-subscription" 
            style={{
              display: 'inline-block',
              marginTop: '15px',
              padding: '8px 15px',
              backgroundColor: '#3498db',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '5px'
            }}
          >
            Manage Subscription
          </Link>
        </div>

        <div className="dashboard-card" style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', backgroundColor: 'white'}}>
          <h2>Today's Challenge</h2>
          <p>Explore AI-generated coding problems with our hierarchical tag system!</p>
          <Link 
            to="/problems" 
            style={{
              display: 'inline-block',
              marginTop: '15px',
              padding: '8px 15px',
              backgroundColor: '#3498db',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '5px'
            }}
          >
            View Problems
          </Link>
        </div>
      </div>
      
      <div className="user-stats" style={{marginTop: '30px'}}>
        <h2>Your Progress</h2>
        <div className="stats-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px'}}>
          <div className="stat-card" style={{textAlign: 'center', backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '5px'}}>
            <span style={{fontSize: '32px', fontWeight: 'bold', display: 'block'}}>0</span>
            <span style={{color: '#666'}}>Problems Solved</span>
          </div>
          <div className="stat-card" style={{textAlign: 'center', backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '5px'}}>
            <span style={{fontSize: '32px', fontWeight: 'bold', display: 'block'}}>0</span>
            <span style={{color: '#666'}}>Days Streak</span>
          </div>
          <div className="stat-card" style={{textAlign: 'center', backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '5px'}}>
            <span style={{fontSize: '32px', fontWeight: 'bold', display: 'block'}}>0</span>
            <span style={{color: '#666'}}>Total Points</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
