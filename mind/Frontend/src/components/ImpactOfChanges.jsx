import { useEffect, useState } from "react";
import { apiService } from "../services/api";

export default function ImpactOfChanges({ selectedFile, repoId }) {
  const [impacts, setImpacts] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (repoId) {
      setLoading(true);
      apiService.getImpactOfChanges(repoId, selectedFile)
        .then(data => setImpacts(data.data?.impacts || []))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [repoId, selectedFile]);

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
        Impact of Changes {selectedFile && `- ${selectedFile}`}
      </h2>
      {loading ? (
        <div style={{ color: '#94a3b8' }}>Loading...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {impacts.length > 0 ? (
            impacts.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: "#1e293b",
                  padding: 12,
                  borderRadius: 6,
                  borderLeft: `3px solid ${item.severity === "high" ? "#ef4444" : item.severity === "medium" ? "#f59e0b" : "#10b981"}`,
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 500, color: "#e5e7eb" }}>
                  {item.file || item.node}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                  Incoming: {item.incoming_calls} | Outgoing: {item.outgoing_calls}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>
                  Type: {item.type} | Severity: {item.severity}
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: '#94a3b8', fontSize: 12 }}>
              No impacts found
            </div>
          )}
        </div>
      )}
    </div>
  );
}