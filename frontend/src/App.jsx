import { useState } from "react";
import "./App.css";

function App() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Python");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  function analyzeCode() {
    setLoading(true);
    setResult(null);

    setTimeout(() => {
      setResult({
        score: 82,
        level: "Good",
        issues: 3,
        agents: 5,
        workflow: [
          { name: "Planner Agent", status: "Complete", detail: "Created QA workflow" },
          { name: "Reviewer Agent", status: "Complete", detail: "Checked bugs and code quality" },
          { name: "Security Agent", status: "Complete", detail: "Scanned risky patterns" },
          { name: "Test Agent", status: "Complete", detail: "Generated test ideas" },
          { name: "Report Agent", status: "Complete", detail: "Built final QA report" }
        ],
        bugs: ["Unused variable detected", "Function is too long"],
        security: ["Input is not sanitized"],
        tests: ["test_login()", "test_register()", "test_empty_input()"],
        summary:
          "The code has a good base, but it needs better input checks, shorter functions, and stronger testing."
      });
      setLoading(false);
    }, 1200);
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="badge">AMD Developer Hackathon • AI Agents Track</p>
          <h1>AsystQA Command Center</h1>
          <p className="subtitle">Your AI Software QA Team in One Click</p>
        </div>
      </header>

      <section className="stats">
        <Stat title="Agents Used" value={result ? result.agents : 5} />
        <Stat title="QA Score" value={result ? `${result.score}/100` : "--"} />
        <Stat title="Issues Found" value={result ? result.issues : "--"} />
        <Stat title="Status" value={loading ? "Running" : result ? "Complete" : "Ready"} />
      </section>

      <main className="grid">
        <section className="panel input-panel">
          <h2>Code Input</h2>

          <label>Language</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option>Python</option>
            <option>JavaScript</option>
            <option>PHP</option>
          </select>

          <label>Paste Code</label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={`Paste your ${language} code here...`}
          />

          <button onClick={analyzeCode} disabled={loading || code.trim() === ""}>
            {loading ? "Agents Running..." : "Analyze Code"}
          </button>
        </section>

        <section className="panel">
          <h2>Agent Workflow</h2>

          {!result && !loading && (
            <p className="muted">Run an analysis to activate the agent workflow.</p>
          )}

          {loading && (
            <div className="loading-box">
              <div className="loader"></div>
              <p>Agents are reviewing your code...</p>
            </div>
          )}

          {result && (
            <div className="workflow">
              {result.workflow.map((agent, index) => (
                <div className="agent-card" key={index}>
                  <div className="agent-dot"></div>
                  <div>
                    <h3>{agent.name}</h3>
                    <p>{agent.detail}</p>
                    <span>{agent.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {result && (
        <section className="results">
          <ResultCard title="Bugs Found" items={result.bugs} />
          <ResultCard title="Security Risks" items={result.security} />
          <ResultCard title="Tests Generated" items={result.tests} />
          <ResultCard title="Final Summary" items={[result.summary]} />
        </section>
      )}
    </div>
  );
}

function Stat({ title, value }) {
  return (
    <div className="stat-card">
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}

function ResultCard({ title, items }) {
  return (
    <div className="result-card">
      <h2>{title}</h2>
      <ul>
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;