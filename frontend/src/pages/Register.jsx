import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../lib/api';

function Register({ setIsLoggedIn, setIsAdmin }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '', // Changed from 'name' to 'full_name' to match backend schema
    subscription_status: 'active'
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Debug log to check what's being sent to the server
      console.log('Sending registration data:', formData);
      
      const response = await authApi.register(formData);
      console.log('Registration successful:', response.data);
      
      // Auto-login after registration
      const loginResponse = await authApi.login(formData.email, formData.password);
      localStorage.setItem('auth_token', loginResponse.data.access_token);
      
      // Handle admin status
      let isUserAdmin = false;
      if (loginResponse.data.is_admin !== undefined) {
        isUserAdmin = loginResponse.data.is_admin === true;
        localStorage.setItem('is_admin', isUserAdmin ? 'true' : 'false');
      }
      
      // If user data is included in the response, store full_name and email
      if (loginResponse.data.user) {
        // Store using the correct field name (full_name instead of name)
        localStorage.setItem('user_name', loginResponse.data.user.full_name || '');
        localStorage.setItem('user_email', loginResponse.data.user.email || '');
        if (loginResponse.data.user.is_admin !== undefined) {
          isUserAdmin = loginResponse.data.user.is_admin === true;
          localStorage.setItem('is_admin', isUserAdmin ? 'true' : 'false');
        }
      }
      
      // Set login state
      setIsLoggedIn(true);
      
      // Update admin state if available
      if (setIsAdmin) {
        setIsAdmin(isUserAdmin);
        console.log('Register: Updated App component admin state to:', isUserAdmin);
      }
      
      // Force page reload to ensure all state is properly synchronized
      setTimeout(() => {
        console.log('Reloading page to ensure all state is properly applied...');
        window.location.href = '/dashboard';
      }, 100);
    } catch (error) {
      console.error('Registration error:', error);
      setError(
        error.response?.data?.detail || 
        'Registration failed. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Create Account</h1>
      
      {error && <div className="error">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="full_name">Full Name</label>
          <input
            type="text"
            id="full_name"
            name="full_name"
            value={formData.full_name}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            disabled={loading}
            minLength="8"
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Creating Account...' : 'Register'}
        </button>
      </form>
    </div>
  );
}

export default Register;
