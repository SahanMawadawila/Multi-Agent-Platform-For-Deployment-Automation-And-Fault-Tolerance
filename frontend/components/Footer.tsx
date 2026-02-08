import {
  Terminal,
  Globe,
  Server
} from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-slate-900 py-12 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div>
            <h4 className="font-semibold text-white mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><a href="#" className="hover:text-violet-400">Agents</a></li>
              <li><a href="#" className="hover:text-violet-400">Deployments</a></li>
              <li><a href="#" className="hover:text-violet-400">Observability</a></li>
              <li><a href="#" className="hover:text-violet-400">Changelog</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4">Resources</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><a href="#" className="hover:text-violet-400">Documentation</a></li>
              <li><a href="#" className="hover:text-violet-400">API Reference</a></li>
              <li><a href="#" className="hover:text-violet-400">Community</a></li>
              <li><a href="#" className="hover:text-violet-400">Blog</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4">Company</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li><a href="#" className="hover:text-violet-400">About</a></li>
              <li><a href="#" className="hover:text-violet-400">Careers</a></li>
              <li><a href="#" className="hover:text-violet-400">Legal</a></li>
              <li><a href="#" className="hover:text-violet-400">Contact</a></li>
            </ul>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="h-6 w-6 bg-violet-600 rounded-md flex items-center justify-center">
                <Terminal className="text-white" size={14} />
              </div>
              <span className="font-bold text-lg text-white">FlowPilot</span>
            </div>
            <p className="text-xs text-slate-500">
              © 2024 FlowPilot Inc.<br />
              San Francisco, CA
            </p>
          </div>
        </div>
        <div className="flex items-center justify-between pt-8 border-t border-slate-900">
          <div className="flex gap-4">
            <Globe size={20} className="text-slate-500 hover:text-white cursor-pointer" />
            <Server size={20} className="text-slate-500 hover:text-white cursor-pointer" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-xs text-slate-400">All Systems Normal</span>
          </div>
        </div>
      </div>
    </footer>
  );
}