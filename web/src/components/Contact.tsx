import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

export function Contact() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="contact" className="py-32 relative overflow-hidden bg-abyssal-900" ref={ref}>
      {/* Background & Effects */}
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-30" />
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyber-lime/[0.02] rounded-full blur-3xl pointer-events-none" />
      
      <div className="max-w-4xl mx-auto px-6 relative z-10 flex flex-col items-center justify-center min-h-[50vh]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, ease }}
          className="w-full"
        >
          {/* Header */}
          <div className="mb-16 text-center">
            <h2 className="text-5xl md:text-7xl font-sans font-black tracking-tighter text-white mb-4 uppercase">
              Contact
            </h2>
            <div className="font-mono text-xs tracking-[0.4em] text-cyber-lime/80 uppercase">
              Establish Secure Connection
            </div>
            {/* Subtle structural line */}
            <div className="h-px w-24 bg-white/10 mx-auto mt-8" />
          </div>

          {/* Form Area */}
          <div className="glass-strong border border-white/10 p-8 md:p-12 relative overflow-hidden group">
            {/* Corner accents */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-white/20 transition-colors group-hover:border-cyber-lime/50" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-white/20 transition-colors group-hover:border-cyber-lime/50" />

            <form className="space-y-6 relative z-10 font-sans" action="https://formspree.io/f/mqkenryp" method="POST">
              <div className="space-y-2">
                <label className="text-[10px] text-white/50 uppercase tracking-widest font-mono pl-1">Target Email</label>
                <input 
                  type="email" 
                  name="email"
                  required
                  placeholder="name@domain.com"
                  className="w-full bg-black/40 border border-white/10 px-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-cyber-lime/50 focus:ring-1 focus:ring-cyber-lime/50 transition-all font-mono text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-white/50 uppercase tracking-widest font-mono pl-1">Payload (Message)</label>
                <textarea 
                  name="message"
                  required
                  rows={4}
                  placeholder="Define your parameters..."
                  className="w-full bg-black/40 border border-white/10 px-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-cyber-lime/50 focus:ring-1 focus:ring-cyber-lime/50 transition-all font-mono text-sm resize-none"
                />
              </div>

              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                type="submit"
                className="w-full mt-4 bg-cyber-lime text-black font-mono font-black py-4 uppercase tracking-[0.2em] text-sm flex items-center justify-center gap-3 transition-colors hover:bg-white"
              >
                Transmit
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-4 h-4">
                  <path d="M8.14645 3.14645C8.34171 2.95118 8.65829 2.95118 8.85355 3.14645L12.8536 7.14645C13.0488 7.34171 13.0488 7.65829 12.8536 7.85355L8.85355 11.8536C8.65829 12.0488 8.34171 12.0488 8.14645 11.8536C7.95118 11.6583 7.95118 11.3417 8.14645 11.1464L11.2929 8H2.5C2.22386 8 2 7.77614 2 7.5C2 7.22386 2.22386 7 2.5 7H11.2929L8.14645 3.85355C7.95118 3.65829 7.95118 3.34171 8.14645 3.14645Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd"></path>
                </svg>
              </motion.button>
            </form>
          </div>

          {/* Social Links Footer */}
          <div className="mt-12 flex justify-center gap-8 font-mono text-xs tracking-widest uppercase">
            {['GitHub', 'LinkedIn', 'Email'].map((link) => (
              <a 
                key={link} 
                href="#" 
                className="text-white/40 hover:text-cyber-lime transition-colors duration-300 relative group"
              >
                {link}
                <span className="absolute -bottom-2 left-0 w-0 h-px bg-cyber-lime transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
