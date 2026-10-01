import { useEffect, useState } from "react";
import { apiService } from "../services/api";

export default function StarFiles({ selectedFile, repoId }) {
  const [starFiles, setStarFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (repoId) {
      setLoading(true);
      apiService.getStarFiles(repoId, 5)
        .then(data => setStarFiles(data.data?.files || []))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [repoId]);

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
        Star Files {selectedFile && `- ${selectedFile}`}
      </h2>

      {loading ? (
        <div style={{
          background: "#1e293b",
          padding: 20,
          borderRadius: 8,
          minHeight: 300,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
        }}>
          Loading...
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {starFiles.length > 0 ? (
            starFiles.map((file, idx) => (
              <div
                key={idx}
                style={{
                  background: "#1e293b",
                  padding: 12,
                  borderRadius: 6,
                  borderLeft: "3px solid #fbbf24",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 500, color: "#e5e7eb" }}>
                  ⭐ {file.file}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                  {file.reason}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 4 }}>
                  Importance: {(file.importance_score * 100).toFixed(0)}% | Calls: {file.incoming_calls}
                </div>
              </div>
            ))
          ) : (
            <div style={{
              background: "#1e293b",
              padding: 20,
              borderRadius: 8,
              minHeight: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#64748b",
            }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>⭐</div>
                <div>No important files identified yet</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
} 

