import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { authApi } from '../lib/api';

const EmailVerification = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('Verifying your email address...');

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link. No token provided.');
        return;
      }

      try {
        // Make POST request to verify the email
        const response = await authApi.verifyEmail(token);
        
        // Axios returns the data nested in a data property
        const responseData = response.data;
        console.log('Verification response:', responseData);
        
        // Always assume success if the request doesn't throw an error
        // This is because the backend returns 200 OK on successful verification
        setStatus('success');
        
        // Use email from response if available, otherwise use a generic message
        const email = responseData && responseData.email ? responseData.email : 'your email';
        setMessage(`${email} has been successfully verified! You'll be redirected to login shortly.`);
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login', { 
            state: { 
              message: 'Email verified successfully! Please log in.'
            }
          });
        }, 3000);
      } catch (error) {
        console.error('Email verification error:', error);
        setStatus('error');
        
        if (error.response && error.response.status === 400) {
          setMessage('This verification link is invalid or has expired. Please request a new verification email.');
        } else {
          setMessage('Failed to verify your email. Please try again or contact support.');
        }
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  return (
    <div className="container">
      <div className={`verification-card ${status}`} style={{
        maxWidth: '500px',
        width: '100%',
        margin: '0 auto',
        padding: '2rem',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        textAlign: 'center',
        borderTop: status === 'success' ? '4px solid var(--success-color)' : 
                  status === 'error' ? '4px solid var(--danger-color)' : 
                  '4px solid var(--primary-color)'
      }}>
        <h1>Email Verification</h1>
        
        {status === 'verifying' && (
          <div className="spinner" style={{
            display: 'inline-block',
            width: '50px',
            height: '50px',
            border: '3px solid rgba(0, 0, 0, 0.1)',
            borderRadius: '50%',
            borderTopColor: 'var(--primary-color)',
            animation: 'spin 1s ease-in-out infinite',
            margin: '1rem 0'
          }}></div>
        )}
        
        {status === 'success' && (
          <div className="success-icon" style={{ fontSize: '3rem', color: 'var(--success-color)', margin: '1rem 0' }}>✓</div>
        )}
        
        {status === 'error' && (
          <div className="error-icon" style={{ fontSize: '3rem', color: 'var(--danger-color)', margin: '1rem 0' }}>⚠</div>
        )}
        
        <p>{message}</p>
        
        {status === 'error' && (
          <div className="actions" style={{ marginTop: '2rem' }}>
            <button 
              onClick={() => navigate('/login')}
            >
              Go to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailVerification;
