"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DownloadIcon from "@mui/icons-material/Download";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import PipelineProgressBar from "@/components/PipelineProgress";
import ProfileHeader, { MetricsGrid } from "@/components/ProfileHeader";
import ProfileDetails from "@/components/ProfileDetails";
import CollaborationNetworkView from "@/components/CollaborationNetwork";
import { generateProfile, getPdfUrl } from "@/lib/api";
import type { HCPProfile, PipelineProgress } from "@/types/hcp";

export default function HomePage() {
  const [npi, setNpi] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<HCPProfile | null>(null);
  const [progress, setProgress] = useState<PipelineProgress | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setProfile(null);
    setLoading(true);
    setProgress({
      npi,
      stage: "init",
      progress_pct: 0,
      message: "Starting pipeline...",
      sources_completed: [],
    });

    try {
      const response = await generateProfile(npi.trim());
      if (response.success && response.profile) {
        setProfile(response.profile);
        setProgress({
          npi,
          stage: "complete",
          progress_pct: 100,
          message: "Profile generation complete",
          sources_completed: response.profile.source_results
            .filter((s) => s.success)
            .map((s) => s.source),
        });
      } else {
        setError(response.error || "Profile generation failed");
        setProgress({ npi, stage: "failed", progress_pct: 0, message: response.error || "Failed", sources_completed: [] });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setProgress({ npi, stage: "failed", progress_pct: 0, message: String(err), sources_completed: [] });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 4 }}>
        <LocalHospitalIcon sx={{ fontSize: 48, color: "primary.main" }} />
        <Box>
          <Typography variant="h4" color="primary">
            HCP Intelligence Platform
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            AI-Powered Healthcare Professional Profiling & KOL Analysis
          </Typography>
        </Box>
      </Box>

      <Paper sx={{ p: 3, mb: 4 }}>
        <form onSubmit={handleSubmit}>
          <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
            <TextField
              label="NPI Number"
              placeholder="Enter 10-digit NPI"
              value={npi}
              onChange={(e) => setNpi(e.target.value.replace(/\D/g, "").slice(0, 10))}
              fullWidth
              required
              inputProps={{ maxLength: 10, pattern: "[0-9]{10}" }}
              helperText="National Provider Identifier (10 digits)"
              disabled={loading}
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              startIcon={<SearchIcon />}
              disabled={loading || npi.length !== 10}
              sx={{ minWidth: 160, height: 56 }}
            >
              {loading ? "Analyzing..." : "Analyze HCP"}
            </Button>
          </Box>
        </form>
      </Paper>

      {(loading || progress) && (
        <Paper sx={{ p: 3, mb: 4 }}>
          <PipelineProgressBar progress={progress} loading={loading} />
        </Paper>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {profile && (
        <>
          <ProfileHeader profile={profile} />
          <MetricsGrid profile={profile} />
          <Box sx={{ mb: 3 }}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              href={getPdfUrl(profile.npi)}
              target="_blank"
              rel="noopener noreferrer"
            >
              Download PDF Report
            </Button>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) minmax(420px, 1.1fr)" }, gap: 3, alignItems: "start" }}>
            <ProfileDetails profile={profile} />
            {profile.collaboration_network && <CollaborationNetworkView network={profile.collaboration_network} />}
          </Box>
        </>
      )}
    </Container>
  );
}
