function CodePanel({ code, setCode, language, setLanguage, fileName, handleUpload, runScan, isScanning }) {
  return (
    <div className="codePanel">
      <div className="panelHeader">
        <h2>Analyze Your Code</h2>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
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
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
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

export default CodePanel;
