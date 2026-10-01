import React, { useState, useEffect } from "react";
import { apiService } from "../services/api";

export function FileContentViewer({ fileName, repoId }) {
  const [fileContent, setFileContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState("text");

  useEffect(() => {
    const fetchFileContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await apiService.getFileContent(repoId, fileName);
        
        setFileContent(response.content || "");
        setLanguage(response.language || "text");
      } catch (err) {
        setError(err.message || "Failed to load file");
        console.error("Error fetching file content:", err);
      } finally {
        setLoading(false);
      }
    };

    if (repoId && fileName) {
      fetchFileContent();
    }
  }, [fileName, repoId]);

  if (loading) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
        }}
      >
        Loading file...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#ef4444",
          padding: "16px",
          textAlign: "center",
        }}
      >
        Error: {error}
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        overflow: "auto",
        padding: "12px",
      }}
    >
      <pre
        style={{
          fontFamily: "'Monaco', 'Courier New', monospace",
          fontSize: 12,
          lineHeight: 1.6,
          margin: 0,
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
          color: "#e2e8f0",
          background: "#0f172a",
          padding: "12px",
          borderRadius: "4px",
          overflowX: "auto",
        }}
      >
        {fileContent || "File is empty"}
      </pre>
    </div>
  );
}
