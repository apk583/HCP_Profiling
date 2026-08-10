import type { HCPProfileResponse, PipelineProgress } from "@/types/hcp";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function checkHealth(): Promise<{
  status: string;
  azure_configured: boolean;
  gemini_configured: boolean;
}> {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) throw new Error("Backend unavailable");
  return res.json();
}

export async function generateProfile(npi: string): Promise<HCPProfileResponse> {
  const res = await fetch(`${API_BASE}/api/v1/hcp/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ npi }),
  });
  if (res.status === 404) {
    const err = await res.json();
    throw new Error(err.detail || "Provider not found");
  }
  if (res.status === 422) {
    throw new Error("Invalid NPI format. Must be 10 digits.");
  }
  return res.json();
}

export async function getProgress(npi: string): Promise<PipelineProgress> {
  const res = await fetch(`${API_BASE}/api/v1/hcp/profile/${npi}/progress`);
  if (!res.ok) throw new Error("Progress not available");
  return res.json();
}

export function getPdfUrl(npi: string): string {
  return `${API_BASE}/api/v1/hcp/profile/${npi}/pdf`;
}
