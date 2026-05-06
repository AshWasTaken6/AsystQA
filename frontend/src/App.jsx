function App() {
  return (
    <div style={{
      backgroundColor: "#0f172a",
      minHeight: "100vh",
      color: "white",
      padding: "40px",
      fontFamily: "Arial"
    }}>

      <h1 style={{ fontSize: "42px", marginBottom: "10px" }}>
        AsystQA Command Center
      </h1>

      <p style={{ color: "#94a3b8", marginBottom: "30px" }}>
        Your AI Software QA Team in One Click
      </p>

      <div style={{
        display: "flex",
        gap: "20px"
      }}>

        {/* LEFT SIDE */}
        <div style={{
          flex: 1,
          backgroundColor: "#1e293b",
          padding: "20px",
          borderRadius: "12px"
        }}>

          <h2>Code Input</h2>

          <select style={{
            width: "100%",
            padding: "10px",
            marginBottom: "20px",
            borderRadius: "8px"
          }}>
            <option>Python</option>
            <option>JavaScript</option>
            <option>PHP</option>
          </select>

          <textarea
            placeholder="Paste your code here..."
            style={{
              width: "100%",
              height: "300px",
              padding: "15px",
              borderRadius: "10px",
              border: "none",
              resize: "none"
            }}
          />

          <button style={{
            marginTop: "20px",
            width: "100%",
            padding: "15px",
            backgroundColor: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "10px",
            fontSize: "16px",
            cursor: "pointer"
          }}>
            Analyze Code
          </button>

        </div>

        {/* RIGHT SIDE */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: "20px"
        }}>

          <div style={{
            backgroundColor: "#1e293b",
            padding: "20px",
            borderRadius: "12px"
          }}>
            <h2>QA Score</h2>
            <p>82 / 100</p>
          </div>

          <div style={{
            backgroundColor: "#1e293b",
            padding: "20px",
            borderRadius: "12px"
          }}>
            <h2>Bugs Found</h2>
            <ul>
              <li>Unused variable detected</li>
            </ul>
          </div>

          <div style={{
            backgroundColor: "#1e293b",
            padding: "20px",
            borderRadius: "12px"
          }}>
            <h2>Security Risks</h2>
            <ul>
              <li>No sanitization detected</li>
            </ul>
          </div>

          <div style={{
            backgroundColor: "#1e293b",
            padding: "20px",
            borderRadius: "12px"
          }}>
            <h2>Tests Generated</h2>
            <ul>
              <li>test_login()</li>
            </ul>
          </div>

        </div>

      </div>

    </div>
  )
}

export default App