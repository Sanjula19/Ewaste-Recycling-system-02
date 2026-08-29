import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import Home from './pages/Home.jsx';
import StageDetail from './pages/StageDetail.jsx';
import History from './pages/History.jsx';
import { STAGES } from './config.js';

// Legacy paths from the previous (Step 6) shell, kept as redirects so old
// links/bookmarks still land somewhere sensible.
const LEGACY_REDIRECTS = {
  '/dashboard': '/',
  '/component1': '/detect',
  '/component2': '/protect',
  '/component3': '/process',
  '/component4': '/recover',
};

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          {STAGES.map((stage) => (
            <Route key={stage.id} path={stage.path} element={<StageDetail stage={stage} />} />
          ))}
          <Route path="/history" element={<History />} />
          {Object.entries(LEGACY_REDIRECTS).map(([from, to]) => (
            <Route key={from} path={from} element={<Navigate to={to} replace />} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
