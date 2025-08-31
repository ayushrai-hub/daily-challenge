import React from 'react';
import ReactDOM from 'react-dom/client';

// Extremely simple component for testing
function Test() {
  return <h1>Hello World</h1>;
}

// Make sure we have the root element
const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(<Test />);
} else {
  console.error('Could not find root element');
  document.body.innerHTML = '<div>Error: Could not find root element</div>';
}
