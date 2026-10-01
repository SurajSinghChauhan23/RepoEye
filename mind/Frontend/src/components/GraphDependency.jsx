import { useEffect, useState } from "react";
import { apiService } from "../services/api";

export default function GraphDependency({ selectedFile, repoId }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (repoId) {
      setLoading(true);
      apiService.getGraphDependency(repoId, selectedFile)
        .then(data => setGraphData(data.data || { nodes: [], edges: [] }))
        .catch(err => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [repoId, selectedFile]);

  return (
    <div style={{
      padding: '20px',
      background: '#1e1b4b',
      borderRadius: '8px',
      color: '#e0e7ff',
      height: '100%',
      overflowY: 'auto'
    }}>
      <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: 'bold' }}>
        Graph Dependency
      </h3>
      {loading ? (
        <div style={{
          padding: '12px',
          background: '#312e81',
          borderRadius: '4px',
          borderLeft: '4px solid #818cf8'
        }}>
          <p style={{ fontSize: '14px' }}>Loading dependency graph...</p>
        </div>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{
            padding: '12px',
            background: '#312e81',
            borderRadius: '4px',
            borderLeft: '4px solid #818cf8'
          }}>
            <p style={{ fontSize: '14px', fontWeight: '500' }}>
              Nodes: {graphData.nodes?.length || 0}
            </p>
            <p style={{ fontSize: '12px', color: '#a5b4fc', marginTop: '4px' }}>
              Dependencies: {graphData.edges?.length || 0}
            </p>
          </div>
          
          {graphData.nodes && graphData.nodes.length > 0 && (
            <div style={{
              padding: '12px',
              background: '#312e81',
              borderRadius: '4px'
            }}>
              <p style={{ fontSize: '12px', color: '#a5b4fc', marginBottom: '8px' }}>
                Modules:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {graphData.nodes.slice(0, 8).map((node, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: '11px',
                      background: '#2d2a84',
                      padding: '4px 8px',
                      borderRadius: '3px',
                      color: '#c7d2fe'
                    }}
                  >
                    {node.label?.split('/').pop() || node.id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
