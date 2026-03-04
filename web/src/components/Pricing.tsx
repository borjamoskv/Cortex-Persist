import { motion, useInView, AnimatePresence } from 'framer-motion';
import { Zap, Rocket, Check, ArrowRight, CheckCircle2, HeartHandshake } from 'lucide-react';
import { useRef, useState, useCallback } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const SUCCESS_URL = 'https://cortex-landing-2i9ficnwo-borja-moskvs-projects.vercel.app/success';

const tiers = [
  {
    name: 'Community',
    price: 'Free',
    period: 'forever',
    description: 'Full sovereign engine. Apache 2.0.',
    icon: <Zap className="w-5 h-5" />,
    accent: 'text-text-secondary',
    accentBg: 'bg-white/[0.02]',
    borderAccent: 'border-white/10',
    features: [
      'SHA-256 hash-chained ledger',
      'Local-first execution',
      'CLI + MCP Server access',
      'Privacy Shield protocols',
      'Community support',
    ],
    cta: 'Start Free',
    ctaStyle: 'bg-white/[0.05] hover:bg-white/10 text-white border border-white/10 cursor-pointer',
    featured: false,
    href: 'https://cortexpersist.com/signup',
  },
  {
    name: 'Pro',
    price: '$49',
    period: '/month',
    description: 'Automated compliance reporting.',
    icon: <Rocket className="w-5 h-5" />,
    accent: 'text-cyber-lime',
    accentBg: 'bg-cyber-lime/[0.03]',
    borderAccent: 'border-cyber-lime/20',
    features: [
      'Everything in Community',
      'Up to 1M agent calls/mo',
      'EU AI Act compliance reports',
      'Deterministic audit trails',
      'Priority support',
      'No setup fees. Cancel anytime.',
    ],
    cta: 'Start Pro Trial',
    ctaStyle: 'bg-cyber-lime text-black hover:shadow-[0_0_30px_rgba(204,255,0,0.3)] font-black',
    featured: true,
    href: `https://buy.stripe.com/test_v2x14P27s0qg4hO6oo?success_url=${SUCCESS_URL}`,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'Full verification & 24/7 support.',
    icon: <HeartHandshake className="w-5 h-5" />,
    accent: 'text-yinmn-blue',
    accentBg: 'bg-yinmn-blue/[0.03]',
    borderAccent: 'border-yinmn-blue/20',
    features: [
      'Everything in Pro',
      'Unlimited agent calls',
      'Custom deployment (VPC)',
      'On-site compliance audit',
      'SLA: 99.99% Verification',
      'Direct developer access',
    ],
    cta: 'Contact Sales',
    ctaStyle: 'bg-yinmn-blue/20 text-white border border-yinmn-blue/50 hover:bg-yinmn-blue/40 font-bold',
    featured: false,
    href: 'mailto:borja@borjamoskv.com',
  },
];

function TierCard({
  tier,
  index,
  onCopy,
}: {
  tier: typeof tiers[0];
  index: number;
  onCopy: () => void;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40, filter: 'blur(8px)' }}
      animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
      transition={{ duration: 0.7, delay: index * 0.1, ease }}
      className={`relative group ${tier.featured ? 'lg:-mt-4 lg:mb-4' : ''}`}
    >
      {tier.featured && (
        <div className="absolute -inset-px bg-gradient-to-b from-cyber-lime/30 via-cyber-lime/10 to-transparent rounded-none pointer-events-none" />
      )}

      <div
        className={`h-full glass-strong rounded-none border ${tier.borderAccent} ${tier.accentBg} p-8 relative overflow-hidden transition-all duration-500 hover:border-opacity-100 flex flex-col`}
      >
        {tier.featured && (
          <div className="absolute top-0 right-0">
            <div className="bg-cyber-lime text-black text-[9px] font-mono font-black tracking-[0.3em] uppercase px-4 py-1.5 shadow-[0_0_20px_rgba(204,255,0,0.4)]">
              RECOMMENDED
            </div>
          </div>
        )}

        <div className="mb-8">
          <div className={`w-10 h-10 rounded-none border ${tier.borderAccent} flex items-center justify-center mb-5 ${tier.accent} ${tier.accentBg}`}>
            {tier.icon}
          </div>
          <h3 className="text-lg font-bold font-mono tracking-tight mb-1">{tier.name}</h3>
          <p className="text-xs text-text-tertiary mb-5">{tier.description}</p>
          <div className="flex items-baseline gap-1">
            <span className={`text-4xl font-black tracking-tighter ${tier.featured ? 'text-cyber-lime drop-shadow-[0_0_10px_rgba(204,255,0,0.3)]' : 'text-white'}`}>
              {tier.price}
            </span>
            <span className="text-sm text-text-tertiary font-mono">{tier.period}</span>
          </div>
        </div>

        <div className={`h-px w-full ${tier.featured ? 'bg-cyber-lime/20' : 'bg-white/5'} mb-8`} />

        <ul className="space-y-3.5 mb-10 flex-1">
          {tier.features.map((feature) => (
            <li key={feature} className="flex items-start gap-3 text-sm">
              <Check className={`w-4 h-4 mt-0.5 flex-shrink-0 ${tier.accent}`} />
              <span className="text-text-secondary">{feature}</span>
            </li>
          ))}
        </ul>

        {tier.href !== '#' ? (
          <a
            href={tier.href}
            target={tier.href.startsWith('http') ? '_blank' : undefined}
            rel="noreferrer"
            className={`w-full py-4 rounded-none font-mono text-sm tracking-wide transition-all duration-300 flex items-center justify-center gap-2 group/btn ${tier.ctaStyle}`}
          >
            {tier.cta}
            <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
          </a>
        ) : (
          <button
            className={`w-full py-4 rounded-none font-mono text-sm tracking-wide transition-all duration-300 flex items-center justify-center gap-2 group/btn ${tier.ctaStyle}`}
            onClick={onCopy}
          >
            {tier.cta}
          </button>
        )}
      </div>
    </motion.div>
  );
}

export function Pricing() {
  const [showToast, setShowToast] = useState(false);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText('pip install cortex-engine');
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  }, []);

  return (
    <section id="pricing" className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      {/* Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h2 className="text-watermark text-[22vw] whitespace-nowrap">
          PRICING
        </h2>
      </div>

      {/* Central glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-cyber-lime/[0.02] rounded-[100%] blur-[200px] pointer-events-none" />

      {/* Clipboard toast */}
      <AnimatePresence>
        {showToast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2, ease }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-2.5 px-5 py-3 bg-cyber-lime text-black font-mono text-xs font-black tracking-widest uppercase shadow-[0_0_30px_rgba(204,255,0,0.4)]"
          >
            <CheckCircle2 className="w-4 h-4" />
            Copied to clipboard
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center mb-20">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Zap className="w-3.5 h-3.5" />
            Pricing
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Compliance made <br />
            <span className="text-gradient">simple.</span>
            <br />
            <span className="text-text-secondary text-3xl md:text-4xl font-medium tracking-normal">
              Fixed rate, zero friction.
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary max-w-xl mx-auto text-lg"
          >
            Start free with the open-source engine. Upgrade to Pro for automated compliance reporting and deterministic audit trails.
          </motion.p>
        </div>

        {/* Pricing Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {tiers.map((tier, idx) => (
            <TierCard key={tier.name} tier={tier} index={idx} onCopy={handleCopy} />
          ))}
        </div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.8 }}
          className="text-center text-xs text-text-tertiary font-mono mt-12 tracking-wide"
        >
          All plans include Apache 2.0 core · No vendor lock-in · Cancel anytime
        </motion.p>
      </div>
    </section>
  );
}
