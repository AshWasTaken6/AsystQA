import MarketingNav from "./MarketingNav";

function AboutPage({ openDashboard, openLogin, openLanding, openPricing, openAbout }) {
  return (
    <section className="aboutPage">
      <MarketingNav
        activePage="about"
        openLanding={openLanding}
        openPricing={openPricing}
        openAbout={openAbout}
        openDashboard={openDashboard}
        openLogin={openLogin}
      />

      <main className="aboutHero">
        <div className="aboutBadge">Built for AI Agents & Agentic Workflows</div>

        <h1>
          Software QA, rebuilt as a <span>multi-agent command center.</span>
        </h1>

        <p>
          AsystQA helps developers, students, startups, and small engineering teams
          turn raw code into clear QA reports using specialist agents for review,
          security, testing, and reporting.
        </p>

        <div className="aboutHeroActions">
          <button onClick={openDashboard}>Open Command Center</button>
          <button className="aboutGhostBtn" onClick={openPricing}>
            View Business Model
          </button>
        </div>
      </main>

      <section className="aboutMission">
        <div className="missionCard mainMission">
          <span>01</span>
          <h2>The Problem</h2>
          <p>
            Code review and QA are often slow, repetitive, and hard to manage.
            Small teams may not have dedicated QA engineers, security reviewers,
            or structured testing support, which can lead to missed bugs and weak
            validation.
          </p>
        </div>

        <div className="missionCard">
          <span>02</span>
          <h2>The Solution</h2>
          <p>
            AsystQA turns code into a guided QA workflow. A user can paste or
            upload code, run a scan, and receive a clear report with issues,
            suggested tests, risk level, and a QA score.
          </p>
        </div>

        <div className="missionCard">
          <span>03</span>
          <h2>The Vision</h2>
          <p>
            Our long-term goal is to connect AsystQA with GitHub, pull requests,
            CI/CD pipelines, team workspaces, and deeper AI reasoning so teams can
            improve quality continuously.
          </p>
        </div>
      </section>

      <section className="agentStory">
        <div className="agentStoryText">
          <span>Agent Workflow</span>
          <h2>Each agent has a clear job.</h2>
          <p>
            Instead of showing one generic AI response, AsystQA separates the QA
            process into focused agents. This makes the output easier to understand,
            easier to explain, and more useful for real development teams.
          </p>
        </div>

        <div className="agentStack">
          <AgentRow
            number="01"
            name="Planner Agent"
            text="Prepares the scan, detects language, and organizes the QA workflow."
          />
          <AgentRow
            number="02"
            name="Reviewer Agent"
            text="Checks code quality, maintainability, repeated logic, and debugging leftovers."
          />
          <AgentRow
            number="03"
            name="Security Agent"
            text="Scans for hardcoded secrets, risky execution, exposed tokens, and unsafe patterns."
          />
          <AgentRow
            number="04"
            name="Tester Agent"
            text="Generates edge case, validation, functional, and performance test ideas."
          />
          <AgentRow
            number="05"
            name="Reporter Agent"
            text="Builds the final QA score, risk level, recommendations, and downloadable report."
          />
        </div>
      </section>

      <section className="aboutImpact">
        <div>
          <strong>5</strong>
          <span>specialist agents</span>
        </div>
        <div>
          <strong>4</strong>
          <span>scan profiles planned</span>
        </div>
        <div>
          <strong>1</strong>
          <span>clear QA command center</span>
        </div>
      </section>

      <section className="aboutFinal">
        <h2>Built to help teams ship safer code faster.</h2>
        <p>
          AsystQA is designed to make software quality easier, faster, and more
          accessible by giving teams a structured way to review code before it
          reaches production.
        </p>
        <button onClick={openDashboard}>Launch AsystQA</button>
      </section>
    </section>
  );
}

function AgentRow({ number, name, text }) {
  return (
    <div className="agentRow">
      <div>{number}</div>
      <section>
        <h3>{name}</h3>
        <p>{text}</p>
      </section>
    </div>
  );
}

export default AboutPage;