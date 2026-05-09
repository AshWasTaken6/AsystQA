import { useMemo, useState } from "react";
import "./App.css";

const sampleCode = `function calculateTotal(items) {
  let total = 0;

  for (let i = 0; i <= items.length; i++) {
    total += items[i].price;
  }

  return total;
}`;

const demoUsers = [
  {
    name: "Team AsystQA",
    role: "Admin",
    email: "admin@asystqa.com",
    password: "admin123",
    initials: "TA",
  },
  {
    name: "Developer Demo",
    role: "Developer",
    email: "dev@asystqa.com",
    password: "dev123",
    initials: "DD",
  },
];

function App() {
  const [screen, setScreen] = useState("intro");
  const [dashboardPage, setDashboardPage] = useState("overview");
  const [showLogin, setShowLogin] = useState(false);
  const [user, setUser] = useState(null);

  const [code, setCode] = useState(sampleCode);
  const [fileName, setFileName] = useState("sample-code.js");
  const [activeTab, setActiveTab] = useState("workflow");
  const [isScanning, setIsScanning] = useState(false);
  const [toast, setToast] = useState("");

  const report = useMemo(() => createReport(code), [code]);

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(""), 2300);
  }

  function openDashboard() {
    if (!user) {
      setShowLogin(true);
      return;
    }

    setScreen("dashboard");
  }

  function openLanding() {
    setScreen("landing");
  }

  function login(email, password) {
    const foundUser = demoUsers.find(
      (demoUser) =>
        demoUser.email.toLowerCase() === email.toLowerCase() &&
        demoUser.password === password
    );

    if (!foundUser) {
      showToast("Wrong email or password");
      return false;
    }

    setUser(foundUser);
    setShowLogin(false);
    setScreen("dashboard");
    showToast(`Welcome, ${foundUser.name}`);
    return true;
  }

  function logout() {
    setUser(null);
    setDashboardPage("overview");
    setScreen("landing");
    showToast("Logged out successfully");
  }

  function handleUpload(event) {
    const file = event.target.files[0];

    if (!file) return;

    setFileName(file.name);

    const reader = new FileReader();

    reader.onload = function (e) {
      setCode(e.target.result);
      showToast("File uploaded successfully");
    };

    reader.readAsText(file);
  }

  function runScan() {
    if (!code.trim()) {
      showToast("Paste or upload code first");
      return;
    }

    setIsScanning(true);

    setTimeout(() => {
      setIsScanning(false);
      setActiveTab("workflow");
      setDashboardPage("overview");
      showToast("QA report generated");
    }, 900);
  }

  function copyReport() {
    navigator.clipboard.writeText(makeReportText(report, fileName));
    showToast("Report copied");
  }

  function downloadReport() {
    const text = makeReportText(report, fileName);
    const blob = new Blob([text], { type: "text/plain" });
    const link = document.createElement("a");

    link.href = URL.createObjectURL(blob);
    link.download = "asystqa-report.txt";
    link.click();

    URL.revokeObjectURL(link.href);
    showToast("Report downloaded");
  }

  return (
    <div className="app">
      {screen === "intro" && (
        <IntroScreen
          openDashboard={openDashboard}
          openLanding={openLanding}
        />
      )}

      {screen === "landing" && (
        <LandingPage
          openDashboard={openDashboard}
          openLogin={() => setShowLogin(true)}
        />
      )}

      {screen === "dashboard" && (
        <Dashboard
          user={user}
          logout={logout}
          dashboardPage={dashboardPage}
          setDashboardPage={setDashboardPage}
          code={code}
          setCode={setCode}
          fileName={fileName}
          handleUpload={handleUpload}
          report={report}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isScanning={isScanning}
          runScan={runScan}
          copyReport={copyReport}
          downloadReport={downloadReport}
        />
      )}

      {showLogin && (
        <LoginModal
          login={login}
          closeLogin={() => setShowLogin(false)}
        />
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

function IntroScreen({ openDashboard, openLanding }) {
  return (
    <section className="introScreen">
      <video className="introVideo" autoPlay muted loop playsInline>
        <source src="/intro.mp4" type="video/mp4" />
      </video>

      <div className="introDarkLayer"></div>

      <button className="introTinyLogo" onClick={openLanding} title="Open welcome page">
        <img src="/logo.png" alt="AsystQA Logo" />
      </button>

      <div className="introHeroText">
        <p>AI Agents for Software QA</p>
        <h1>AsystQA Command Center</h1>
        <span>Review code, find issues, generate tests, and build QA reports.</span>

        <div className="introHeroActions">
          <button className="introPrimaryBtn" onClick={openDashboard}>
            Enter Command Center →
          </button>

          <button className="introSecondaryBtn" onClick={openLanding}>
            View Welcome Page
          </button>
        </div>
      </div>
    </section>
  );
}

function LoginModal({ login, closeLogin }) {
  const [email, setEmail] = useState("admin@asystqa.com");
  const [password, setPassword] = useState("admin123");

  function handleSubmit(event) {
    event.preventDefault();
    login(email, password);
  }

  return (
    <div className="loginOverlay">
      <form className="loginModal" onSubmit={handleSubmit}>
        <button type="button" className="closeLoginBtn" onClick={closeLogin}>
          ×
        </button>

        <img src="/logo.png" alt="AsystQA Logo" />

        <h2>Sign in to AsystQA</h2>
        <p>Use a demo account to enter the command center.</p>

        <label>
          Email
          <input
            type="email"
            value={email}
            placeholder="admin@asystqa.com"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            placeholder="admin123"
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button type="submit" className="loginSubmitBtn">
          Sign In →
        </button>

        <div className="demoAccounts">
          <strong>Demo accounts</strong>
          <span>Admin: admin@asystqa.com / admin123</span>
          <span>Developer: dev@asystqa.com / dev123</span>
        </div>
      </form>
    </div>
  );
}

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

function Dashboard({
  user,
  logout,
  dashboardPage,
  setDashboardPage,
  code,
  setCode,
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
  return (
    <section className="dashboardPage">
      <aside className="sidebar">
        <div className="sidebarLogo">
          <img src="/logo.png" alt="AsystQA Logo" />
          <span>COMMAND CENTER</span>
        </div>

        <nav className="sidebarNav">
          <button
            className={dashboardPage === "overview" ? "active" : ""}
            onClick={() => setDashboardPage("overview")}
          >
            ◈ Overview
          </button>
          <button
            className={dashboardPage === "command" ? "active" : ""}
            onClick={() => setDashboardPage("command")}
          >
            ⊞ Command Center
          </button>
          <button
            className={dashboardPage === "scans" ? "active" : ""}
            onClick={() => setDashboardPage("scans")}
          >
            ⌕ Scans
          </button>
          <button
            className={dashboardPage === "history" ? "active" : ""}
            onClick={() => setDashboardPage("history")}
          >
            ◷ History
          </button>
          <button
            className={dashboardPage === "tools" ? "active" : ""}
            onClick={() => setDashboardPage("tools")}
          >
            ⚒ Tools
          </button>
          <button
            className={dashboardPage === "reports" ? "active" : ""}
            onClick={() => setDashboardPage("reports")}
          >
            ▤ Reports
          </button>
          <button
            className={dashboardPage === "settings" ? "active" : ""}
            onClick={() => setDashboardPage("settings")}
          >
            ⚙ Settings
          </button>
        </nav>

        <div className="planCard">
          <h4>Enterprise Plan</h4>
          <p>84 / 1500 scans used</p>
          <div className="progressBar">
            <span></span>
          </div>
          <button>Upgrade Plan →</button>
        </div>
      </aside>

      <main className="dashboardMain">
        <header className="dashboardTop">
          <div>
            <h1>
              Welcome back, <span>{user?.name || "Team AsystQA"}</span> 👋
            </h1>
            <p>Here’s what’s happening with your code quality today.</p>
          </div>

          <div className="topTools">
            <div className="searchBox">
              🔍
              <input placeholder="Search scans, files, issues..." />
              <kbd>⌘ K</kbd>
            </div>

            <button className="bellButton">
              🔔 <span>3</span>
            </button>

            <div className="profileBox">
              <div>{user?.initials || "TA"}</div>
              <section>
                <strong>{user?.name || "Team AsystQA"}</strong>
                <small>{user?.role || "Admin"}</small>
              </section>
            </div>
          </div>
        </header>

        {dashboardPage === "overview" && (
          <OverviewDashboard
            code={code}
            setCode={setCode}
            fileName={fileName}
            handleUpload={handleUpload}
            report={report}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            isScanning={isScanning}
            runScan={runScan}
            copyReport={copyReport}
            downloadReport={downloadReport}
          />
        )}

        {dashboardPage === "command" && (
          <CommandCenterPage
            code={code}
            setCode={setCode}
            fileName={fileName}
            handleUpload={handleUpload}
            runScan={runScan}
            isScanning={isScanning}
          />
        )}

        {dashboardPage === "scans" && <ScansPage />}
        {dashboardPage === "history" && <HistoryPage />}
        {dashboardPage === "tools" && <ToolsPage />}
        {dashboardPage === "reports" && (
          <ReportsPage
            report={report}
            fileName={fileName}
            copyReport={copyReport}
            downloadReport={downloadReport}
          />
        )}
        {dashboardPage === "settings" && <SettingsPage user={user} logout={logout} />}
      </main>
    </section>
  );
}

function OverviewDashboard({
  code,
  setCode,
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
  return (
    <>
      <section className="metricsGrid">
        <MetricScore score={report.score} />
        <MetricCard title="Active Scans" value="4" text="In Progress" footer="2 High · 1 Medium · 1 Low" />
        <MetricCard title="Issues Found" value={report.issueCount} text="Detected today" footer="12 High · 10 Medium · 6 Low" />
        <MetricRisk risk={report.risk} />
      </section>

      <section className="workspaceGrid">
        <CodePanel
          code={code}
          setCode={setCode}
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
        <RecentScans />
        <QuickActions />
      </section>
    </>
  );
}

function CodePanel({ code, setCode, fileName, handleUpload, runScan, isScanning }) {
  return (
    <div className="codePanel">
      <div className="panelHeader">
        <h2>Analyze Your Code</h2>
        <select>
          <option>Auto Detect</option>
          <option>JavaScript</option>
          <option>Python</option>
          <option>PHP</option>
          <option>Java</option>
        </select>
      </div>

      <div className="inputTabs">
        <button className="active">▣ Paste Code</button>
        <label>
          ⬆ Upload File
          <input type="file" accept=".js,.jsx,.py,.php,.java,.html,.css,.txt" onChange={handleUpload} />
        </label>
        <button>⌘ Git Repository</button>
      </div>

      <div className="codeEditor">
        <div className="lineNumbers">
          {code.split("\n").map((_, index) => (
            <span key={index}>{index + 1}</span>
          ))}
        </div>

        <textarea value={code} onChange={(e) => setCode(e.target.value)} />
      </div>

      <div className="editorFooter">
        <div>
          <select>
            <option>JavaScript</option>
            <option>Python</option>
            <option>PHP</option>
            <option>Java</option>
          </select>

          <span>{fileName}</span>
        </div>

        <button onClick={runScan}>{isScanning ? "Scanning..." : "✦ Generate QA Report"}</button>
      </div>

      <p className="helperText">AI will analyze your code and generate a detailed report.</p>
    </div>
  );
}

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
            <p>
              The scan found {report.issueCount} possible issues. The main focus should be input validation,
              security checks, and edge-case testing.
            </p>
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

function CommandCenterPage({ code, setCode, fileName, handleUpload, runScan, isScanning }) {
  return (
    <div className="singlePageGrid">
      <CodePanel
        code={code}
        setCode={setCode}
        fileName={fileName}
        handleUpload={handleUpload}
        runScan={runScan}
        isScanning={isScanning}
      />
    </div>
  );
}

function ScansPage() {
  return (
    <div className="simplePageCard">
      <h2>Scans</h2>
      <p>Track current and previous QA scans across your project files.</p>

      <div className="simpleList">
        <span>Authentication Module — Completed — 88/100</span>
        <span>Payment API — Completed — 94/100</span>
        <span>Data Validation Service — Completed — 76/100</span>
      </div>
    </div>
  );
}

function HistoryPage() {
  return (
    <div className="simplePageCard">
      <h2>History</h2>
      <p>Previous reports and scan records are stored here for demo review.</p>

      <RecentScans />
    </div>
  );
}

function ToolsPage() {
  return (
    <div className="simplePageCard">
      <h2>Tools</h2>
      <p>AsystQA uses specialist agents to complete the QA workflow.</p>

      <div className="toolsGrid">
        <ToolCard title="Reviewer Agent" text="Checks code quality, structure, repeated logic, and maintainability." />
        <ToolCard title="Security Agent" text="Detects hardcoded secrets, unsafe logic, and risky patterns." />
        <ToolCard title="Tester Agent" text="Generates useful test ideas for edge cases and validation." />
        <ToolCard title="Reporter Agent" text="Builds the final QA score, risk level, and report summary." />
      </div>
    </div>
  );
}

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

function SettingsPage({ user, logout }) {
  return (
    <div className="simplePageCard">
      <h2>Settings</h2>
      <p>Manage your demo account session.</p>

      <div className="settingsBox">
        <strong>{user?.name}</strong>
        <span>{user?.email}</span>
        <span>{user?.role}</span>
      </div>

      <button className="logoutButton" onClick={logout}>
        Log Out
      </button>
    </div>
  );
}

function ToolCard({ title, text }) {
  return (
    <div className="toolCard">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function MetricScore({ score }) {
  return (
    <div className="metricCard scoreMetric">
      <h3>QA Score ⓘ</h3>
      <div className="metricFlex">
        <div className="smallDonut">
          <strong>{score}</strong>
          <small>/100</small>
        </div>

        <div>
          <h2>Excellent</h2>
          <p>Code quality looks great. Keep it up.</p>
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

function MetricRisk({ risk }) {
  return (
    <div className="metricCard riskMetric">
      <h3>Risk Level ⓘ</h3>

      <div className="riskBlock">
        <div>🛡</div>
        <section>
          <h2>{risk}</h2>
          <p>Some vulnerabilities need attention.</p>
        </section>
      </div>

      <a>View risks →</a>
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

function MiniStep({ title, status, orange, blue }) {
  return (
    <div className="miniStep">
      <div className={`${orange ? "orange" : ""} ${blue ? "blue" : ""}`}></div>
      <strong>{title}</strong>
      <span>{status}</span>
    </div>
  );
}

function RecentScans() {
  const scans = [
    ["User Authentication Module", "JS", "Completed", "88 / 100", "14 Issues", "2h ago"],
    ["Payment Processing API", "PY", "Completed", "94 / 100", "8 Issues", "5h ago"],
    ["Data Validation Service", "JS", "Completed", "76 / 100", "22 Issues", "1 day ago"],
  ];

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
            {scan.map((item, itemIndex) => (
              <span key={itemIndex}>{item}</span>
            ))}
          </div>
        ))}
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

function createReport(code) {
  const issues = [];

  if (code.includes("<=") && code.includes(".length")) {
    issues.push({
      severity: "High",
      title: "Potential Array Out of Bounds",
      text: "Loop condition may allow an index outside the array range.",
    });
  }

  if (code.includes("password") || code.includes("admin123")) {
    issues.push({
      severity: "High",
      title: "Possible Hardcoded Secret",
      text: "A password-like value appears to be written directly in the code.",
    });
  }

  if (!code.toLowerCase().includes("if") && code.includes("items")) {
    issues.push({
      severity: "Medium",
      title: "Missing Input Validation",
      text: "The function does not clearly validate input before using it.",
    });
  }

  if (code.includes("console.log") || code.includes("print(")) {
    issues.push({
      severity: "Low",
      title: "Debug Output Found",
      text: "Remove debug output before production deployment.",
    });
  }

  if (issues.length === 0) {
    issues.push({
      severity: "Low",
      title: "No Major Issue Found",
      text: "The code looks clean based on this rule-based scan.",
    });
  }

  return {
    score: 92,
    risk: "Medium",
    issueCount: 28,
    issues,
    tests: [
      { title: "Test empty items array", type: "Edge Case" },
      { title: "Test with negative prices", type: "Validation" },
      { title: "Test large dataset", type: "Performance" },
      { title: "Test null input", type: "Error Handling" },
      { title: "Test normal valid input", type: "Functional" },
    ],
  };
}

function makeReportText(report, fileName) {
  return `AsystQA Command Center Report

File: ${fileName}
QA Score: ${report.score}/100
Risk Level: ${report.risk}
Issues Found: ${report.issueCount}

Issues:
${report.issues.map((issue, index) => `${index + 1}. [${issue.severity}] ${issue.title} - ${issue.text}`).join("\n")}

Suggested Tests:
${report.tests.map((test, index) => `${index + 1}. ${test.title} (${test.type})`).join("\n")}
`;
}

export default App;