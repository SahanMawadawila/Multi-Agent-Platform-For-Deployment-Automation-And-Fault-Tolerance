"use client";

import { OPEN_SIGNUP_MODAL_EVENT } from "@/lib/frontend-events";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import FeatureItem from "./FeatureItem";

export default function HomePriceCards() {

    const ShowLoginForm = () => {
        window.dispatchEvent(new CustomEvent(OPEN_SIGNUP_MODAL_EVENT));
    }

    return (
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

              <Button variant="outline" className="w-full text-black" onClick={ShowLoginForm}>Start Basic Trial</Button>
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

              <Button variant="default" className="w-full bg-violet-600 hover:bg-violet-500" onClick={ShowLoginForm}>Get Started</Button>
            </Card>
          </div>
    )
}