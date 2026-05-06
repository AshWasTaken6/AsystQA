import { useState } from "react";

function App() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Python");
  const [result, setResult] = useState(null);

  function analyzeCode() {
    setResult({
      score: 82,
      totalIssues: 3,
      agentsUsed: 5,
      workflow: [
        "Planner Agent: Complete",
        "Reviewer Agent: Complete",
        "Security Agent: Complete",
        "Test Agent: Complete",
        "Report Agent: Complete"
      ],
      bugs: ["Unused variable detected", "Function is too long"],
      security: ["No input sanitization detected"],
      tests: ["test_login()", "test_register()"],
      summary: "Good structure, but some issues need fixing."
    });
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>AsystQA Command Center</h1>
        <p style={styles.subtitle}>Your AI Software QA Team in One Click</p>
      </div>

      <div style={styles.statsRow}>
        <StatCard title="Agents" value={result ? result.agentsUsed : 5} />
        <StatCard title="QA Score" value={result ? `${result.score}/100` : "--"} />
        <StatCard title="Issues" value={result ? result.totalIssues : "--"} />
      </div>

      <div style={styles.mainGrid}>
        <div style={styles.panel}>
          <h2>Code Input</h2>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={styles.select}
          >
            <option>Python</option>
            <option>JavaScript</option>
            <option>PHP</option>
          </select>

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your code here..."
            style={styles.textarea}
          />

          <button onClick={analyzeCode} style={styles.button}>
            Analyze Code
          </button>
        </div>

        <div style={styles.resultsColumn}>
          {!result ? (
            <div style={styles.panel}>
              <h2>Results</h2>
              <p style={styles.muted}>Run an analysis to see results.</p>
            </div>
          ) : (
            <>
              <Card title="Agent Workflow" items={result.workflow} />
              <Card title="Bugs Found" items={result.bugs} />
              <Card title="Security Risks" items={result.security} />
              <Card title="Tests Generated" items={result.tests} />
              <Card title="Summary" items={[result.summary]} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div style={styles.statCard}>
      <p style={styles.statTitle}>{title}</p>
      <h2 style={styles.statValue}>{value}</h2>
    </div>
  );
}

function Card({ title, items }) {
  return (
    <div style={styles.panel}>
      <h2>{title}</h2>
      <ul>
        {items.map((item, index) => (
          <li key={index} style={{ marginBottom: "8px" }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

const styles = {
  page: {
    backgroundColor: "#0f172a",
    minHeight: "100vh",
    color: "white",
    padding: "40px",
    fontFamily: "Arial"
  },
  header: {
    marginBottom: "25px"
  },
  title: {
    fontSize: "42px",
    marginBottom: "10px"
  },
  subtitle: {
    color: "#94a3b8",
    fontSize: "18px"
  },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: "20px",
    marginBottom: "25px"
  },
  statCard: {
    backgroundColor: "#1e293b",
    padding: "20px",
    borderRadius: "14px"
  },
  statTitle: {
    color: "#94a3b8",
    margin: 0
  },
  statValue: {
    fontSize: "30px",
    margin: "10px 0 0"
  },
  mainGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px"
  },
  panel: {
    backgroundColor: "#1e293b",
    padding: "20px",
    borderRadius: "14px"
  },
  select: {
    width: "100%",
    padding: "10px",
    marginBottom: "20px",
    borderRadius: "8px"
  },
  textarea: {
    width: "100%",
    height: "300px",
    padding: "15px",
    borderRadius: "10px",
    resize: "none"
  },
  button: {
    marginTop: "20px",
    width: "100%",
    padding: "15px",
    backgroundColor: "#3b82f6",
    color: "white",
    border: "none",
    borderRadius: "10px",
    fontSize: "16px",
    cursor: "pointer"
  },
  resultsColumn: {
    display: "flex",
    flexDirection: "column",
    gap: "20px"
  },
  muted: {
    color: "#94a3b8"
  }
};

export default App;