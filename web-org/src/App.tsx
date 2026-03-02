import { OrgHero } from './components/OrgHero';
import { Mission } from './components/Mission';
import { Roadmap } from './components/Roadmap';
import { GetInvolved } from './components/GetInvolved';
import { OrgFooter } from './components/OrgFooter';

function App() {
  return (
    <div className="min-h-screen bg-abyssal-900 text-white font-sans antialiased selection:bg-yinmn-blue selection:text-white">
      <main>
        <OrgHero />
        <Mission />
        <Roadmap />
        <GetInvolved />
      </main>
      <OrgFooter />
    </div>
  );
}

export default App;
