function MarketingNav({
  activePage,
  openLanding,
  openPricing,
  openAbout,
  openDashboard,
  openLogin,
}) {
  return (
    <header className="landingNav">
      <button className="landingLogo" onClick={openLanding} aria-label="Go to welcome page">
        <img src="/logo.png" alt="AsystQA Logo" />
      </button>

      <nav aria-label="Main navigation">
        <button onClick={openDashboard}>Dashboard</button>
        <button onClick={openDashboard}>Tools</button>
        <button
          className={activePage === "pricing" ? "active" : ""}
          onClick={openPricing}
        >
          Pricing
        </button>
        <button className={activePage === "about" ? "active" : ""} onClick={openAbout}>
          About
        </button>
      </nav>

      <div className="navActions">
        <button className="ghostButton" onClick={openLogin}>
          Sign In
        </button>
        <button className="orangeButton" onClick={openDashboard}>
          Launch Command Center
        </button>
      </div>
    </header>
  );
}

export default MarketingNav;
