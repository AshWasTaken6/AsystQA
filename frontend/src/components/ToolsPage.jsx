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

function ToolCard({ title, text }) {
  return (
    <div className="toolCard">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export default ToolsPage;
