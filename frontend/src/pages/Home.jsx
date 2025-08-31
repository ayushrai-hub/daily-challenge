import React from 'react';
import { Link } from 'react-router-dom';

function Home() {
  return (
    <div className="home-page">
      <div className="hero">
        <h1>Code Cadence</h1>
        <p className="subtitle">Improve your coding skills with daily programming challenges</p>
        
        <div className="cta-buttons">
          <Link to="/register" className="btn btn-primary">Get Started</Link>
          <Link to="/login" className="btn btn-secondary">Log In</Link>
        </div>
      </div>

      <div className="features">
        <div className="feature-card">
          <h3>Daily Problems</h3>
          <p>Receive curated coding challenges every day based on your interests and skill level.</p>
        </div>
        
        <div className="feature-card">
          <h3>Tag-Based Learning</h3>
          <p>Select from a wide range of technology tags to customize your learning journey.</p>
        </div>
        
        <div className="feature-card">
          <h3>Track Progress</h3>
          <p>Monitor your improvement over time with detailed stats and progress tracking.</p>
        </div>
      </div>
    </div>
  );
}

export default Home;
