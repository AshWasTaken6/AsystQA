import { useState, useEffect } from 'react';
import CodePanel from './CodePanel';
import ResultsPanel from './ResultsPanel';

const demoScans = [
  {
    name: 'User Authentication Module',
    lang: 'JS',
    status: 'Completed',
    score: 88,
    issues: 14,
    updated: '2h ago',
    progress: 100,
  },
  {
    name: 'Payment Processing API',
    lang: 'PY',
    status: 'Completed',
    score: 94,
    issues: 8,
    updated: '5h ago',
    progress: 100,
  },
  {
    name: 'Data Validation Service',
    lang: 'JS',
    status: 'In Progress',
    score: 76,
    issues: 22,
    updated: '1 day ago',
    progress: 65,
  },
  {
    name: 'User Profile API',
    lang: 'PY',
    status: 'Pending',
    score: 0,
    issues: 0,
    updated: '3h ago',
    progress: 0,
  },
  {
    name: 'Security Module',
    lang: 'TS',
    status: 'Failed',
    score: 52,
    issues: 35,
    updated: '6h ago',
    progress: 45,
    error: 'Timeout during analysis',
  },
];

function OverviewDashboard({
  code,
  setCode,
  language,
  setLanguage,
  fileName,
  handleUpload,
  report,
  activeTab,
  setActiveTab,
  isScanning,
  runScan,
  copyReport,
  downloadReport,
}) {
  const scans = demoScans;

  // Simulate progress updates for "In Progress" scans
  const [scanProgress, setScanProgress] = useState({});

  useEffect(() => {
    const interval = setInterval(() => {
      setScanProgress((prev) => {
        const updated = { ...prev };
        scans.forEach((scan) => {
          if (scan.status === 'In Progress') {
            const current = updated[scan.name] || scan.progress;
            if (current < 100) {
              updated[scan.name] = Math.min(current + Math.random() * 8, 95);
            }
          }
        });
        return updated;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [scans]);

  const activeScans = scans.filter((scan) => scan.status !== 'Completed').length;
  const issuesDetails = report.issues || [];
  const issueSummary = issuesDetails.length
    ? summarizeIssueCounts(issuesDetails)
    : '12 High · 10 Medium · 6 Low';

  const statusLabel = getScoreLabel(report.score);
  const subtitle =
    report.score === 0
      ? 'Run a scan to generate your QA score and see the latest issues.'
      : 'Keep monitoring quality and review the latest findings.';

  const riskDescription =
    report.risk === 'Unknown'
      ? 'No risk data yet. Run a scan to start your first analysis.'
      : 'Some vulnerabilities need attention. Review the risk report.';

  return (
    <>
      <section className="metricsGrid">
        <MetricScore score={report.score} label={statusLabel} subtitle={subtitle} />
        <MetricCard
          title="Active Scans"
          value={activeScans}
          text={activeScans ? 'In progress' : 'No active scans'}
          footer="Active scans are currently processing."
        />
        <MetricCard
          title="Issues Found"
          value={report.issueCount}
          text={report.issueCount ? 'Detected today' : 'No issues currently'}
          footer={issueSummary}
        />
        <MetricRisk risk={report.risk} description={riskDescription} />
      </section>

      <section className="workspaceGrid">
        <CodePanel
          code={code}
          setCode={setCode}
          language={language}
          setLanguage={setLanguage}
          fileName={fileName}
          handleUpload={handleUpload}
          runScan={runScan}
          isScanning={isScanning}
        />

        <ResultsPanel
          report={report}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          copyReport={copyReport}
          downloadReport={downloadReport}
        />
      </section>

      <section className="bottomGrid">
        <RecentScans scans={scans} scanProgress={scanProgress} />
        <QuickActions />
      </section>
    </>
  );
}

function getScoreLabel(score) {
  if (score === 0) {
    return 'Awaiting first scan';
  }

  if (score < 60) {
    return 'Needs improvement';
  }

  if (score < 80) {
    return 'Good';
  }

  return 'Excellent';
}

function summarizeIssueCounts(issues) {
  const counts = {
    High: 0,
    Medium: 0,
    Low: 0,
  };

  issues.forEach((item) => {
    const severity =
      item && typeof item === 'object'
        ? item.severity || item.level || item.priority
        : item;
    const text = String(severity || '').toLowerCase();

    if (text.includes('high')) counts.High += 1;
    else if (text.includes('medium')) counts.Medium += 1;
    else if (text.includes('low')) counts.Low += 1;
  });

  return `${counts.High} High · ${counts.Medium} Medium · ${counts.Low} Low`;
}

function MetricScore({ score, label, subtitle }) {
  return (
    <div className="metricCard scoreMetric">
      <h3>QA Score ⓘ</h3>
      <div className="metricFlex">
        <div className="smallDonut">
          <strong>{score}</strong>
          <small>/100</small>
        </div>

        <div>
          <h2>{label}</h2>
          <p>{subtitle}</p>
          <a>View full report →</a>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, text, footer }) {
  return (
    <div className="metricCard">
      <h3>{title} ⓘ</h3>
      <strong className="metricValue">{value}</strong>
      <p>{text}</p>
      <small>{footer}</small>
    </div>
  );
}

function MetricRisk({ risk, description }) {
  return (
    <div className="metricCard riskMetric">
      <h3>Risk Level ⓘ</h3>

      <div className="riskBlock">
        <div>🛡</div>
        <section>
          <h2>{risk}</h2>
          <p>{description}</p>
        </section>
      </div>

      <a>View risks →</a>
    </div>
  );
}

function RecentScans({ scans, scanProgress = {} }) {
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

        {scans.map((scan, index) => {
          const progress = scanProgress[scan.name] !== undefined ? scanProgress[scan.name] : scan.progress;
          
          return (
            <div className="scanRow" key={index}>
              <span>{scan.name}</span>
              <span>{scan.lang}</span>
              <span>
                <span className={`statusTag ${scan.status.toLowerCase().replace(/\s+/g, '-')}`}>
                  {scan.status}
                </span>
              </span>
              <span>{scan.score > 0 ? `${scan.score} / 100` : '—'}</span>
              <span>{scan.issues > 0 ? scan.issues : '—'}</span>
              <span>{scan.updated}</span>
              
              {/* Progress indicator for In Progress scans */}
              {scan.status === 'In Progress' && (
                <div className="progressContainer">
                  <div className="progressBar">
                    <div className="progressFill" style={{ width: `${progress}%` }}></div>
                  </div>
                  <span className="progressText">{Math.round(progress)}%</span>
                </div>
              )}
              
              {/* Error indicator for Failed scans */}
              {scan.status === 'Failed' && scan.error && (
                <div className="errorIndicator" title={scan.error}>
                  ⚠ {scan.error}
                </div>
              )}
              
              {/* Pending indicator */}
              {scan.status === 'Pending' && (
                <div className="pendingIndicator">
                  ⏳ Queued for analysis
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function QuickActions() {
  return (
    <div className="quickPanel">
      <h2>Quick Actions</h2>

      <div className="quickGrid">
        <QuickItem icon="&lt;/&gt;" title="New Scan" text="Start a new code scan" />
        <QuickItem icon="⬆" title="Upload File" text="Analyze a file" />
        <QuickItem icon="●" title="Git Integration" text="Connect repository" />
        <QuickItem icon="📄" title="Report Builder" text="Create custom report" />
        <QuickItem icon="⚗" title="Test Generator" text="Generate tests" />
      </div>
    </div>
  );
}

function QuickItem({ icon, title, text }) {
  return (
    <div className="quickItem">
      <div>{icon}</div>
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

export default OverviewDashboard;
