import { useMemo, useState } from 'react';

const allScans = [
  {
    name: 'Authentication Module',
    lang: 'JS',
    status: 'Completed',
    score: 88,
    issues: 14,
    updated: '2h ago',
    timestamp: 6,
  },
  {
    name: 'Payment Processing API',
    lang: 'PY',
    status: 'Completed',
    score: 94,
    issues: 8,
    updated: '5h ago',
    timestamp: 4,
  },
  {
    name: 'Data Validation Service',
    lang: 'JS',
    status: 'In Progress',
    score: 76,
    issues: 22,
    updated: '1 day ago',
    timestamp: 2,
  },
  {
    name: 'User Profile API',
    lang: 'PY',
    status: 'Pending',
    score: 0,
    issues: 0,
    updated: '3h ago',
    timestamp: 5,
  },
  {
    name: 'Security Module',
    lang: 'TS',
    status: 'Failed',
    score: 52,
    issues: 35,
    updated: '6h ago',
    timestamp: 3,
  },
  {
    name: 'Frontend Components',
    lang: 'JS',
    status: 'Completed',
    score: 91,
    issues: 6,
    updated: '1 day ago',
    timestamp: 1,
  },
];

function ScansPage({ onStartNewScan }) {
  // State for filtering and sorting
  const [statusFilter, setStatusFilter] = useState('All');
  const [sortBy, setSortBy] = useState('date');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Apply filters and sorting
  const filteredAndSortedScans = useMemo(() => {
    let result = [...allScans];

    // Filter by status
    if (statusFilter !== 'All') {
      result = result.filter((scan) => scan.status === statusFilter);
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'score') {
        return b.score - a.score; // Descending score
      } else if (sortBy === 'date') {
        return b.timestamp - a.timestamp; // Newest first
      } else if (sortBy === 'status') {
        return a.status.localeCompare(b.status);
      }
      return 0;
    });

    return result;
  }, [statusFilter, sortBy]);

  // Calculate pagination
  const totalPages = Math.ceil(filteredAndSortedScans.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedScans = filteredAndSortedScans.slice(startIndex, startIndex + itemsPerPage);

  const scans = allScans;
  const activeCount = scans.filter((scan) => scan.status !== 'Completed').length;

  return (
    <div className="simplePageCard">
      <div className="sectionTitle">
        <div>
          <h2>Scans</h2>
          <p>Track current and previous QA scans across your project files.</p>
        </div>
        <button 
          className="orangeButton"
          onClick={() => onStartNewScan && onStartNewScan()}
        >
          Start New Scan
        </button>
      </div>

      <div className="scanOverview">
        <div className="summaryCard">
          <strong>{scans.length}</strong>
          <span>Total scans</span>
        </div>
        <div className="summaryCard">
          <strong>{activeCount}</strong>
          <span>Active scans</span>
        </div>
        <div className="summaryCard">
          <strong>88 / 100</strong>
          <span>Latest score</span>
        </div>
      </div>

      {/* Filter and Sort Controls */}
      <div className="scanControls">
        <div className="controlGroup">
          <label>Filter by Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
          >
            <option>All</option>
            <option>Completed</option>
            <option>In Progress</option>
            <option>Pending</option>
            <option>Failed</option>
          </select>
        </div>

        <div className="controlGroup">
          <label>Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setCurrentPage(1);
            }}
          >
            <option value="date">Date (Newest)</option>
            <option value="score">Score (Highest)</option>
            <option value="status">Status (A-Z)</option>
          </select>
        </div>

        <div className="resultsInfo">
          Showing {paginatedScans.length > 0 ? startIndex + 1 : 0}–{Math.min(startIndex + itemsPerPage, filteredAndSortedScans.length)} of {filteredAndSortedScans.length} scans
        </div>
      </div>

      <div className="scanTable">
        <div className="scanRow head">
          <span>Scan Name</span>
          <span>Lang</span>
          <span>Status</span>
          <span>Score</span>
          <span>Issues</span>
          <span>Updated</span>
        </div>

        {paginatedScans.map((scan, index) => (
          <div className="scanRow" key={index}>
            <span>{scan.name}</span>
            <span>{scan.lang}</span>
            <span>
              <span className={`statusTag ${scan.status.toLowerCase().replace(/\s+/g, '-')}`}>
                {scan.status}
              </span>
            </span>
            <span>{scan.score > 0 ? `${scan.score} / 100` : '—'}</span>
            <span>{scan.issues > 0 ? `${scan.issues} Issues` : 'None'}</span>
            <span>{scan.updated}</span>
          </div>
        ))}
      </div>

      {/* Pagination */}
      <div className="paginationControls">
        <button
          disabled={currentPage === 1}
          onClick={() => setCurrentPage(currentPage - 1)}
          className="paginationBtn"
        >
          ← Previous
        </button>
        
        <span className="paginationInfo">
          Page {currentPage} of {totalPages || 1}
        </span>
        
        <button
          disabled={currentPage === totalPages}
          onClick={() => setCurrentPage(currentPage + 1)}
          className="paginationBtn"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

export default ScansPage;
