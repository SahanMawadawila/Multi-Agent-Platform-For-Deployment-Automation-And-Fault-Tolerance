import { 
  GitBranch, 
  Activity, 
  ShieldAlert, 
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import FeatureItem from '@/components/custom-ui/FeatureItem';

export default function Home() {
  return (
  <>
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden">
        {/* Background Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_110%)]" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <Badge>Multi-Agent DevOps Platform</Badge>
          <h1 className="mt-8 text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight text-white">
            Deploy with <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-purple-600">Intelligent Agents</span>.
            <br className="hidden md:block" /> Scale Infinitely.
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-lg md:text-xl text-slate-400">
            From simple apps to complex microservices. Our autonomous agents handle 
            version control, CI/CD, monitoring, and fault tolerance for you.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Button className="h-12 px-8 text-base">Start Deploying Now</Button>
            <Button variant="secondary" className="h-12 px-8 text-base">Read Documentation</Button>
          </div>
        </div>

        {/* Abstract Visualization (Graph Line) */}
        <div className="mt-20 relative max-w-5xl mx-auto h-64 opacity-50">
           <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-slate-800" />
           <div className="absolute bottom-0 left-10 w-20 h-20 border-l border-t border-violet-500/50" />
           <div className="absolute bottom-20 left-30 w-32 h-32 border-r border-t border-purple-500/50" />
           <div className="absolute bottom-0 left-[20%] w-[1px] h-40 bg-slate-800" />
           <div className="absolute bottom-0 left-[40%] w-[1px] h-60 bg-slate-800" />
           <div className="absolute bottom-0 left-[60%] w-[1px] h-32 bg-slate-800" />
           <div className="absolute bottom-0 left-[80%] w-[1px] h-52 bg-slate-800" />
           {/* Floating Badge */}
           <div className="absolute bottom-40 right-[20%] bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl animate-pulse">
              <div className="text-xs text-violet-400 font-mono">Fault Detected</div>
              <div className="text-xs text-slate-400 mt-1">Agent #42 rerouting traffic...</div>
           </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="rounded-xl border border-slate-800 bg-slate-950/50 text-slate-100 shadow-sm p-6 hover:border-violet-500/50 transition-colors group">
              <div className="h-12 w-12 rounded-lg bg-slate-900 flex items-center justify-center mb-4 group-hover:bg-violet-900/20">
                <GitBranch className="text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Automated CI/CD</h3>
              <p className="text-slate-200 text-sm">
                Push to Git and our agents build, test, and deploy your changes instantly. No config files needed.
              </p>
            </Card>
            <Card className="rounded-xl border border-slate-800 bg-slate-950/50 text-slate-100 shadow-sm p-6 hover:border-violet-500/50 transition-colors group">
              <div className="h-12 w-12 rounded-lg bg-slate-900 flex items-center justify-center mb-4 group-hover:bg-violet-900/20">
                <ShieldAlert className="text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Fault Tolerance</h3>
              <p className="text-slate-400 text-sm">
                Self-healing architecture. If a service fails, our agents spin up a replacement in milliseconds.
              </p>
            </Card>
            <Card className="rounded-xl border border-slate-800 bg-slate-950/50 text-slate-100 shadow-sm p-6 hover:border-violet-500/50 transition-colors group">
              <div className="h-12 w-12 rounded-lg bg-slate-900 flex items-center justify-center mb-4 group-hover:bg-violet-900/20">
                <Activity className="text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Proactive Monitoring</h3>
              <p className="text-slate-400 text-sm">
                Real-time metrics and logs. Agents analyze patterns to predict and prevent downtime before it happens.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 border-t border-slate-900 bg-slate-950/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Transparent Pricing
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              Start small and scale. Pay for the agents you use, not the servers you don't.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Basic Plan */}
            <Card className="rounded-xl border  bg-slate-950/50 text-slate-100 shadow-sm p-8 flex flex-col border-slate-800 hover:border-slate-700 transition-all relative overflow-hidden ">
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-white">Basic</h3>
                <p className="text-slate-400 mt-2">Perfect for hobbyists and simple apps.</p>
                <div className="mt-6 flex items-baseline">
                  <span className="text-4xl font-bold text-white">$29</span>
                  <span className="text-slate-500 ml-2">/month</span>
                </div>
              </div>
              
              <div className="flex-1 space-y-4 mb-8">
                <FeatureItem text="Up to 5 Active Agents" />
                <FeatureItem text="Automatic Deployments" />
                <FeatureItem text="Basic Health Checks" />
                <FeatureItem text="7-day Log Retention" />
                <FeatureItem text="Community Support" />
                <FeatureItem text="Shared Infrastructure" />
              </div>

              <Button variant="outline" className="w-full text-black">Start Basic Trial</Button>
            </Card>

            {/* Premium Plan */}
            <Card className="p-8 flex flex-col border-violet-500/30 bg-slate-900/20 relative overflow-hidden ring-1 ring-violet-500/20">
              <div className="absolute top-0 right-0 bg-violet-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
                RECOMMENDED
              </div>
              
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-white">Premium</h3>
                <p className="text-slate-400 mt-2">For scaling startups and mission-critical workloads.</p>
                <div className="mt-6 flex items-baseline">
                  <span className="text-4xl font-bold text-white">$99</span>
                  <span className="text-slate-500 ml-2">/month</span>
                </div>
              </div>
              
              <div className="flex-1 space-y-4 mb-8">
                <FeatureItem text="Unlimited Active Agents" />
                <FeatureItem text="Advanced Fault Tolerance & Self-Healing" />
                <FeatureItem text="AI-Powered Incident Response" />
                <FeatureItem text="90-day Log Retention" />
                <FeatureItem text="Priority 24/7 Support" />
                <FeatureItem text="Dedicated Isolation" />
                <FeatureItem text="Custom Compliance Rules" />
              </div>

              <Button variant="default" className="w-full bg-violet-600 hover:bg-violet-500">Get Started</Button>
            </Card>
          </div>

          {/* Enterprise Callout */}
          <div className="mt-12 rounded-2xl bg-slate-900 p-8 flex flex-col md:flex-row items-center justify-between gap-6 max-w-5xl mx-auto border border-slate-800">
             <div>
               <h3 className="text-lg font-semibold text-white">Need a custom solution?</h3>
               <p className="text-slate-400">We offer on-premise deployment and dedicated support for large enterprises.</p>
             </div>
             <Button variant="secondary">Contact Sales</Button>
          </div>
        </div>
      </section>
    </>
    );
}
