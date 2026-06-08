import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext.jsx';
import './styles/index.css';

const savedTheme = localStorage.getItem('audit_mis_theme') || 'light';

document.documentElement.classList.remove('light', 'dark');
document.body.classList.remove('light', 'dark');

document.documentElement.classList.add(savedTheme);
document.body.classList.add(savedTheme);

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);