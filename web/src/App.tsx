import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Trigger } from './components/Trigger';
import { Engine } from './components/Engine';
import { Knockout } from './components/Knockout';
import { Footer } from './components/Footer';
import { BackgroundEffects } from './components/BackgroundEffects';

function App() {
  return (
    <div className="min-h-screen bg-abyssal-900 text-white font-sans antialiased selection:bg-cyber-lime selection:text-black">
      <BackgroundEffects />
      <Navbar />
      <main>
        <Hero />
        <Trigger />
        <Engine />
        <Knockout />
      </main>
      <Footer />
    </div>
  );
}

export default App;
