import { 
  Check
} from 'lucide-react';


const FeatureItem = ({ text }:{text:string}) => (
  <div className="flex items-center gap-3 text-sm text-slate-300">
    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-500/20 text-violet-400">
      <Check size={12} strokeWidth={3} />
    </div>
    <span>{text}</span>
  </div>
);


export default FeatureItem;