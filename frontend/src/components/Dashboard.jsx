import OverviewDashboard from './OverviewDashboard';
import CommandCenterPage from './CommandCenterPage';
import ScansPage from './ScansPage';
import HistoryPage from './HistoryPage';
import ToolsPage from './ToolsPage';
import ReportsPage from './ReportsPage';
import SettingsPage from './SettingsPage';

function Dashboard({
  user,
  logout,
  dashboardPage,
  setDashboardPage,
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
  return (
    <section className="dashboardPage">
      <aside className="sidebar">
        <div className="sidebarLogo">
          <img src="/logo.png" alt="AsystQA Logo" />
          <span>AGENT HUB</span>
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
            ⊞ Agent Workflow
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
            language={language}
            setLanguage={setLanguage}
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
            language={language}
            setLanguage={setLanguage}
            fileName={fileName}
            handleUpload={handleUpload}
            runScan={runScan}
            isScanning={isScanning}
          />
        )}

        {dashboardPage === "scans" && (
          <ScansPage
            onStartNewScan={() => {
              setDashboardPage("command");
            }}
          />
        )}
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

export default Dashboard;
