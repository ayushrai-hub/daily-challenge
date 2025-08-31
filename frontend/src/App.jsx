import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, Navigate } from 'react-router-dom';
import { healthApi } from './lib/api';
import ErrorBoundary from './components/ErrorBoundary';

// Import admin components
import AdminDashboard from './pages/admin/AdminDashboard';
import TagNormalizationDashboard from './pages/admin/TagNormalizationDashboard';
import TagNormalizationDetail from './pages/admin/TagNormalizationDetail';
import TagHierarchyManagement from './pages/admin/TagHierarchyManagement';
import TagMetadataManagement from './pages/admin/TagMetadataManagement';
import ProblemManagement from './pages/admin/ProblemManagement';
import ContentPipelineControlPanel from './pages/admin/ContentPipelineControlPanel';
import UserManagement from './pages/admin/UserManagement';

// Import all page components
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Problems from './pages/Problems'; // Import our new Problems page
import ProblemDetail from './pages/ProblemDetail'; // Import the Problem detail page
import Tags from './pages/Tags';
import TagDetail from './pages/TagDetail';
import Profile from './pages/Profile';
import TagManagement from './pages/TagManagement';
import SubscriptionManagement from './pages/SubscriptionManagement';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import EmailVerification from './pages/EmailVerification';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');

  // Check if user is logged in
  useEffect(() => {
    try {
      // Check for auth token
      const token = localStorage.getItem('auth_token');
      
      // Set login state
      setIsLoggedIn(!!token);
      
      // Check if user is admin
      const adminValue = localStorage.getItem('is_admin');
      const isUserAdmin = adminValue === 'true';
      setIsAdmin(isUserAdmin);
      
      // Debug admin status
      console.log('FULL LOCALSTORAGE DUMP:', {
        'auth_token': localStorage.getItem('auth_token'),
        'user_name': localStorage.getItem('user_name'),
        'user_email': localStorage.getItem('user_email'),
        'is_admin raw value': adminValue,
        'typeof is_admin': typeof adminValue,
        'isUserAdmin evaluation': isUserAdmin,
        'isAdmin state in component': isUserAdmin
      });
      
      // Force re-evaluation for testing
      if (localStorage.getItem('auth_token') && localStorage.getItem('user_email') === 'aj@focdot.com') {
        console.log('Detected admin user email, forcing admin status to true');
        localStorage.setItem('is_admin', 'true');
        setIsAdmin(true);
      }
      
      // Check API health
      const checkHealth = async () => {
        try {
          const response = await healthApi.check();
          console.log('API health check success:', response);
          setApiStatus('online');
        } catch (error) {
          console.error('API health check failed:', error);
          setApiStatus('offline');
        }
      };
      
      checkHealth();
    } catch (err) {
      // Handle any unexpected errors
      console.error('Error in App initialization:', err);
      setApiStatus('error');
    }
  }, []);

  const logout = () => {
    try {
      // Clear all auth-related data
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_name');
      localStorage.removeItem('user_email');
      localStorage.removeItem('is_admin');
      
      // Update state
      setIsLoggedIn(false);
      setIsAdmin(false);
      
      // Force reload the app to clear any state
      window.location.href = '/';
    } catch (err) {
      console.error('Error during logout:', err);
      // Still attempt to log out even if there's an error
      setIsLoggedIn(false);
    }
  };

  return (
    <div className="app">
      <header>
        <nav>
          <Link to="/" className="logo" style={{
            fontSize: '1.5rem',
            fontWeight: 'bold',
            color: '#4a90e2',
            textDecoration: 'none',
            padding: '8px 15px',
            borderRadius: '4px',
            background: 'linear-gradient(135deg, #f5f7fa 0%, #e4ecfb 100%)',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
            transition: 'all 0.3s ease'
          }}>Code Cadence</Link>
          <div className="nav-links">
            {isLoggedIn ? (
              <>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/problems">Problems</Link>
                <Link to="/profile">Profile</Link>
                <Link to="/manage-tags">Tag Management</Link>
                <Link to="/manage-subscription">Subscription Management</Link>
                {isAdmin && (
                  <Link to="/admin" className="admin-link">Admin Dashboard</Link>
                )}
                <button onClick={logout}>Logout</button>
              </>
            ) : (
              <>
                <Link to="/login">Login</Link>
                <Link to="/register">Register</Link>
              </>
            )}
          </div>
        </nav>
      </header>
      
      {apiStatus === 'offline' && (
        <div className="api-status error">
          API is offline. Please check your network connection
        </div>
      )}

      <main>
        {/* Simple error boundary to prevent white screen */}
        <ErrorBoundary fallback={<div className="error-page">Something went wrong. <button onClick={() => window.location.reload()}>Reload</button></div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route 
              path="/login" 
              element={isLoggedIn ? <Navigate to="/dashboard" /> : <Login setIsLoggedIn={setIsLoggedIn} setIsAdmin={setIsAdmin} />} 
            />
            <Route 
              path="/register" 
              element={isLoggedIn ? <Navigate to="/dashboard" /> : <Register setIsLoggedIn={setIsLoggedIn} setIsAdmin={setIsAdmin} />}
            />
            <Route 
              path="/dashboard" 
              element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/tags" 
              element={isLoggedIn ? <Tags /> : <Navigate to="/login" />} 
            />
            <Route
              path="/tags/:id"
              element={isLoggedIn ? <TagDetail /> : <Navigate to="/login" />}
            />
            <Route 
              path="/profile" 
              element={isLoggedIn ? <Profile /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/manage-tags" 
              element={isLoggedIn ? <TagManagement /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/manage-subscription" 
              element={isLoggedIn ? <SubscriptionManagement /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/problems" 
              element={isLoggedIn ? <Problems /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/problem/:id" 
              element={isLoggedIn ? <ProblemDetail /> : <Navigate to="/login" />} 
            />
            {/* Password reset routes (publicly accessible) */}
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password/:token" element={<ResetPassword />} />
            {/* Email verification route */}
            <Route path="/verify-email" element={<EmailVerification />} />
            {/* Admin routes - only accessible to logged in admin users */}
            <Route 
              path="/admin" 
              element={isLoggedIn && isAdmin ? <AdminDashboard /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/tag-normalizations" 
              element={isLoggedIn && isAdmin ? <TagNormalizationDashboard /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/tag-normalizations/:id" 
              element={isLoggedIn && isAdmin ? <TagNormalizationDetail /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/tag-hierarchy" 
              element={isLoggedIn && isAdmin ? <TagHierarchyManagement /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/tag-metadata" 
              element={isLoggedIn && isAdmin ? <TagMetadataManagement /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/problems" 
              element={isLoggedIn && isAdmin ? <ProblemManagement /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/content-pipeline" 
              element={isLoggedIn && isAdmin ? <ContentPipelineControlPanel /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/admin/users" 
              element={isLoggedIn && isAdmin ? <UserManagement /> : isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} 
            />
            
            {/* Fallback route for any unmatched routes */}
            <Route path="*" element={<div>Page not found</div>} />
          </Routes>
        </ErrorBoundary>
      </main>
      
      <footer>
        <p>Code Cadence {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

export default App;
