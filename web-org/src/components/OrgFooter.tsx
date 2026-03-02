import { Shield, Github, FileText } from 'lucide-react';

export function OrgFooter() {
  return (
    <footer className="border-t border-white/5 bg-abyssal-800/50 backdrop-blur-xl relative z-10">
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo */}
          <div className="flex items-center gap-2.5 font-mono text-sm">
            <Shield className="w-4 h-4 text-yinmn-light" />
            <span className="font-bold">CORTEX</span>
            <span className="text-text-tertiary">persist</span>
            <span className="mx-2 text-text-tertiary">·</span>
            <span className="text-yinmn-light text-xs font-mono">Open Trust Standard</span>
          </div>

          {/* Domain links */}
          <div className="flex gap-4 text-sm font-mono">
            <a href="https://cortexpersist.com" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-cyber-lime transition-colors flex items-center gap-1.5 px-3 py-1 bg-white/[0.03] border border-white/5">
              .com
            </a>
            <a href="https://cortexpersist.dev" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-white transition-colors flex items-center gap-1.5 px-3 py-1 bg-white/[0.03] border border-white/5">
              <FileText className="w-3.5 h-3.5" /> .dev
            </a>
            <a href="https://github.com/borjamoskv/cortex" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-white transition-colors flex items-center gap-1.5 px-3 py-1 bg-white/[0.03] border border-white/5">
              <Github className="w-3.5 h-3.5" /> GitHub
            </a>
          </div>

          {/* Copyright */}
          <div className="text-xs text-text-tertiary font-mono">
            © 2026 MOSKV-1 SOVEREIGN SYSTEMS · Apache 2.0
          </div>
        </div>
      </div>
    </footer>
  );
}
