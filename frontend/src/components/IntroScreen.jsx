function IntroScreen({ openDashboard, openLanding }) {
  return (
    <section className="introScreen">
      <video className="introVideo" autoPlay muted loop playsInline>
        <source src="/intro.mp4" type="video/mp4" />
      </video>

      <div className="introDarkLayer"></div>

      <button className="introTinyLogo" onClick={openLanding} title="Open welcome page">
        <img src="/logo.png" alt="AsystQA Logo" />
      </button>

      <div className="introHeroText">
        <p>AI Agents for Software QA</p>
        <h1>AsystQA Command Center</h1>
        <span>Review code, find issues, generate tests, and build QA reports.</span>

        <div className="introHeroActions">
          <button className="introPrimaryBtn" onClick={openDashboard}>
            Enter Command Center →
          </button>

          <button className="introSecondaryBtn" onClick={openLanding}>
            View Welcome Page
          </button>
        </div>
      </div>
    </section>
  );
}

export default IntroScreen;
