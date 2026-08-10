"use client";

import { useMemo, useState } from "react";
import { Box, Card, CardContent, Chip, Drawer, IconButton, MenuItem, Select, Stack, Tooltip, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import type { CollaborationNode, CollaborationNetwork } from "@/types/hcp";

export default function CollaborationNetworkView({ network }: { network: CollaborationNetwork }) {
  const [limit, setLimit] = useState(15);
  const [selected, setSelected] = useState<CollaborationNode | null>(null);
  const authors = network.nodes.filter((node) => node.type === "author").slice(0, limit);
  const positions = useMemo(() => authors.map((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(authors.length, 1) - Math.PI / 2;
    const radius = 34 + (index % 3) * 7;
    return { node, x: 50 + Math.cos(angle) * radius, y: 50 + Math.sin(angle) * radius };
  }), [authors]);
  const maxWeight = Math.max(...authors.map((a) => a.shared_publications), 1);
  const m = network.metrics;

  return <>
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} gap={1} mb={2}>
          <Box><Typography variant="h6">Research Collaboration Network</Typography><Typography variant="body2" color="text.secondary">PubMed co-authorship network</Typography></Box>
          <Select size="small" value={limit} onChange={(e) => setLimit(Number(e.target.value))} aria-label="Collaborator count">
            <MenuItem value={15}>Top 15</MenuItem><MenuItem value={25}>Top 25</MenuItem><MenuItem value={50}>Top 50</MenuItem><MenuItem value={9999}>All</MenuItem>
          </Select>
        </Stack>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 1, mb: 2 }}>
          {[["Publications", m.total_publications], ["Unique collaborators", m.unique_collaborators], ["Strongest collaboration", m.max_shared_publications], ["Top collaborator", m.strongest_collaborator || "N/A"], ["Avg. collaborations", m.average_collaborations_per_author], ["Network density", m.collaboration_network_density]].map(([label, value]) => <Box key={String(label)} sx={{ bgcolor: "grey.50", p: 1, borderRadius: 1 }}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography fontWeight={700} noWrap>{value}</Typography></Box>)}
        </Box>
        {authors.length ? <Box sx={{ height: 440, position: "relative", overflow: "hidden", borderRadius: 2, bgcolor: "#f7faff", border: "1px solid", borderColor: "divider" }}>
          <svg viewBox="0 0 100 100" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" aria-label="Collaboration network">
            {positions.map(({ node, x, y }) => <line key={node.id} x1="50" y1="50" x2={x} y2={y} stroke="#90caf9" strokeWidth={0.35 + (node.shared_publications / maxWeight) * 1.2} />)}
            <circle cx="50" cy="50" r="6" fill="#1565c0" /><text x="50" y="51" textAnchor="middle" fill="white" fontSize="2.5">HCP</text>
            {positions.map(({ node, x, y }) => <g key={node.id} onClick={() => setSelected(node)} style={{ cursor: "pointer" }}><Tooltip title={`${node.label}: ${node.shared_publications} shared publications`}><circle cx={x} cy={y} r={2.5 + (node.shared_publications / maxWeight) * 2.5} fill="#26a69a" /></Tooltip><text x={x} y={y + 6} textAnchor="middle" fontSize="2.4" fill="#263238">{node.label.length > 18 ? `${node.label.slice(0, 18)}…` : node.label}</text></g>)}
          </svg>
        </Box> : <Typography color="text.secondary">No co-authors were found in the available PubMed publications.</Typography>}
      </CardContent>
    </Card>
    <Drawer anchor="right" open={Boolean(selected)} onClose={() => setSelected(null)}><Box sx={{ width: 360, p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between" }}><Typography variant="h6">Collaborator details</Typography><IconButton onClick={() => setSelected(null)}><CloseIcon /></IconButton></Box>
      {selected && <><Typography variant="h5" sx={{ mt: 2 }}>{selected.label}</Typography><Stack direction="row" gap={1} sx={{ my: 2 }}><Chip label={`${selected.shared_publications} shared`} color="primary" /><Chip label={`${selected.publication_count} publications`} /></Stack><Typography variant="body2">NPI: {selected.npi || "Not available"}</Typography><Typography variant="subtitle1" sx={{ mt: 3 }}>Shared publications</Typography>{selected.publications.map((publication) => <Box key={publication.pmid} sx={{ py: 1, borderBottom: "1px solid", borderColor: "divider" }}><Typography variant="body2" fontWeight={600}>{publication.title}</Typography><Typography variant="caption" color="text.secondary">{publication.journal} · {publication.pub_date}</Typography></Box>)}</>}
    </Box></Drawer>
  </>;
}
