"use client";

import {
  Box,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import type { HCPProfile } from "@/types/hcp";

interface Props {
  profile: HCPProfile;
}

export default function ProfileDetails({ profile }: Props) {
  const judge = profile.judge_evaluation;
  const usedGemini = judge?.judge_model !== "Heuristic fallback" && judge?.judge_model !== "Gemini unavailable";

  return (
    <Box>
      {profile.ml_predictions.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Influence Predictions
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell align="right">Score</TableCell>
                  <TableCell>KOL Tier</TableCell>
                  <TableCell align="right">Confidence</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {profile.ml_predictions.map((p) => (
                  <TableRow key={p.model_name}>
                    <TableCell>{p.model_name}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={p.influence_score}
                          sx={{ flex: 1, height: 8, borderRadius: 4 }}
                        />
                        <Typography variant="body2">{p.influence_score}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label={p.kol_tier} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">{(p.confidence * 100).toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {profile.publications.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Publications ({profile.publications.length})
            </Typography>
            {profile.publications.slice(0, 5).map((pub) => (
              <Box key={pub.pmid} sx={{ mb: 1.5 }}>
                <Typography variant="body2" fontWeight={600}>
                  {pub.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {pub.journal} | {pub.pub_date}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}

      {profile.clinical_trials.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Clinical Trials ({profile.clinical_trials.length})
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>NCT ID</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Role</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {profile.clinical_trials.slice(0, 5).map((t) => (
                  <TableRow key={t.nct_id}>
                    <TableCell>{t.nct_id}</TableCell>
                    <TableCell>{t.title}</TableCell>
                    <TableCell>{t.status}</TableCell>
                    <TableCell>{t.role || "N/A"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {profile.ai_summary && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              AI Intelligence Summary
            </Typography>
            <Typography
              variant="body1"
              sx={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}
            >
              {profile.ai_summary}
            </Typography>
          </CardContent>
        </Card>
      )}

      {judge && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              LLM Profile Validation
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {judge.evaluation_scope} reviewed by {usedGemini ? `Gemini (${judge.judge_model || "configured model"})` : judge.judge_model}
            </Typography>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 1 }}>
              <Chip
                label={judge.passed ? `Validated · ${judge.overall_score}/10` : `Needs review · ${judge.overall_score}/10`}
                color={judge.passed ? "success" : "warning"}
              />
              <Chip label={`Groundedness: ${judge.groundedness}/10`} />
              <Chip label={`Completeness: ${judge.completeness}/10`} />
              <Chip label={`Clarity: ${judge.clarity}/10`} />
            </Box>
            <Typography variant="body2" color="text.secondary">
              {judge.feedback}
            </Typography>
          </CardContent>
        </Card>
      )}

      {profile.source_results.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Data Sources
            </Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              {profile.source_results.map((sr) => (
                <Chip
                  key={sr.source}
                  label={`${sr.source}: ${sr.success ? sr.record_count + " records" : "failed"}`}
                  color={sr.success ? "success" : "error"}
                  variant="outlined"
                  size="small"
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
