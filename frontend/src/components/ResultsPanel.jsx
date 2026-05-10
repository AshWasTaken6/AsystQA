function ResultsPanel({ report, activeTab, setActiveTab, copyReport, downloadReport }) {
  return (
    <div className="resultsPanel">
      <div className="resultTabs">
        <button className={activeTab === "overview" ? "active" : ""} onClick={() => setActiveTab("overview")}>
          Overview
        </button>
        <button className={activeTab === "workflow" ? "active" : ""} onClick={() => setActiveTab("workflow")}>
          Workflow
        </button>
        <button className={activeTab === "issues" ? "active" : ""} onClick={() => setActiveTab("issues")}>
          Issues
        </button>
        <button className={activeTab === "tests" ? "active" : ""} onClick={() => setActiveTab("tests")}>
          Tests
        </button>
      </div>

      {activeTab === "overview" && (
        <div className="tabContent">
          <div className="summaryBox">
            <h2>QA Report Summary</h2>
            <p>{report.summary || "The analysis will appear here after a successful scan."}</p>
          </div>

          <div className="actionButtons">
            <button onClick={copyReport}>Copy Report</button>
            <button onClick={downloadReport}>Download Report</button>
          </div>
        </div>
      )}

      {activeTab === "workflow" && (
        <div className="tabContent">
          <div className="sectionTitle">
            <h2>Agent Workflow</h2>
            <a>View full timeline →</a>
          </div>

          <div className="agentTimeline">
            <AgentStep icon="✓" title="Planner" status="Completed" time="2m 10s" />
            <AgentStep icon="✦" title="Reviewer" status="Completed" time="3m 45s" />
            <AgentStep icon="🛡" title="Security" status="Completed" time="4m 22s" orange />
            <AgentStep icon="⚗" title="Tester" status="In Progress" time="2m 05s" />
            <AgentStep icon="📄" title="Reporter" status="Pending" time="—" pending />
          </div>

          <div className="sectionTitle">
            <h2>Top Issues</h2>
            <a>View all issues →</a>
          </div>

          <div className="issueGrid">
            {report.issues.slice(0, 3).map((issue, index) => (
              <IssueCard key={index} issue={issue} />
            ))}
          </div>

          <div className="sectionTitle">
            <h2>Suggested Tests</h2>
            <a>View all tests →</a>
          </div>

          <div className="testGrid">
            {report.tests.slice(0, 4).map((test, index) => (
              <TestCard key={index} test={test} />
            ))}
          </div>
        </div>
      )}

      {activeTab === "issues" && (
        <div className="tabContent">
          <div className="issueList">
            {report.issues.map((issue, index) => (
              <IssueCard key={index} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {activeTab === "tests" && (
        <div className="tabContent">
          <div className="testList">
            {report.tests.map((test, index) => (
              <div className="testRow" key={index}>
                <span>✓</span>
                <p>
                  {test.title} <small>({test.type})</small>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AgentStep({ icon, title, status, time, orange, pending }) {
  return (
    <div className="agentStep">
      <div className={`agentCircle ${orange ? "orange" : ""} ${pending ? "pending" : ""}`}>{icon}</div>
      <strong>{title}</strong>
      <span>{status}</span>
      <small>{time}</small>
    </div>
  );
}

function IssueCard({ issue }) {
  return (
    <div className="issueCard">
      <span className={`severity ${issue.severity.toLowerCase()}`}>{issue.severity}</span>
      <h3>{issue.title}</h3>
      <p>{issue.text}</p>
      <small>Detected by AsystQA Agent</small>
    </div>
  );
}

function TestCard({ test }) {
  return (
    <div className="testCard">
      <span>✓</span>
      <div>
        <strong>{test.title}</strong>
        <small>{test.type}</small>
      </div>
    </div>
  );
}

export default ResultsPanel;
