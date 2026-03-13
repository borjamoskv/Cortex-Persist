import { motion, useInView } from 'framer-motion';
import { Github, BookOpen, MessageCircle, Tag, ArrowRight } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const channels = [
  {
    icon: <Github className="w-6 h-6" />,
    title: 'GitHub',
    description: 'Browse the source, open issues, submit PRs. Good first issues tagged for newcomers.',
    cta: 'View Repository',
    href: 'https://github.com/borjamoskv/cortex',
    accent: 'yinmn-blue',
  },
  {
    icon: <BookOpen className="w-6 h-6" />,
    title: 'Documentation',
    description: 'Comprehensive guides, API reference, tutorials, and architecture deep-dives.',
    cta: 'Read the Docs',
    href: 'https://cortexpersist.dev',
    accent: 'cyber-lime',
  },
  {
    icon: <MessageCircle className="w-6 h-6" />,
    title: 'Discussions',
    description: 'Ask questions, propose features, share your use cases with the community.',
    cta: 'Join Discussion',
    href: 'https://github.com/borjamoskv/cortex/discussions',
    accent: 'cyber-violet',
  },
  {
    icon: <Tag className="w-6 h-6" />,
    title: 'Releases',
    description: 'Stay up to date with the latest versions, changelogs, and migration guides.',
    cta: 'View Releases',
    href: 'https://github.com/borjamoskv/cortex/releases',
    accent: 'industrial-gold',
  },
];

export function GetInvolved() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] rounded-[100%] pointer-events-none bg-[image:radial-gradient(circle,rgba(46,80,144,0.03)_0%,transparent_70%)]" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-20">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-yinmn-blue bg-yinmn-blue/[0.06] text-yinmn-light text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Github className="w-3.5 h-3.5" />
            Get Involved
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Build the future of{' '}
            <span className="text-gradient-blue">AI trust.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary max-w-xl mx-auto text-lg"
          >
            Whether you're a developer, researcher, or enterprise architect—there's a place for you.
          </motion.p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          {channels.map((channel, idx) => (
            <motion.a
              key={channel.title}
              href={channel.href}
              target="_blank"
              rel="noreferrer"
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + idx * 0.1, ease }}
              className={`glass-strong rounded-none p-8 border-l-4 border-${channel.accent}/30 hover:border-${channel.accent} group transition-all duration-500 flex flex-col`}
            >
              <div className={`w-12 h-12 rounded-none border border-${channel.accent}/20 flex items-center justify-center mb-6 text-${channel.accent} bg-${channel.accent}/[0.04] group-hover:bg-${channel.accent}/[0.08] transition-colors`}>
                {channel.icon}
              </div>
              <h3 className="text-xl font-bold tracking-tight mb-3 group-hover:text-yinmn-light transition-colors">
                {channel.title}
              </h3>
              <p className="text-text-secondary text-sm leading-relaxed mb-6 flex-1">
                {channel.description}
              </p>
              <div className={`flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-${channel.accent} group-hover:gap-3 transition-all`}>
                {channel.cta}
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </section>
  );
}
