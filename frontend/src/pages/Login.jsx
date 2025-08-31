import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../lib/api';

function Login({ setIsLoggedIn, setIsAdmin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState('');
  const navigate = useNavigate();
  
  // Check if there's an existing token on component mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      console.log('Found existing token, redirecting to dashboard');
      setIsLoggedIn(true);
      navigate('/dashboard');
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setDebugInfo(null);
    setLoading(true);

    try {
      console.log('Attempting login with:', { email });
      
      const response = await authApi.login(email, password);
      console.log('Login successful, FULL response:', response);
      console.log('Login data structure:', JSON.stringify(response.data, null, 2));
      
      // Store token in localStorage
      localStorage.setItem('auth_token', response.data.access_token);
      
      // Check if email verification is required
      if (response.data.email_verification_required) {
        setVerificationRequired(true);
        setVerificationEmail(email);
        setLoading(false);
        return;
      }
      
      // Store user data directly from response
      if (response.data.is_admin !== undefined) {
        localStorage.setItem('is_admin', response.data.is_admin.toString());
        console.log('Storing admin status in localStorage:', response.data.is_admin);
      }
      
      if (response.data.email) {
        localStorage.setItem('user_email', response.data.email);
      }
      
      if (response.data.full_name) {
        localStorage.setItem('user_name', response.data.full_name);
      }
      
      // Set app state
      setIsLoggedIn(true);
      
      // Update admin state in App component
      if (setIsAdmin && response.data.is_admin !== undefined) {
        setIsAdmin(response.data.is_admin);
        console.log('Updated App component admin state to:', response.data.is_admin);
      }
      
      // Navigate to dashboard without page reload
      navigate('/dashboard');
    } catch (error) {
      console.error('Login error:', error);
      
      // Set debug info
      setDebugInfo({
        loginSuccess: false,
        errorType: error.name,
        status: error.response?.status,
        message: error.message,
        timestamp: new Date().toISOString()
      });
      
      // Set user-facing error message
      setError(
        error.response?.data?.detail || 
        'Login failed. Please check your credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Log In</h1>
      
      {error && (
        <div style={{ 
          backgroundColor: '#ffeeee', 
          padding: '10px 15px', 
          borderRadius: '5px', 
          color: '#d8000c',
          marginBottom: '20px' 
        }}>
          {error}
        </div>
      )}
      
      {verificationRequired && (
        <div style={{ 
          backgroundColor: '#fff3cd', 
          padding: '15px', 
          borderRadius: '5px', 
          color: '#856404',
          marginBottom: '20px', 
          border: '1px solid #ffeeba'
        }}>
          <h4 style={{ margin: '0 0 10px 0' }}>Email Verification Required</h4>
          <p>Your email address ({verificationEmail}) needs to be verified before you can access your account.</p>
          <button 
            onClick={async () => {
              try {
                // Store email temporarily for resend verification
                localStorage.setItem('temp_email', verificationEmail);
                
                // First login to get a token
                const loginResponse = await authApi.login(verificationEmail, password);
                localStorage.setItem('auth_token', loginResponse.data.access_token);
                
                // Then request a new verification email
                const resendResponse = await authApi.resendVerification();
                alert('Verification email has been sent. Please check your inbox.');
              } catch (e) {
                console.error('Failed to resend verification email:', e);
                alert('Failed to resend verification email. Please try again later.');
              }
            }}
            style={{
              padding: '8px 15px',
              backgroundColor: '#ffc107',
              color: '#212529',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Resend Verification Email
          </button>
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
          <div style={{ textAlign: 'right', marginTop: '5px' }}>
            <Link to="/forgot-password" style={{ fontSize: '14px', color: '#4A6572', textDecoration: 'none' }}>
              Forgot your password?
            </Link>
          </div>
        </div>
        
        <button 
          type="submit" 
          disabled={loading}
          style={{
            padding: '8px 15px',
            backgroundColor: loading ? '#cccccc' : '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Logging in...' : 'Log In'}
        </button>
      </form>
      
      {/* Show debug info for development */}
      {debugInfo && (
        <div style={{ marginTop: '20px', fontSize: '12px', color: '#777' }}>
          <details>
            <summary>Debug Information</summary>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(debugInfo, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

export default Login;
