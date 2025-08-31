import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { authApi } from '../lib/api';

function ResetPassword() {
  const { token } = useParams(); // Get token from URL
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  // Password validation
  const validatePassword = (password) => {
    if (password.length < 8) {
      return 'Password must be at least 8 characters long';
    }
    return '';
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Reset any previous errors
    setError('');
    
    // Validate passwords
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setLoading(true);
    
    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
      
      // Auto redirect to login after 5 seconds
      setTimeout(() => {
        navigate('/login');
      }, 5000);
    } catch (err) {
      console.error('Password reset error:', err);
      
      if (err.response?.status === 400) {
        setError('This password reset link is invalid or has expired. Please request a new one.');
      } else {
        setError('An error occurred. Please try again or request a new reset link.');
      }
    } finally {
      setLoading(false);
    }
  };
  
  if (success) {
    return (
      <div style={{ 
        maxWidth: '400px',
        margin: '40px auto',
        padding: '20px',
        borderRadius: '5px',
        boxShadow: '0 0 10px rgba(0,0,0,0.1)',
        backgroundColor: 'white'
      }}>
        <div style={{
          padding: '10px',
          backgroundColor: '#dff0d8',
          color: '#3c763d',
          borderRadius: '3px',
          marginBottom: '15px',
          textAlign: 'center'
        }}>
          <h3>Password Reset Successful!</h3>
        </div>
        
        <p>Your password has been successfully reset. You can now login with your new password.</p>
        
        <p>You will be automatically redirected to the login page in 5 seconds...</p>
        
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Link 
            to="/login" 
            style={{
              display: 'inline-block',
              padding: '8px 16px',
              backgroundColor: '#4A6572',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '3px'
            }}
          >
            Login Now
          </Link>
        </div>
      </div>
    );
  }
  
  return (
    <div style={{ 
      maxWidth: '400px',
      margin: '40px auto',
      padding: '20px',
      borderRadius: '5px',
      boxShadow: '0 0 10px rgba(0,0,0,0.1)',
      backgroundColor: 'white'
    }}>
      <h2>Reset Your Password</h2>
      <p>Please enter and confirm your new password below.</p>
      
      {error && (
        <div style={{
          padding: '10px',
          backgroundColor: '#ffdddd',
          color: '#ff0000',
          borderRadius: '3px',
          marginBottom: '15px'
        }}>
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label htmlFor="password" style={{ display: 'block', marginBottom: '5px' }}>
            New Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter new password"
            required
            minLength="8"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ddd',
              borderRadius: '3px'
            }}
            disabled={loading}
          />
        </div>
        
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="confirmPassword" style={{ display: 'block', marginBottom: '5px' }}>
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            required
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ddd',
              borderRadius: '3px'
            }}
            disabled={loading}
          />
        </div>
        
        <button 
          type="submit" 
          disabled={loading}
          style={{
            backgroundColor: '#4A6572',
            color: 'white',
            padding: '10px 15px',
            border: 'none',
            borderRadius: '3px',
            cursor: loading ? 'not-allowed' : 'pointer',
            width: '100%'
          }}
        >
          {loading ? 'Resetting Password...' : 'Reset Password'}
        </button>
      </form>
      
      <div style={{ textAlign: 'center', marginTop: '15px' }}>
        <Link to="/forgot-password" style={{ color: '#4A6572', textDecoration: 'none' }}>
          Request a new reset link
        </Link>
      </div>
    </div>
  );
}

export default ResetPassword;
