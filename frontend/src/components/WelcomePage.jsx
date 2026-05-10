function LandingPage({ openDashboard, openLogin }) {
  return (
    <section className="landingPage">
      <header className="landingNav">
        <div className="landingLogo">
          <img src="/logo.png" alt="AsystQA Logo" />
        </div>

        <nav>
          <button onClick={openDashboard}>Dashboard</button>
          <button onClick={openDashboard}>Tools</button>
          <button>Pricing</button>
          <button>About</button>
        </nav>

        <div className="navActions">
          <button className="ghostButton" onClick={openLogin}>
            Sign In
          </button>
          <button className="orangeButton" onClick={openDashboard}>
            Launch Command Center 🚀
          </button>
        </div>
      </header>

      <main className="landingHero">
        <div className="heroBadge">✦ AI Agents for Software QA</div>

        <h1>
          Turn Code into <br />
          Actionable <span>QA Reports.</span>
        </h1>

        <p>
          AsystQA Command Center uses specialist agents to review code, scan security risks,
          generate tests, and build clear developer-ready QA reports.
        </p>

        <div className="heroInputBox">
          <div className="codeIcon">&lt;/&gt;</div>
          <input placeholder="Paste code or start a QA scan..." />
          <button className="detectButton">Auto Detect⌄</button>
          <button className="arrowButton" onClick={openDashboard}>
            →
          </button>
        </div>

        <div className="chipRow">
          <span>&lt;/&gt; Code Review</span>
          <span>🛡 Security Scan</span>
          <span>⚗ Test Generator</span>
          <span>📄 Report Builder</span>
          <span>⌁ Workflow Timeline</span>
          <span>☁ Upload File</span>
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
