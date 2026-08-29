import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Monitor from "./pages/Monitor";
import History from "./pages/History";
import Alerts  from "./pages/Alerts";
import Testing from "./pages/Testing";

const App = () => (
  <div style={{ minHeight: "100vh", background: "var(--bg-base, #050c05)" }}>
    <Navbar />
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "28px 24px" }}>
      <Routes>
        <Route path="/"        element={<Monitor />} />
        <Route path="/history" element={<History />} />
        <Route path="/alerts"  element={<Alerts  />} />
        <Route path="/testing" element={<Testing />} />
      </Routes>
    </main>
  </div>
);

export default App;
