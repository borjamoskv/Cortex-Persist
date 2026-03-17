import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ReactLenis } from '@studio-freight/react-lenis';
import { Home } from './pages/Home';
import { Success } from './pages/Success';
import Audit from './pages/Audit';
import MoltbookForum from './pages/MoltbookForum';
import Pricing from './pages/Pricing';
import OracleDashboard from './pages/OracleDashboard';

function App() {
  return (
    <ReactLenis root options={{ lerp: 0.1, duration: 1.2, smoothWheel: true }}>
      <Router>
        <div className="min-h-screen bg-abyssal-900 text-white font-sans antialiased selection:bg-cyber-lime selection:text-black">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/success" element={<Success />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/foro" element={<MoltbookForum />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/oracle" element={<OracleDashboard />} />
          </Routes>
        </div>
      </Router>
    </ReactLenis>
  );
}

export default App;
