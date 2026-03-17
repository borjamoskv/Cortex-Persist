import { useState } from 'react';
import { motion } from 'framer-motion';
import { CreditCard, CheckCircle2, ArrowRight } from 'lucide-react';
import { BackgroundEffects } from '../components/BackgroundEffects';
import { Navbar } from '../components/Navbar';

const PLANS = [
  {
    id: 'pro',
    name: 'Sovereign Pro',
    price: '€499',
    period: '/mo',
    description: 'B2B Tactical Auditing. Up to 50,000 requests.',
    features: [
      'Access to The Oracle API',
      'Surface & Deep Scans (Depth 1-2)',
      'Ariadne & Nyx Agents',
      'Community Support',
    ],
    highlight: false,
  },
  {
    id: 'team',
    name: 'Enterprise Swarm',
    price: '€1,499',
    period: '/mo',
    description: 'Unlimited capacity for massive infrastructure audits.',
    features: [
      'Unlimited API Requests',
      'Exhaustive Topological Scans (Depth 3)',
      'All Specialized Agents (Scavenger, etc)',
      'Dedicated Sovereign Support',
      'Custom webhook integration'
    ],
    highlight: true,
  }
];

export default function Pricing() {
  const [loading, setLoading] = useState<string | null>(null);

  const handleCheckout = async (planId: string) => {
    setLoading(planId);
    try {
      // In production this points to CORTEX API /v1/stripe/checkout
      // For demo purposes we simulate the redirect
      setTimeout(() => {
        window.location.href = `/success?plan=${planId}`;
      }, 1500);
    } catch (error) {
      console.error(error);
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen selection:bg-cyber-lime selection:text-black">
      <BackgroundEffects />
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-32 relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8">
            <CreditCard className="w-3.5 h-3.5" />
            Pricing Protocol
          </div>
          <h1 className="text-5xl md:text-7xl font-sans font-black tracking-tight mb-6">
            Unlock The Oracle
          </h1>
          <p className="text-text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
            Acquire Sovereign Agent bandwidth. Instantly audit any target globally with military-grade precision.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {PLANS.map((plan) => (
            <motion.div
              key={plan.id}
              whileHover={{ y: -5 }}
              className={`glass-strong relative overflow-hidden flex flex-col ${
                plan.highlight ? 'border-cyber-lime shadow-[0_0_30px_rgba(204,255,0,0.1)]' : 'border-white/10'
              }`}
            >
              {plan.highlight && (
                <div className="absolute top-0 inset-x-0 h-1 bg-cyber-lime shadow-[0_0_20px_rgba(204,255,0,0.5)]" />
              )}
              
              <div className="p-8 border-b border-white/5">
                <h3 className="text-2xl font-black tracking-tight mb-2">{plan.name}</h3>
                <p className="text-sm text-text-secondary h-10">{plan.description}</p>
                <div className="mt-6 flex items-baseline">
                  <span className="text-5xl font-black font-mono tracking-tighter">{plan.price}</span>
                  <span className="text-text-tertiary ml-2 font-mono uppercase text-sm">{plan.period}</span>
                </div>
              </div>

              <div className="p-8 flex-1 flex flex-col">
                <ul className="space-y-4 mb-8 flex-1">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-3">
                      <CheckCircle2 className={`w-5 h-5 flex-shrink-0 ${plan.highlight ? 'text-cyber-lime' : 'text-white/40'}`} />
                      <span className="text-sm text-text-primary">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleCheckout(plan.id)}
                  disabled={!!loading}
                  className={`w-full py-4 font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-3 ${
                    plan.highlight 
                      ? 'bg-cyber-lime text-black hover:shadow-[0_0_30px_rgba(204,255,0,0.3)]' 
                      : 'bg-white/5 text-white hover:bg-white/10 border border-white/10 hover:border-white/30'
                  }`}
                >
                  {loading === plan.id ? (
                    <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      {plan.highlight ? 'Initialize Swarm' : 'Start Protocol'}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
}
