"use client";

import {
  Box,
  LinearProgress,
  Step,
  StepLabel,
  Stepper,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import type { PipelineProgress } from "@/types/hcp";

const STAGES = [
  { key: "fetching_npi", label: "NPI Registry" },
  { key: "collecting_data", label: "Data Collection" },
  { key: "normalizing", label: "Normalization" },
  { key: "ml_prediction", label: "ML Prediction" },
  { key: "generating_summary", label: "AI Summary" },
  { key: "judging_summary", label: "Quality Judge" },
  { key: "generating_pdf", label: "PDF Report" },
  { key: "complete", label: "Complete" },
];

interface Props {
  progress: PipelineProgress | null;
  loading: boolean;
}

export default function PipelineProgressBar({ progress, loading }: Props) {
  if (!loading && !progress) return null;

  const activeStage = progress?.stage || "init";
  const activeIndex = STAGES.findIndex((s) => s.key === activeStage);
  const isFailed = activeStage === "failed";

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 1, gap: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Pipeline Progress
        </Typography>
        {activeStage === "complete" && <CheckCircleIcon color="success" fontSize="small" />}
        {isFailed && <ErrorIcon color="error" fontSize="small" />}
      </Box>

      <LinearProgress
        variant="determinate"
        value={progress?.progress_pct ?? 0}
        sx={{ height: 8, borderRadius: 4, mb: 2 }}
      />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {progress?.message || "Initializing..."}
      </Typography>

      <Stepper activeStep={Math.max(0, activeIndex)} alternativeLabel>
        {STAGES.map((stage) => (
          <Step key={stage.key} completed={activeIndex > STAGES.indexOf(stage)}>
            <StepLabel>{stage.label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {progress?.sources_completed && progress.sources_completed.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Sources completed: {progress.sources_completed.join(", ")}
        </Typography>
      )}
    </Box>
  );
}
