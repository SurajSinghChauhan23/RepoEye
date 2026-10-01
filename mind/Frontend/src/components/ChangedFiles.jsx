export default function ChangedFiles() {
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
        Already Changed Files
      </h3>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        <div style={{
          padding: '12px',
          background: '#312e81',
          borderRadius: '4px',
          borderLeft: '4px solid #fbbf24'
        }}>
          <p style={{ fontSize: '14px' }}>No changed files yet</p>
        </div>
        <p style={{ fontSize: '12px', color: '#a5b4fc' }}>
          Files that have been modified will appear here.
        </p>
      </div>
    </div>
  )
}
