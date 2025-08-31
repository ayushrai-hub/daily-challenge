import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../lib/api';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setError('Please enter your email address');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await authApi.requestPasswordReset(email);
      
      // Always show success even if email doesn't exist (for security)
      setSuccess(true);
    } catch (err) {
      console.error('Password reset request error:', err);
      // For security, always show general message
      setSuccess(true);
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
        <h2>Password Reset Email Sent</h2>
        <p>
          If an account exists with the email <strong>{email}</strong>, you will receive 
          password reset instructions shortly.
        </p>
        <p>
          Please check your email inbox and follow the instructions to reset your password.
        </p>
        <p>
          <small>
            If you don't see the email in your inbox, please check your spam folder.
            The reset link is valid for 1 hour.
          </small>
        </p>
        <div style={{ marginTop: '20px' }}>
          <Link to="/login" style={{ 
            display: 'inline-block',
            padding: '8px 16px',
            backgroundColor: '#4A6572',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '3px'
          }}>
            Return to Login
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
      <h2>Forgot Password</h2>
      <p>Enter the email address associated with your account to receive a password reset link.</p>
      
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
          <label htmlFor="email" style={{ display: 'block', marginBottom: '5px' }}>
            Email Address
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
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
            width: '100%',
            marginBottom: '10px'
          }}
        >
          {loading ? 'Sending...' : 'Send Reset Link'}
        </button>
        
        <div style={{ textAlign: 'center', marginTop: '10px' }}>
          <Link to="/login" style={{ color: '#4A6572', textDecoration: 'none' }}>
            Return to Login
          </Link>
        </div>
      </form>
    </div>
  );
}

export default ForgotPassword;
