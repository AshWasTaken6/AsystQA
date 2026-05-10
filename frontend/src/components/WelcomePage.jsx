import MarketingNav from "./MarketingNav";

const trustStats = [
  ["4", "specialist agents"],
  ["92", "sample QA score"],
  ["28", "issues triaged"],
];

function LandingPage({ openDashboard, openLogin, openLanding, openPricing, openAbout }) {
  return (
    <section className="landingPage">
      <MarketingNav
        activePage="home"
        openLanding={openLanding}
        openPricing={openPricing}
        openAbout={openAbout}
        openDashboard={openDashboard}
        openLogin={openLogin}
      />

      <main className="landingHero">
        <div className="heroCopy">
          <h1>
            Turn code into <span>actionable QA reports.</span>
          </h1>

          <p>
            AsystQA Command Center uses specialist agents to review code, scan security risks,
            generate tests, and build clear developer-ready QA reports.
          </p>
        </div>

        <div className="heroInputBox">
          <div className="codeIcon">&lt;/&gt;</div>
          <input aria-label="Code scan prompt" placeholder="Paste code or start a QA scan..." />
          <button className="detectButton">Auto Detect</button>
          <button className="arrowButton" onClick={openDashboard} aria-label="Open dashboard">
            →
          </button>
        </div>

        <div className="trustStrip" aria-label="AsystQA highlights">
          {trustStats.map(([value, label]) => (
            <div key={label}>
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>

        <div className="chipRow" aria-label="Core tools">
          <span>&lt;/&gt; Code Review</span>
          <span>Security Scan</span>
          <span>Test Generator</span>
          <span>Report Builder</span>
          <span>Workflow Timeline</span>
          <span>Upload File</span>
        </div>

        <div className="previewGrid">
          <div className="previewCard scorePreview">
            <div className="donut">
              <strong>92</strong>
              <small>/100</small>
            </div>
            <div>
              <h3>QA Score</h3>
              <h2>Excellent</h2>
              <p>Code quality looks great. Keep it up.</p>
              <a>View full report →</a>
            </div>
          </div>

          <div className="previewCard">
            <h3>Issues Found</h3>
            <strong className="bigNumber">28</strong>
            <p>12 High · 10 Medium · 6 Low</p>
          </div>

          <div className="previewCard">
            <h3>Risk Level</h3>
            <div className="riskPreview">
              <span>🛡</span>
              <div>
                <h2>Medium</h2>
                <p>Some vulnerabilities need attention.</p>
              </div>
            </div>
          </div>

          <div className="previewCard workflowPreview">
            <div className="cardHeader">
              <h3>Agent Workflow</h3>
              <a>View timeline →</a>
            </div>

            <div className="miniWorkflow">
              <MiniStep title="Code" status="Done" />
              <MiniStep title="Security" status="Done" orange />
              <MiniStep title="Tests" status="Done" />
              <MiniStep title="Report" status="Progress" orange />
              <MiniStep title="Final" status="Pending" blue />
            </div>
          </div>
        </div>
      </main>
    </section>
  );
}

function MiniStep({ title, status, orange, blue }) {
  return (
    <div className="miniStep">
      <div className={`${orange ? "orange" : ""} ${blue ? "blue" : ""}`}></div>
      <strong>{title}</strong>
      <span>{status}</span>
    </div>
  );
}

export default LandingPage;
