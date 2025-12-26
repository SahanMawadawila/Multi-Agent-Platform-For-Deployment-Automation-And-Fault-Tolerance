export interface DetailedProject {
  project_id: string;
  project_name: string;
  github_url?: string;
  is_auto_deploy_enabled: boolean;
  domain_name?: string;
  status?: string;
  topology_info?: any;
  env_variables?: any[];
}


export interface ProjectSimple {
  project_id: string;
  project_name: string;
  domain_name?: string;
  status?: string;
}