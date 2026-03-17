import { DocsHero } from './components/DocsHero';
import { QuickStart } from './components/QuickStart';
import { ApiReference } from './components/ApiReference';
import { Architecture } from './components/Architecture';
import { CliReference } from './components/CliReference';
import { DevFooter } from './components/DevFooter';

function App() {
  return (
    <div className="min-h-screen bg-abyssal-900 text-white font-sans antialiased selection:bg-cyber-lime selection:text-black">
      <main>
        <DocsHero />
        <QuickStart />
        <ApiReference />
        <Architecture />
        <CliReference />
      </main>
      <DevFooter />
    </div>
  );
}

export default App;
