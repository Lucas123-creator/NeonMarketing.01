import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';

const App: React.FC = () => (
  <Router>
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 shadow mb-6">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/dashboard" className="text-xl font-bold text-blue-600">NeonHub Dashboard</Link>
          <div className="space-x-4">
            <Link to="/dashboard" className="hover:underline">Dashboard</Link>
            {/* Add more nav links as needed */}
          </div>
        </div>
      </nav>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </div>
  </Router>
);

export default App;
