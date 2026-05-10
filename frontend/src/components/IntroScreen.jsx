function IntroScreen({ openDashboard, openLanding }) {
  return (
    <section className="introScreen" onClick={openLanding}>
      <video className="introVideo" autoPlay muted loop playsInline>
        <source src="/intro.mp4" type="video/mp4" />
      </video>

      <div className="introDarkLayer"></div>

      <button
        className="introTinyLogo"
        onClick={(event) => {
          event.stopPropagation();
          openLanding();
        }}
        title="Open welcome page"
      >
        <img src="/logo.png" alt="AsystQA Logo" />
      </button>

      <div className="introHeroText">
        <h1>
          AsystQA <br />
          Command Center
        </h1>

        <span>
          AI agents that review code, detect risks, and generate QA reports.
        </span>

        <div className="introHeroActions">
          <button
            className="introPrimaryBtn"
            onClick={(event) => {
              event.stopPropagation();
              openDashboard("overview");
            }}
          >
            Enter Command Center 
          </button>
        </div>
      </div>
    </section>
  );
}

export default IntroScreen;