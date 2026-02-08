"use client";

import { useCallback, useState } from "react";
import {
  Terminal,
  User,
  Settings,
  CreditCard,
  Layers,
  LogOut,
  ChevronDown
} from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { signOut, useSession } from "next-auth/react";
import Link from "next/link";

const DashboardNavbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { data } = useSession();

  const handleLogOut = useCallback(() => {
    void signOut({ callbackUrl: "/" });
  }, []);
  return (
    <nav className="sticky top-0 w-full z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className=" w-full max-w-[1640px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / Title */}
          <Link href={'/dashboard'} >
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 bg-violet-600 rounded-lg flex items-center justify-center">
                <Terminal className="text-white" size={20} />
              </div>
              <span className="font-bold text-xl tracking-tight text-white">FlowPilot</span>
            </div>
          </Link>

          <div className="flex items-center gap-4">
            Hello! {data?.user?.name}
          </div>

          {/* User Profile and Dropdown */}
          <div className="relative">
            <Popover open={isMenuOpen} onOpenChange={setIsMenuOpen}>
              <PopoverTrigger>
                <Button
                  variant="ghost"
                  size="icon"

                  asChild={true}
                >
                  <div className="rounded-full h-10 w-10  hover:bg-transparent text-white p-0 hover:text-violet-300">
                    <User size={20} />
                    <ChevronDown size={16} className={`ml-1 transition-transform ${isMenuOpen ? 'rotate-180' : 'rotate-0'}`} />
                  </div>
                </Button>
              </PopoverTrigger>
              <PopoverContent className="bg-transparent p-0 border-0 w-auto" align="end" side="bottom">
                <Card
                  className="mt-0 w-56 p-2 rounded-xl border border-slate-700 bg-slate-900 shadow-xl text-sm z-50 animate-in fade-in slide-in-from-top-1"
                  data-slot="card" // Use Card for styling, but override gap/padding
                >
                  <div className="flex flex-col gap-1">
                    <div className="p-2 text-white font-semibold border-b border-slate-800 mb-1">
                      User Options
                    </div>

                    <a href="/dashboard/projects" className="flex items-center gap-3 p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-violet-400 transition-all duration-150 ease-out hover:translate-x-1">
                      <Layers size={16} /> My projects
                    </a>
                    <a href="/dashboard/billing" className="flex items-center gap-3 p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-violet-400 transition-all duration-150 ease-out hover:translate-x-1">
                      <CreditCard size={16} /> Billing & Subscription
                    </a>
                    <a href="/dashboard/settings" className="flex items-center gap-3 p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-violet-400 transition-all duration-150 ease-out hover:translate-x-1">
                      <Settings size={16} /> Account Options
                    </a>
                    <div className="border-t border-slate-800 mt-1 pt-1">
                      <button
                        onClick={handleLogOut}
                        className="flex items-center w-full gap-3 p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-red-400 transition-all duration-150 ease-out hover:translate-x-1"
                      >
                        <LogOut size={16} /> Logout
                      </button>
                    </div>
                  </div>
                </Card>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default DashboardNavbar;