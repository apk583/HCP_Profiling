export interface Address {
  line1: string;
  line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface NPIData {
  npi: string;
  entity_type: string;
  first_name: string;
  last_name: string;
  organization_name: string;
  credential: string;
  primary_specialty: string;
  address: Address;
  phone: string;
  status: string;
}

export interface Publication {
  pmid: string;
  title: string;
  journal: string;
  pub_date: string;
  authors: string[];
}

export interface ClinicalTrial {
  nct_id: string;
  title: string;
  status: string;
  phase: string;
  role: string;
}

export interface MLFeatures {
  publication_count: number;
  clinical_trial_count: number;
  collaborator_count: number;
  unique_collaborator_count: number;
  strongest_collaboration_count: number;
  average_collaboration_strength: number;
  collaboration_network_density: number;
  recurring_collaborator_ratio: number;
  years_active: number;
}

export interface CollaborationNode {
  id: string;
  label: string;
  type: "hcp" | "author";
  npi?: string | null;
  publication_count: number;
  shared_publications: number;
  publications: Publication[];
}

export interface CollaborationEdge { source: string; target: string; weight: number; }

export interface CollaborationNetwork {
  hcp: { name: string; npi: string };
  metrics: {
    total_publications: number; total_collaborators: number; unique_collaborators: number;
    strongest_collaborator: string; max_shared_publications: number;
    average_collaborations_per_author: number; collaboration_network_density: number;
  };
  nodes: CollaborationNode[];
  edges: CollaborationEdge[];
}

export interface MLPrediction {
  model_name: string;
  influence_score: number;
  kol_tier: string;
  confidence: number;
  feature_importance: Record<string, number>;
}

export interface JudgeEvaluation {
  overall_score: number;
  groundedness: number;
  completeness: number;
  clarity: number;
  feedback: string;
  passed: boolean;
  judge_model: string;
  evaluation_scope: string;
}

export interface SourceResult {
  source: string;
  success: boolean;
  record_count: number;
  error?: string;
}

export interface HCPProfile {
  npi: string;
  identity: NPIData;
  publications: Publication[];
  clinical_trials: ClinicalTrial[];
  collaboration_network: CollaborationNetwork | null;
  features: MLFeatures;
  ml_predictions: MLPrediction[];
  ai_summary: string;
  judge_evaluation: JudgeEvaluation | null;
  source_results: SourceResult[];
  pdf_path: string | null;
  generated_at: string;
}

export interface PipelineProgress {
  npi: string;
  stage: string;
  progress_pct: number;
  message: string;
  sources_completed: string[];
}

export interface HCPProfileResponse {
  success: boolean;
  profile?: HCPProfile;
  error?: string;
}
