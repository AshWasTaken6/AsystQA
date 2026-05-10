import MarketingNav from "./MarketingNav";

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

        <div className="chipRow" aria-label="Core tools">
          <span>&lt;/&gt; Code Review</span>
          <span>Security Scan</span>
          <span>Test Generator</span>
          <span>Report Builder</span>
          <span>Workflow Timeline</span>
          <span>Upload File</span>
        </div>

        <section className="howItWorks">
          <div className="sectionIntro">
            <span>Workflow</span>
            <h2>How AsystQA Works</h2>
            <p>
              A simple flow that turns raw code into a structured QA report using specialist agents.
            </p>
          </div>

          <div className="workflowCards">
            <WorkflowCard
              number="01"
              title="Paste or Upload Code"
              text="Start by pasting code into the editor or uploading a project file for analysis."
            />

            <WorkflowCard
              number="02"
              title="Agents Review the Code"
              text="Planner, Reviewer, Security, Tester, and Reporter agents work together through a clear QA workflow."
            />

            <WorkflowCard
              number="03"
              title="Get a QA Report"
              text="Receive a QA score, risk level, issue breakdown, suggested tests, and downloadable report."
            />
          </div>
        </section>
      </main>
    </section>
  );
}

function WorkflowCard({ number, title, text }) {
  return (
    <div className="workflowCard">
      <div className="workflowNumber">{number}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export default LandingPage;