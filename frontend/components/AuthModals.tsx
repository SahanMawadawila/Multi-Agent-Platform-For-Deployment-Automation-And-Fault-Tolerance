"use client"
import { useSession, signIn, signOut } from "next-auth/react"
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Chrome, Github, Mail, UserPlus, LogIn, X } from 'lucide-react';

// Simple Input component for the hidden form, styled to match the dark theme
const Input = ({ ...props }: React.ComponentProps<'input'>) => (
  <input 
    className="w-full bg-slate-800 border border-slate-700 rounded-md p-2 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-colors outline-none" 
    {...props} 
  />
);

type AuthModalProps = {
  isOpen: boolean;
  onClose: () => void;
  initialView: 'signin' | 'signup';
};

const AuthModals: React.FC<AuthModalProps> = ({ isOpen, onClose, initialView }) => {
  const { data: session } = useSession()
  const [view, setView] = useState(initialView);

  if (!isOpen) return null;

  const isSignIn = view === 'signin';
  const title = isSignIn ? 'Sign In to Tool X' : 'Create an Account';
  const socialTitle = isSignIn ? 'Sign in with your favorite provider' : 'Sign up with your favorite provider';
  const icon = isSignIn ? <LogIn size={20} /> : <UserPlus size={20} />;
  
  // Hidden Email/Password Form
  const EmailPasswordForm = ({ submitLabel, hidden }: { submitLabel: string, hidden: boolean }) => (
    <form className={`space-y-4 ${hidden ? 'hidden' : ''}`}>
      <Input type="email" placeholder="Email" />
      <Input type="password" placeholder="Password" />
      {/* Hidden email/password option for future use */}
      <Button className="w-full h-10 px-4 text-base bg-violet-600 hover:bg-violet-500" type="submit">
        {submitLabel}
      </Button>
    </form>
  );

  return (
    // Backdrop
    <div 
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 transition-opacity"
      onClick={onClose}
    >
      {/* Modal Card */}
      <div 
        className="bg-slate-900 border border-slate-800 rounded-xl p-8 w-full max-w-sm shadow-2xl animate-in fade-in zoom-in-95"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal
      >
        <div className="flex justify-between items-start mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            {icon}
            {title}
          </h2>
          <Button variant="ghost" size="icon-sm" onClick={onClose} className="text-slate-400 hover:text-white hover:bg-transparent  cursor-pointer">
            <X size={20} />
          </Button>
        </div>

        <p className="text-slate-400 text-sm mb-6">{socialTitle}</p>
        
        <div className="space-y-3">
          {/* Social Login Buttons */}
          <Button 
            onClick={() => signIn("google")}
            variant="outline" 
            className="w-full h-10 text-base bg-slate-800 border-slate-700 hover:bg-slate-700 text-white cursor-pointer"
          >
            <Chrome className="mr-2" size={18} />
            {isSignIn ? 'Sign in with Google' : 'Sign up with Google'}
          </Button>
          <Button 
            onClick={() => signIn("github")}
            variant="outline" 
            className="w-full h-10 text-base bg-slate-800 border-slate-700 hover:bg-slate-700 text-white cursor-pointer"
          >
            <Github className="mr-2" size={18} />
            {isSignIn ? 'Sign in with GitHub' : 'Sign up with GitHub'}
          </Button>
        </div>

        {/* Separator and Hidden Form */}
        <div className="mt-6 space-y-4">
          <div className="flex items-center">
            <div className="flex-grow border-t border-slate-800" />
            <span className="shrink-0 px-4 text-xs font-medium uppercase text-slate-500">
              {/*isSignIn ? 'Or hidden email login' : 'Or hidden email signup'*/}
              OR
            </span>
            <div className="flex-grow border-t border-slate-800" />
          </div>

          <EmailPasswordForm 
            submitLabel={isSignIn ? 'Sign In (Hidden)' : 'Sign Up (Hidden)'}
            hidden={true} // Keep this form hidden as requested
          />
        </div>

        {/* Switch View Link */}
        <p className="mt-6 text-center text-sm text-slate-400">
          {isSignIn ? "Don't have an account?" : "Already have an account?"}
          <button 
            onClick={() => setView(isSignIn ? 'signup' : 'signin')}
            className="text-violet-400 hover:text-violet-300 ml-1 font-medium transition-colors"
          >
            {isSignIn ? 'Sign Up' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default AuthModals;