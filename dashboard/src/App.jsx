import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import Home from './pages/Home.jsx';
import ComponentDetail from './pages/ComponentDetail.jsx';
import { COMPONENTS } from './config.js';

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Home />} />
          {COMPONENTS.map((c) => (
            <Route key={c.id} path={c.path} element={<ComponentDetail component={c} />} />
          ))}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
