"use client";

import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { 
  Terminal, 
  Menu,
  X,
} from 'lucide-react';
import AuthModals from './AuthModals';
import { OPEN_SIGNUP_MODAL_EVENT } from "@/lib/frontend-events";


const Navbar = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  // New state for Auth Modals
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authView, setAuthView] = useState<'signin' | 'signup'>('signin');

  const openModal = (view: 'signin' | 'signup') => {
    setAuthView(view);
    setIsAuthModalOpen(true);
    setIsMobileMenuOpen(false); // Close mobile menu when opening modal
  };

  const closeModal = () => {
    setIsAuthModalOpen(false);
  };

  // Add useEffect to listen for the custom event
  useEffect(() => {
    const handleOpenSignup = () => {
      openModal('signup');
    };

    // Listen on the window object for events dispatched from anywhere in the document
    window.addEventListener(OPEN_SIGNUP_MODAL_EVENT, handleOpenSignup);

    // Cleanup function
    return () => {
      window.removeEventListener(OPEN_SIGNUP_MODAL_EVENT, handleOpenSignup);
    };
  }, []); // Empty dependency array ensures this runs once on mount

  return (
    <>
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
              <a href="/docs" className="hover:text-white transition-colors">Docs</a>
              <a href="/#pricing" className="text-white">Pricing</a>
            </div>

            <div className="hidden md:flex items-center space-x-4">
              <Button 
                variant="ghost" 
                className="h-9 px-4"
                onClick={() => openModal('signin')} // Open Sign In modal
              >
                Sign in
              </Button>
              <Button 
                variant="default" 
                className="h-9 px-4 bg-white text-black hover:bg-slate-200 shadow-none"
                onClick={() => openModal('signup')} // Open Sign Up modal
              >
                Start Building
              </Button>
            </div>

            <div className="md:hidden">
              <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="text-slate-300 hover:text-white">
                {isMobileMenuOpen ? <X /> : <Menu />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-slate-800 bg-slate-950">
            <div className="px-4 pt-2 pb-4 space-y-1">
              <a href="#" className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800">Platform</a>
              <a href="#" className="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800">Pricing</a>
              {/* Mobile Sign In button, opens modal */}
              <button
                className="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
                onClick={() => openModal('signin')}
              >
                Sign in
              </button>
            </div>
          </div>
        )}
      </nav>
      {/* Auth Modals */}
      <AuthModals 
        isOpen={isAuthModalOpen} 
        onClose={closeModal} 
        initialView={authView}
      />
    </>
  );
};

export default Navbar;