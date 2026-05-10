import { useEffect, useState } from "react";
import "./App.css";
import IntroScreen from "./components/IntroScreen";
import LoginModal from "./components/LoginModal";
import LandingPage from "./components/WelcomePage";
import PricingPage from "./components/PricingPage";
import AboutPage from "./components/AboutPage";
import Dashboard from "./components/Dashboard";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const USERS_STORAGE_KEY = "asystqa.users";
const AUTH_STORAGE_KEY = "asystqa.authUser";

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

function loadUsers() {
  try {
    const storedUsers = JSON.parse(
      localStorage.getItem(USERS_STORAGE_KEY) || "[]"
    );

    if (!Array.isArray(storedUsers)) {
      return demoUsers;
    }

    const storedEmails = new Set(
      storedUsers.map((storedUser) => storedUser.email?.toLowerCase())
    );

    const missingDemoUsers = demoUsers.filter(
      (demoUser) => !storedEmails.has(demoUser.email.toLowerCase())
    );

    return [...missingDemoUsers, ...storedUsers];
  } catch {
    return demoUsers;
  }
}

function saveUsers(nextUsers) {
  const customUsers = nextUsers.filter(
    (nextUser) =>
      !demoUsers.some(
        (demoUser) =>
          demoUser.email.toLowerCase() === nextUser.email.toLowerCase()
      )
  );

  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(customUsers));
}

function getSafeUser(user) {
  return {
    name: user.name,
    role: user.role,
    email: user.email,
    initials: user.initials,
  };
}

function App() {
  const [screen, setScreen] = useState("intro");
  const [dashboardPage, setDashboardPage] = useState("overview");
  const [showLogin, setShowLogin] = useState(false);
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState(loadUsers);

  const [code, setCode] = useState(sampleCode);
  const [language, setLanguage] = useState("JavaScript");
  const [fileName, setFileName] = useState("sample-code.js");
  const [activeTab, setActiveTab] = useState("workflow");
  const [isScanning, setIsScanning] = useState(false);
  const [toast, setToast] = useState("");
  const [report, setReport] = useState({
    score: 0,
    risk: "Unknown",
    issueCount: 0,
    issues: [],
    tests: [],
    summary: "",
    processing_time: 0,
    insights: {},
  });

  useEffect(() => {
    saveUsers(users);
  }, [users]);

  useEffect(() => {
    try {
      const savedUser = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY));

      if (savedUser) {
        setUser(savedUser);
        setScreen("dashboard");
      }
    } catch {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, []);

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

  function openPricing() {
    setScreen("pricing");
  }

  function openAbout() {
    setScreen("about");
  }

  function login(email, password, rememberMe = false) {
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedPassword = password.trim();

    const foundUser = users.find(
      (demoUser) =>
        demoUser.email.toLowerCase() === normalizedEmail &&
        demoUser.password === normalizedPassword
    );

    if (!foundUser) {
      showToast("Wrong email or password");
      return false;
    }

    const safeUser = getSafeUser(foundUser);

    setUser(safeUser);

    if (rememberMe) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(safeUser));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }

    setShowLogin(false);
    setScreen("dashboard");
    showToast(`Welcome, ${safeUser.name}`);
    return true;
  }

  function register(email, password, name, rememberMe = false) {
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedPassword = password.trim();
    const normalizedName = name.trim();

    if (!normalizedEmail || !normalizedPassword) {
      showToast("Email and password are required");
      return false;
    }

    const existingUser = users.find(
      (demoUser) => demoUser.email.toLowerCase() === normalizedEmail
    );

    if (existingUser) {
      showToast("An account with that email already exists");
      return false;
    }

    const newUser = {
      name: normalizedName || "New User",
      role: "User",
      email: normalizedEmail,
      password: normalizedPassword,
      initials: (normalizedName || "NU")
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase(),
    };

    const safeUser = getSafeUser(newUser);

    setUsers((prevUsers) => [...prevUsers, newUser]);
    setUser(safeUser);

    if (rememberMe) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(safeUser));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }

    setShowLogin(false);
    setScreen("dashboard");
    showToast(`Welcome, ${safeUser.name}`);
    return true;
  }

  function logout() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
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

  async function runScan() {
    if (!code.trim()) {
      showToast("Paste or upload code first");
      return;
    }

    setIsScanning(true);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();
      const reporter = data.reporter || {};

      setReport({
        score: reporter.score ?? 0,
        risk: reporter.risk ?? "Unknown",
        issueCount: reporter.issueCount ?? 0,
        issues: reporter.issues ?? [],
        tests: reporter.tests ?? [],
        summary: reporter.summary ?? "",
        processing_time: data.processing_time ?? 0,
        insights: data.insights ?? {},
      });

      setActiveTab("workflow");
      setDashboardPage("overview");
      showToast("QA report generated");
    } catch (error) {
      console.error(error);
      showToast("Report generation failed");
    } finally {
      setIsScanning(false);
    }
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
        <IntroScreen openDashboard={openDashboard} openLanding={openLanding} />
      )}

      {screen === "landing" && (
        <LandingPage
          openDashboard={openDashboard}
          openLogin={() => setShowLogin(true)}
          openLanding={openLanding}
          openPricing={openPricing}
          openAbout={openAbout}
        />
      )}

      {screen === "pricing" && (
        <PricingPage
          openLanding={openLanding}
          openPricing={openPricing}
          openAbout={openAbout}
          openDashboard={openDashboard}
          openLogin={() => setShowLogin(true)}
        />
      )}

      {screen === "about" && (
        <AboutPage
          openLanding={openLanding}
          openPricing={openPricing}
          openAbout={openAbout}
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

      {showLogin && (
        <LoginModal
          login={login}
          register={register}
          closeLogin={() => setShowLogin(false)}
        />
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

function makeReportText(report, fileName) {
  return `AsystQA Command Center Report

File: ${fileName}
QA Score: ${report.score}/100
Risk Level: ${report.risk}
Issues Found: ${report.issueCount}

Issues:
${report.issues
  .map(
    (issue, index) =>
      `${index + 1}. [${issue.severity}] ${issue.title} - ${issue.text}`
  )
  .join("\n")}

Suggested Tests:
${report.tests
  .map((test, index) => `${index + 1}. ${test.title} (${test.type})`)
  .join("\n")}
`;
}

export default App;