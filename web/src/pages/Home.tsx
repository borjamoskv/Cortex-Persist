import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import PanoramicOuroboros from '../components/PanoramicOuroboros';
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

  return (
    <>
      <BackgroundEffects />
      <Navbar />
      <main>
        <Hero />
        <PanoramicOuroboros />
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
