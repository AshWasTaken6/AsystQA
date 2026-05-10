import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function HistoryPage() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/history`)
      .then(res => res.json())
      .then(data => setHistory(data.history || []))
      .catch(err => console.error('Failed to load history', err));
  }, []);

  return (
    <div className="simplePageCard">
      <h2>History</h2>
      <p>Previous reports and scan records.</p>

      <RecentScans scans={history} />
    </div>
  );
}

function RecentScans({ scans }) {
  return (
    <div className="recentPanel">
      <div className="sectionTitle">
        <h2>Recent Scans</h2>
        <a>View all history →</a>
      </div>

      <div className="scanTable">
        <div className="scanRow head">
          <span>Scan Name</span>
          <span>Lang</span>
          <span>Status</span>
          <span>Score</span>
          <span>Issues</span>
          <span>Time</span>
        </div>

        {scans.map((scan, index) => (
          <div className="scanRow" key={index}>
            <span>{scan.fileName || 'Unknown'}</span>
            <span>{scan.language || 'N/A'}</span>
            <span>Completed</span>
            <span>{scan.score}/100</span>
            <span>{scan.issueCount} Issues</span>
            <span>{new Date(scan.timestamp).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default HistoryPage;
