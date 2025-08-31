import React, { useState, useEffect } from 'react';
import { useParams, useLocation, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

// Direct API URL to avoid process.env reference error
const API_BASE_URL = '/api';

function ProblemDetail() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [problem, setProblem] = useState(location.state?.problem || null);
  const [loading, setLoading] = useState(!problem);
  const [error, setError] = useState('');

  useEffect(() => {
    // If we don't have the problem data from location state, fetch it
    if (!problem) {
      fetchProblem();
    } else {
      console.log('Using problem data from navigation state:', problem);
    }
  }, [id]);

  const fetchProblem = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/problems/${id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      setProblem(response.data);
      setError('');
    } catch (err) {
      console.error('Error fetching problem details:', err);
      setError('Failed to load problem details. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  // Format the difficulty level for display
  const formatDifficulty = (level) => {
    if (!level) return '';
    return level.charAt(0).toUpperCase() + level.slice(1).toLowerCase();
  };
  
  // Get color for difficulty badge
  const getDifficultyColor = (level) => {
    switch(level?.toLowerCase()) {
      case 'easy': return '#2ecc71';
      case 'medium': return '#f39c12';
      case 'hard': return '#e74c3c';
      default: return '#95a5a6';
    }
  };

  // Render tag with appropriate color
  const renderTag = (tag) => {
    return (
      <span 
        key={tag.id || tag.name} 
        style={{
          display: 'inline-block',
          padding: '4px 10px',
          margin: '0 5px 5px 0',
          backgroundColor: '#3498db',
          color: 'white',
          borderRadius: '12px',
          fontSize: '14px'
        }}
      >
        {tag.name}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '50px 0' }}>
        <h2>Loading problem...</h2>
      </div>
    );
  }

  if (error || !problem) {
    return (
      <div className="container" style={{ textAlign: 'center', padding: '50px 0' }}>
        <h2>{error || 'Problem not found'}</h2>
        <button 
          onClick={() => navigate('/problems')}
          style={{
            marginTop: '15px',
            padding: '8px 15px',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: 'pointer'
          }}
        >
          Back to Problems
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px' 
      }}>
        <h1>{problem.title}</h1>
        <span
          style={{
            display: 'inline-block',
            padding: '5px 15px',
            backgroundColor: getDifficultyColor(problem.difficulty_level),
            color: 'white',
            borderRadius: '15px',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {formatDifficulty(problem.difficulty_level)}
        </span>
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        {problem.tags && problem.tags.map(tag => renderTag(tag))}
      </div>
      
      <div style={{ 
        backgroundColor: 'white', 
        padding: '20px', 
        borderRadius: '5px',
        border: '1px solid #e0e0e0',
        marginBottom: '20px'
      }}>
        <h2>Problem Description</h2>
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {problem.description}
        </div>
      </div>
      
      {problem.example_input && problem.example_output && (
        <div style={{ 
          backgroundColor: 'white', 
          padding: '20px', 
          borderRadius: '5px',
          border: '1px solid #e0e0e0',
          marginBottom: '20px'
        }}>
          <h2>Examples</h2>
          <div>
            <h3>Input:</h3>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '3px',
              overflow: 'auto'
            }}>
              {problem.example_input}
            </pre>
            
            <h3>Output:</h3>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '3px',
              overflow: 'auto'
            }}>
              {problem.example_output}
            </pre>
          </div>
        </div>
      )}
      
      {problem.constraints && (
        <div style={{ 
          backgroundColor: 'white', 
          padding: '20px', 
          borderRadius: '5px',
          border: '1px solid #e0e0e0',
          marginBottom: '20px'
        }}>
          <h2>Constraints</h2>
          <div style={{ whiteSpace: 'pre-wrap' }}>
            {problem.constraints}
          </div>
        </div>
      )}
      
      <button
        onClick={() => navigate('/problems')}
        style={{
          marginTop: '15px',
          padding: '8px 15px',
          backgroundColor: '#3498db',
          color: 'white',
          border: 'none',
          borderRadius: '3px',
          cursor: 'pointer'
        }}
      >
        Back to Problems
      </button>
    </div>
  );
}

export default ProblemDetail;
