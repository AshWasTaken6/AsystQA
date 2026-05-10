import CodePanel from './CodePanel';

function CommandCenterPage({ code, setCode, language, setLanguage, fileName, handleUpload, runScan, isScanning }) {
  return (
    <div className="singlePageGrid">
      <CodePanel
        code={code}
        setCode={setCode}
        language={language}
        setLanguage={setLanguage}
        fileName={fileName}
        handleUpload={handleUpload}
        runScan={runScan}
        isScanning={isScanning}
      />
    </div>
  );
}

export default CommandCenterPage;
