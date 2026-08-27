import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import ToastContainer from './components/ToastContainer.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Forecast from './pages/Forecast.jsx';
import Disposition from './pages/Disposition.jsx';
import Manifest from './pages/Manifest.jsx';
import { useLanguage } from './context/LanguageContext.jsx';
import { NotificationProvider } from './context/NotificationContext.jsx';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { t } = useLanguage();

  return (
    <NotificationProvider>
      <div className="app-shell">
        <Header onMenuClick={() => setSidebarOpen((v) => !v)} />
        <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />

        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/disposition" element={<Disposition />} />
            <Route path="/manifest" element={<Manifest />} />
          </Routes>

          <hr className="divider" />
          <p style={{ fontSize: '0.78rem', textAlign: 'center' }}>{t('footer.disclaimer')}</p>
        </main>

        <ToastContainer />
      </div>
    </NotificationProvider>
  );
}
