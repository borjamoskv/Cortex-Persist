import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { Success } from './pages/Success';
import Audit from './pages/Audit';
import MoltbookForum from './pages/MoltbookForum';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-abyssal-900 text-white font-sans antialiased selection:bg-cyber-lime selection:text-black">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/success" element={<Success />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/foro" element={<MoltbookForum />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
