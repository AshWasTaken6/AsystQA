import { useState } from "react";

function App() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Python");
  const [result, setResult] = useState(null);

  function analyzeCode() {
    setResult({
      score: 82,
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
    <div style={{ backgroundColor: "#0f172a", minHeight: "100vh", color: "white", padding: "40px", fontFamily: "Arial" }}>
      <h1>AsystQA Command Center</h1>
      <p style={{ color: "#94a3b8" }}>Your AI Software QA Team in One Click</p>

      <div style={{ display: "flex", gap: "20px", marginTop: "30px" }}>
        <div style={{ flex: 1, backgroundColor: "#1e293b", padding: "20px", borderRadius: "12px" }}>
          <h2>Code Input</h2>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ width: "100%", padding: "10px", marginBottom: "20px", borderRadius: "8px" }}
          >
            <option>Python</option>
            <option>JavaScript</option>
            <option>PHP</option>
          </select>

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your code here..."
            style={{ width: "100%", height: "300px", padding: "15px", borderRadius: "10px", resize: "none" }}
          />

          <button
            onClick={analyzeCode}
            style={{
              marginTop: "20px",
              width: "100%",
              padding: "15px",
              backgroundColor: "#3b82f6",
              color: "white",
              border: "none",
              borderRadius: "10px",
              fontSize: "16px",
              cursor: "pointer"
            }}
          >
            Analyze Code
          </button>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "20px" }}>
          {!result ? (
            <div style={{ backgroundColor: "#1e293b", padding: "20px", borderRadius: "12px" }}>
              <h2>Results</h2>
              <p style={{ color: "#94a3b8" }}>Run an analysis to see results.</p>
            </div>
          ) : (
            <>
              <Card title="Agent Workflow" items={result.workflow} />
              <Card title="QA Score" items={[`${result.score} / 100`]} />
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

function Card({ title, items }) {
  return (
    <div style={{ backgroundColor: "#1e293b", padding: "20px", borderRadius: "12px" }}>
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

export default App;