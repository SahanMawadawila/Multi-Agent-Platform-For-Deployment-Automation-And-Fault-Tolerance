"use client";

import { useState } from "react";
import { Button } from "./ui/button";
import { 
  Terminal, 
  Menu,
  X,
} from 'lucide-react';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-violet-600 rounded-lg flex items-center justify-center">
              <Terminal className="text-white" size={20} />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">Tool X</span>
          </div>
          
          <div className="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-300">
            <a href="#" className="hover:text-white transition-colors">Platform</a>
            <a href="#" className="hover:text-white transition-colors">Solutions</a>
            <a href="#" className="hover:text-white transition-colors">Docs</a>
            <a href="#" className="text-white">Pricing</a>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            <Button variant="ghost" className="h-9 px-4">Sign in</Button>
            <Button variant="default" className="h-9 px-4 bg-white text-black hover:bg-slate-200 shadow-none">
              Start Building
            </Button>
          </div>

          <div className="md:hidden">
            <button onClick={() => setIsOpen(!isOpen)} className="text-slate-300 hover:text-white">
              {isOpen ? <X /> : <Menu />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-950">
          <div className="px-4 pt-2 pb-4 space-y-1">
            <a href="#" className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800">Platform</a>
            <a href="#" className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800">Pricing</a>
            <a href="#" className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800">Sign in</a>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;