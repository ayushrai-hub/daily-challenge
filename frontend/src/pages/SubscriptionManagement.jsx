import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { subscriptionApi, authApi } from '../lib/api';

function SubscriptionManagement() {
  const [subscription, setSubscription] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);

  // Fetch subscription data and user profile
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Fetch user subscription and user details in parallel
      const [subResponse, userResponse] = await Promise.all([
        subscriptionApi.getUserSubscription(),
        authApi.getCurrentUser()
      ]);
      
      setSubscription(subResponse.data);
      setUser(userResponse.data);
    } catch (err) {
      console.error('Error fetching subscription data:', err);
      setError('Failed to load subscription information. Please try again.');
      // Set a fallback subscription with status if available in localStorage
      const token = localStorage.getItem('auth_token');
      if (token) {
        setSubscription({
          status: 'active',
          user_id: 'unknown'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle subscription status change
  const handleStatusChange = async (action) => {
    setIsUpdating(true);
    setError('');
    setSuccess('');
    
    try {
      let response;
      
      if (action === 'pause') {
        response = await subscriptionApi.pauseSubscription();
        setSuccess('Your subscription has been paused successfully.');
      } else if (action === 'resume') {
        response = await subscriptionApi.resumeSubscription();
        setSuccess('Your subscription has been resumed successfully.');
      } else if (action === 'unsubscribe') {
        response = await subscriptionApi.updateSubscription('unsubscribed');
        setSuccess('You have been unsubscribed successfully.');
      } else if (action === 'resubscribe') {
        response = await subscriptionApi.updateSubscription('active');
        setSuccess('Your subscription has been reactivated successfully!');
      }
      
      // Update subscription state with response data
      if (response && response.data) {
        setSubscription({
          ...subscription,
          status: response.data.status
        });
      }
      
      // Refresh subscription data after a short delay to ensure backend has updated
      setTimeout(() => {
        fetchData();
      }, 1000);
    } catch (err) {
      console.error(`Error ${action}ing subscription:`, err);
      setError(`Failed to ${action} subscription: ${err.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  if (loading && !subscription && !user) {
    return (
      <div className="container">
        <div style={{padding: '20px', textAlign: 'center', marginTop: '50px'}}>
          <h2>Loading subscription information...</h2>
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

  return (
    <div className="container">
      <h1>Subscription Management</h1>
      
      {error && (
        <div style={{padding: '15px', backgroundColor: '#ffeeee', color: '#e74c3c', borderRadius: '5px', marginBottom: '20px'}}>
          {error}
        </div>
      )}
      {success && (
        <div style={{padding: '15px', backgroundColor: '#eeffee', color: '#2ecc71', borderRadius: '5px', marginBottom: '20px'}}>
          {success}
        </div>
      )}
      
      <div style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', marginBottom: '30px', backgroundColor: 'white'}}>
        <h2>Current Subscription</h2>
        {subscription ? (
          <div>
            <div style={{marginBottom: '20px'}}>
              <p>
                <strong>Status:</strong> 
                <span style={{
                  color: subscriptionApi.getStatusColor(subscription.status),
                  fontWeight: 'bold',
                  marginLeft: '5px'
                }}>
                  {subscriptionApi.getStatusLabel(subscription.status)}
                </span>
              </p>
              
              {user && (
                <p><strong>Email:</strong> {user.email}</p>
              )}
              
              <p><strong>Subscription ID:</strong> {subscription.user_id || 'N/A'}</p>
            </div>
            
            <div style={{marginTop: '20px'}}>
              {subscription.status === 'active' ? (
                <button 
                  onClick={() => handleStatusChange('pause')}
                  disabled={isUpdating}
                  style={{
                    backgroundColor: '#f39c12',
                    color: 'white',
                    border: 'none',
                    padding: '10px 15px',
                    borderRadius: '5px',
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    marginRight: '10px',
                    opacity: isUpdating ? 0.7 : 1
                  }}
                >
                  Pause Subscription
                </button>
              ) : subscription.status === 'paused' ? (
                <button 
                  onClick={() => handleStatusChange('resume')}
                  disabled={isUpdating}
                  style={{
                    backgroundColor: '#2ecc71',
                    color: 'white',
                    border: 'none',
                    padding: '10px 15px',
                    borderRadius: '5px',
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    marginRight: '10px',
                    opacity: isUpdating ? 0.7 : 1
                  }}
                >
                  Resume Subscription
                </button>
              ) : subscription.status === 'unsubscribed' ? (
                <button 
                  onClick={() => handleStatusChange('resubscribe')}
                  disabled={isUpdating}
                  style={{
                    backgroundColor: '#2ecc71',
                    color: 'white',
                    border: 'none',
                    padding: '10px 15px',
                    borderRadius: '5px',
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    marginRight: '10px',
                    opacity: isUpdating ? 0.7 : 1
                  }}
                >
                  Reactivate Subscription
                </button>
              ) : null}
              
              {subscription.status !== 'unsubscribed' && (
                <button 
                  onClick={() => handleStatusChange('unsubscribe')}
                  disabled={isUpdating}
                  style={{
                    backgroundColor: '#e74c3c',
                    color: 'white',
                    border: 'none',
                    padding: '10px 15px',
                    borderRadius: '5px',
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    opacity: isUpdating ? 0.7 : 1
                  }}
                >
                  Unsubscribe
                </button>
              )}
            </div>
          </div>
        ) : (
          <p>No active subscription found. Contact support if you believe this is an error.</p>
        )}
      </div>
      
      <div style={{border: '1px solid #e0e0e0', borderRadius: '5px', padding: '20px', marginBottom: '30px', backgroundColor: 'white'}}>
        <h2>Subscription Benefits</h2>
        <ul style={{paddingLeft: '20px'}}>
          <li>Daily coding challenges tailored to your selected tags</li>
          <li>Problem difficulty adjusted to your skill level</li>
          <li>Track your progress and build a coding streak</li>
          <li>Access to solution explanations and discussions</li>
          {subscription && subscription.status === 'active' && (
            <li style={{color: '#2ecc71', fontWeight: 'bold'}}>All benefits currently active</li>
          )}
          {subscription && subscription.status === 'paused' && (
            <li style={{color: '#f39c12', fontWeight: 'bold'}}>Benefits temporarily paused - resume to reactivate</li>
          )}
          {subscription && subscription.status === 'unsubscribed' && (
            <li style={{color: '#e74c3c', fontWeight: 'bold'}}>No active benefits - resubscribe to regain access</li>
          )}
        </ul>
      </div>
      
      <div style={{display: 'flex', gap: '10px', marginTop: '20px'}}>
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
        <Link 
          to="/dashboard" 
          style={{
            backgroundColor: '#7f8c8d',
            color: 'white',
            padding: '10px 15px',
            textDecoration: 'none',
            borderRadius: '5px',
            display: 'inline-block'
          }}
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default SubscriptionManagement;
