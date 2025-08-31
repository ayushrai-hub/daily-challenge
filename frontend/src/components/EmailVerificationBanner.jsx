import React, { useState } from 'react';
import { authApi } from '../lib/api';

function EmailVerificationBanner({ email }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleResendVerification = async () => {
    try {
      setSending(true);
      setError('');
      await authApi.resendVerification();
      setSent(true);
    } catch (err) {
      console.error('Failed to resend verification email:', err);
      setError('Failed to send verification email. Please try again later.');
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <div style={{
        backgroundColor: '#d4edda',
        color: '#155724',
        padding: '15px',
        margin: '0 0 20px 0',
        borderRadius: '5px',
        border: '1px solid #c3e6cb'
      }}>
        <h4 style={{ margin: '0 0 10px 0' }}>Verification Email Sent</h4>
        <p>A new verification email has been sent to {email}. Please check your inbox and click the verification link.</p>
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#fff3cd',
      padding: '15px',
      margin: '0 0 20px 0',
      borderRadius: '5px',
      color: '#856404',
      border: '1px solid #ffeeba'
    }}>
      <h4 style={{ margin: '0 0 10px 0' }}>Email Verification Required</h4>
      <p>Your email address ({email}) needs to be verified before you can access all features.</p>
      {error && (
        <p style={{ color: '#721c24', backgroundColor: '#f8d7da', padding: '8px', borderRadius: '3px', marginTop: '10px' }}>
          {error}
        </p>
      )}
      <button
        onClick={handleResendVerification}
        disabled={sending}
        style={{
          padding: '8px 15px',
          backgroundColor: sending ? '#e0a800' : '#ffc107',
          color: '#212529',
          border: 'none',
          borderRadius: '3px',
          cursor: sending ? 'not-allowed' : 'pointer',
          fontWeight: 'bold',
          marginTop: '10px'
        }}
      >
        {sending ? 'Sending...' : 'Resend Verification Email'}
      </button>
    </div>
  );
}

export default EmailVerificationBanner;
