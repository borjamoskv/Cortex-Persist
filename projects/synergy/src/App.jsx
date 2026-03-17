import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Heart, MessageCircle, Share2, Shield, Zap, User, Bell, Search, Home, Compass } from 'lucide-react';
import './index.css';

const PulseAvatar = ({ src, name, status = 'online' }) => (
  <div className="relative group">
    <div className={`w-16 h-16 rounded-full overflow-hidden avatar-pulse flex items-center justify-center bg-zinc-800 ${status === 'online' ? 'border-[#CCFF00]' : 'border-zinc-600'}`}>
      {src ? (
        <img src={src} alt={name} className="w-full h-full object-cover" />
      ) : (
        <User className="text-zinc-500" size={32} />
      )}
    </div>
    <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-[#0A0A0A] bg-[#CCFF00]" title={status}></div>
  </div>
);

const PostCard = ({ user, content, timestamp, image }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="glass p-6 rounded-2xl mb-8 friction-hold"
  >
    <div className="flex items-center gap-4 mb-6">
      <PulseAvatar name={user.name} src={user.avatar} />
      <div>
        <h3 className="font-bold text-lg">{user.name}</h3>
        <p className="text-zinc-500 text-sm">{user.handle} • {timestamp}</p>
      </div>
    </div>
    
    <p className="text-zinc-200 text-lg leading-relaxed mb-6">{content}</p>
    
    {image && (
      <div className="rounded-xl overflow-hidden mb-6 border border-white/5">
        <img src={image} alt="Post content" className="w-full h-auto grayscale hover:grayscale-0 transition-all duration-700" />
      </div>
    )}
    
    <div className="flex items-center justify-between pt-4 border-t border-white/5">
      <div className="flex gap-6">
        <button className="flex items-center gap-2 text-zinc-500 hover:text-[#CCFF00] transition-colors">
          <Heart size={20} /> <span className="text-sm font-medium">1.2k</span>
        </button>
        <button className="flex items-center gap-2 text-zinc-500 hover:text-[#CCFF00] transition-colors">
          <MessageCircle size={20} /> <span className="text-sm font-medium">42</span>
        </button>
      </div>
      <button className="text-zinc-500 hover:text-white transition-colors">
        <Share2 size={20} />
      </button>
    </div>
  </motion.div>
);

const EmpatheticInput = () => {
  const [text, setText] = useState('');
  const [sentiment, setSentiment] = useState('neutral'); // neutral, aggressive, kind
  
  useEffect(() => {
    // Mock sentiment analysis
    if (text.toLowerCase().includes('hate') || text.toLowerCase().includes('stupid') || text.includes('!')) {
      setSentiment('aggressive');
    } else if (text.toLowerCase().includes('love') || text.toLowerCase().includes('thanks') || text.length > 50) {
      setSentiment('kind');
    } else {
      setSentiment('neutral');
    }
  }, [text]);

  const getSentimentGlow = () => {
    if (sentiment === 'aggressive') return '0 0 20px rgba(255, 0, 64, 0.4)';
    if (sentiment === 'kind') return '0 0 20px rgba(0, 255, 128, 0.4)';
    return '0 0 20px rgba(204, 255, 0, 0.2)';
  };

  const getBorderColor = () => {
    if (sentiment === 'aggressive') return '#FF0040';
    if (sentiment === 'kind') return '#00FF80';
    return '#CCFF00';
  };

  return (
    <div className="glass p-6 rounded-3xl sticky bottom-8 w-full max-w-2xl mx-auto shadow-2xl transition-all duration-500"
         style={{ boxShadow: getSentimentGlow(), borderColor: getBorderColor() }}>
      <div className="flex items-end gap-4">
        <div className="flex-1">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Share a thoughtful perspective..."
            className="w-full bg-transparent border-none outline-none text-lg resize-none placeholder:text-zinc-700 min-h-[60px] py-2"
          />
        </div>
        <motion.button 
          whileTap={{ scale: 0.9 }}
          className={`p-4 rounded-full bg-[#CCFF00] text-black ${sentiment === 'aggressive' ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <Send size={24} />
        </motion.button>
      </div>
      
      {sentiment === 'aggressive' && (
        <motion.p 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-[#FF0040] text-xs font-bold mt-4 tracking-widest uppercase flex items-center gap-2"
        >
          <Shield size={14} /> Biological Brake: Take a breath before sending.
        </motion.p>
      )}
    </div>
  );
};

export default function App() {
  const mockPosts = [
    { 
      user: { name: 'Aria Vance', handle: '@aria.vance', avatar: null },
      content: 'The architectural shift in interface design is not just aesthetic; it’s ethical. We are rebuilding the digital commons to favor resonance over friction.',
      timestamp: '2h ago',
      image: null
    },
    { 
      user: { name: 'Kenji Tanaka', handle: '@kenji.t', avatar: null },
      content: 'Morning in the Neo-Saito district. Decelerating my consumption to match the pace of real thought.',
      timestamp: '5h ago',
      image: 'https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&q=80&w=1000'
    }
  ];

  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto pb-40">
      <header className="flex items-center justify-between mb-16 py-6 border-b border-white/5">
        <h1 className="text-3xl font-black italic tracking-tighter flex items-center gap-3">
          <Zap className="text-[#CCFF00]" fill="#CCFF00" /> SYNERGY
        </h1>
        <nav className="flex items-center gap-8">
          <Home className="text-[#CCFF00]" size={24} />
          <Compass className="text-zinc-600" size={24} />
          <Bell className="text-zinc-600" size={24} />
          <Search className="text-zinc-600" size={24} />
        </nav>
      </header>
      
      <main>
        <div className="flex items-center gap-2 mb-8 text-[#CCFF00] opacity-50">
          <div className="w-2 h-2 rounded-full bg-[#CCFF00]"></div>
          <span className="text-xs font-bold uppercase tracking-[0.3em]">Decelerated Timeline</span>
        </div>
        
        {mockPosts.map((post, i) => (
          <PostCard key={i} {...post} />
        ))}
      </main>

      <div className="fixed bottom-0 left-0 w-full p-8 pointer-events-none">
        <div className="max-w-4xl mx-auto pointer-events-auto">
          <EmpatheticInput />
        </div>
      </div>
    </div>
  );
}
