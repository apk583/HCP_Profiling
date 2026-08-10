"use client";

import {
  Box,
  Card,
  CardContent,
  Chip,
  Typography,
} from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import type { HCPProfile } from "@/types/hcp";

function displayName(profile: HCPProfile): string {
  const id = profile.identity;
  if (id.organization_name) return id.organization_name;
  return [id.first_name, id.last_name, id.credential].filter(Boolean).join(" ");
}

interface Props {
  profile: HCPProfile;
}

export default function ProfileHeader({ profile }: Props) {
  const id = profile.identity;
  const bestMl = profile.ml_predictions[0];

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
          <Box
            sx={{
              bgcolor: "primary.main",
              color: "white",
              borderRadius: "50%",
              p: 1.5,
              display: "flex",
            }}
          >
            <PersonIcon fontSize="large" />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" gutterBottom>
              {displayName(profile)}
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
              NPI: {profile.npi} | {id.primary_specialty || "Specialty N/A"}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
              <LocationOnIcon fontSize="small" color="action" />
              <Typography variant="body2">
                {id.address.city}, {id.address.state} {id.address.postal_code}
              </Typography>
            </Box>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Chip label={id.entity_type} size="small" variant="outlined" />
              <Chip
                label={`Status: ${id.status || "Unknown"}`}
                size="small"
                color={id.status === "A" ? "success" : "default"}
              />
              {bestMl && (
                <Chip
                  label={`${bestMl.kol_tier} (${bestMl.influence_score}/100)`}
                  size="small"
                  color="primary"
                />
              )}
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export function MetricsGrid({ profile }: Props) {
  const f = profile.features;
  const metrics = [
    { label: "Publications", value: f.publication_count },
    { label: "Clinical Trials", value: f.clinical_trial_count },
    { label: "Collaborators", value: f.unique_collaborator_count },
    { label: "Years Active", value: f.years_active },
  ];

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
        gap: 2,
        mb: 3,
      }}
    >
      {metrics.map((m) => (
        <Card key={m.label}>
          <CardContent sx={{ textAlign: "center" }}>
            <Typography variant="h4" color="primary" fontWeight={700}>
              {m.value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {m.label}
            </Typography>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}
