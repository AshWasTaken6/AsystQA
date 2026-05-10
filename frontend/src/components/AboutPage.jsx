import MarketingNav from "./MarketingNav";

function AboutPage({ openLanding, openPricing, openAbout, openDashboard, openLogin }) {
  return (
    <section className="marketingPage aboutPage">
      <MarketingNav
        activePage="about"
        openLanding={openLanding}
        openPricing={openPricing}
        openAbout={openAbout}
        openDashboard={openDashboard}
        openLogin={openLogin}
      />

      <main className="marketingMain">
        <section className="pageHero aboutHero">
          <h1>A focused space for the story you will add later.</h1>
          <p>
            This page is ready for your final About copy. For now, it keeps the product promise
            clear: AI-assisted code review, security checks, test ideas, and report building in
            one command center.
          </p>
          <button className="orangeButton" onClick={openDashboard}>
            Open Command Center
          </button>
        </section>

        <section className="aboutPlaceholder">
          <div>
            <span>01</span>
            <strong>Mission copy</strong>
            <p>Add the founder or product mission here when it is ready.</p>
          </div>
          <div>
            <span>02</span>
            <strong>Who it helps</strong>
            <p>Use this space for developers, QA teams, students, or security reviewers.</p>
          </div>
          <div>
            <span>03</span>
            <strong>Why it matters</strong>
            <p>Explain the quality, speed, and confidence AsystQA brings to reviews.</p>
          </div>
        </section>
      </main>
    </section>
  );
}

export default AboutPage;
