import { motion, useInView } from 'framer-motion';
import { Building2, ArrowRight, FileText, ShieldCheck, Lock, Globe } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const trustPoints = [
  { icon: <ShieldCheck className="w-5 h-5" />, label: 'EU AI Act Art. 12', detail: 'Full compliance suite' },
  { icon: <Lock className="w-5 h-5" />, label: 'SOC2 Type II', detail: 'Roadmap Q3 2026' },
  { icon: <Globe className="w-5 h-5" />, label: 'GDPR Ready', detail: 'Data sovereignty' },
];

export function Enterprise() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      {/* Gold ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] rounded-[100%] pointer-events-none bg-[image:radial-gradient(circle,rgba(212,175,55,0.02)_0%,transparent_70%)]" />

      <div className="max-w-5xl mx-auto px-6 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 40, filter: 'blur(10px)' }}
          animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
          transition={{ duration: 1, ease }}
          className="relative"
        >
          {/* Border frame */}
          <div className="absolute -inset-px bg-gradient-to-b from-industrial-gold/20 via-industrial-gold/5 to-transparent pointer-events-none" />

          <div className="glass-strong rounded-none border border-industrial-gold/15 p-12 md:p-16 relative overflow-hidden">
            {/* Corner accents */}
            <div className="absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 border-industrial-gold/40" />
            <div className="absolute top-0 right-0 w-12 h-12 border-t-2 border-r-2 border-industrial-gold/40" />
            <div className="absolute bottom-0 left-0 w-12 h-12 border-b-2 border-l-2 border-industrial-gold/40" />
            <div className="absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 border-industrial-gold/40" />

            <div className="relative z-10">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-industrial-gold bg-industrial-gold/[0.08] text-industrial-gold text-[10px] font-mono uppercase tracking-[0.3em] mb-10">
                <Building2 className="w-3.5 h-3.5" />
                Enterprise & Sovereign
              </div>

              <div className="grid lg:grid-cols-2 gap-12 items-center">
                {/* Left */}
                <div>
                  <h2 className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] leading-[0.95] mb-6">
                    Built for regulated{' '}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-industrial-gold to-white">
                      industries.
                    </span>
                  </h2>

                  <p className="text-text-secondary text-lg leading-relaxed mb-10">
                    Fintech. Healthcare. Defense. Legal. If your AI agents make high-stakes decisions,
                    CORTEX provides the cryptographic audit trail that regulators demand.
                  </p>

                  {/* CTAs */}
                  <div className="flex flex-col sm:flex-row gap-4">
                    <a
                      href="mailto:enterprise@cortexpersist.com"
                      className="group relative overflow-hidden rounded-none bg-industrial-gold/10 border border-industrial-gold/30 px-8 py-4 flex items-center justify-center gap-3 text-industrial-gold font-mono text-sm tracking-wide hover:bg-industrial-gold/20 hover:border-industrial-gold/50 transition-all"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-industrial-gold/[0.05] to-transparent -translate-x-full group-hover:animate-shimmer" />
                      <Building2 className="w-4 h-4 relative z-10" />
                      <span className="relative z-10 font-bold">Book a Demo</span>
                      <ArrowRight className="w-4 h-4 relative z-10 group-hover:translate-x-1 transition-transform" />
                    </a>

                    <a
                      href="https://cortexpersist.dev/compliance"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-2 px-6 py-4 text-text-secondary hover:text-white font-mono text-sm tracking-wide transition-colors border border-white/10 hover:border-white/20"
                    >
                      <FileText className="w-4 h-4" />
                      Read Compliance Docs
                    </a>
                  </div>
                </div>

                {/* Right — Trust Points */}
                <div className="space-y-4">
                  {trustPoints.map((point, idx) => (
                    <motion.div
                      key={point.label}
                      initial={{ opacity: 0, x: 30 }}
                      animate={isInView ? { opacity: 1, x: 0 } : {}}
                      transition={{ duration: 0.6, delay: 0.3 + idx * 0.1, ease }}
                      className="flex items-center gap-5 p-5 bg-industrial-gold/[0.03] border-l-2 border-industrial-gold/30 group hover:bg-industrial-gold/[0.06] transition-colors"
                    >
                      <div className="w-12 h-12 flex items-center justify-center border border-industrial-gold/20 text-industrial-gold bg-[#0A0A0A] group-hover:border-industrial-gold/40 transition-colors flex-shrink-0">
                        {point.icon}
                      </div>
                      <div>
                        <div className="font-bold text-white font-mono tracking-tight">{point.label}</div>
                        <div className="text-xs text-text-tertiary font-mono">{point.detail}</div>
                      </div>
                    </motion.div>
                  ))}

                  {/* Bottom stat */}
                  <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                    <span className="text-xs text-text-tertiary font-mono tracking-widest uppercase">Max penalty avoided</span>
                    <span className="text-2xl font-black text-industrial-gold font-mono tracking-tighter drop-shadow-[0_0_10px_rgba(212,175,55,0.3)]">
                      €30M
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
