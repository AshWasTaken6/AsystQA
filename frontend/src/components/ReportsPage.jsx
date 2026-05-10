function ReportsPage({ report, fileName, copyReport, downloadReport }) {
  return (
    <div className="simplePageCard">
      <h2>Reports</h2>
      <p>Export or copy the latest QA report.</p>

      <div className="reportPreview">
        <strong>{fileName}</strong>
        <span>QA Score: {report.score}/100</span>
        <span>Risk Level: {report.risk}</span>
        <span>Issues Found: {report.issueCount}</span>
      </div>

      <div className="actionButtons">
        <button onClick={copyReport}>Copy Report</button>
        <button onClick={downloadReport}>Download Report</button>
      </div>
    </div>
  );
}

export default ReportsPage;
