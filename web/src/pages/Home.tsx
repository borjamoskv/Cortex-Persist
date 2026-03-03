import { useCallback } from 'react';
import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import { Trigger } from '../components/Trigger';
import { HowItWorks } from '../components/HowItWorks';
import { Engine } from '../components/Engine';
import { Knockout } from '../components/Knockout';
import { Pricing } from '../components/Pricing';
import { SocialProof } from '../components/SocialProof';
import { Enterprise } from '../components/Enterprise';
import { Footer } from '../components/Footer';
import { BackgroundEffects } from '../components/BackgroundEffects';

export function Home() {
  const handleBuy = useCallback(() => {
    const el = document.getElementById('pricing');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, []);

  return (
    <>
      <BackgroundEffects />
      <Navbar onBuy={handleBuy} />
      <main>
        <Hero />
        <Trigger />
        <HowItWorks />
        <Engine />
        <Knockout />
        <Pricing />
        <SocialProof />
        <Enterprise />
      </main>
      <Footer />
    </>
  );
}
