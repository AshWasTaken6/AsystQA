import MarketingNav from "./MarketingNav";

const plans = [
  {
    name: "Starter",
    price: "$0",
    cadence: "forever",
    description: "For trying AsystQA on small snippets and demo scans.",
    features: ["5 QA scans per month", "Basic code review", "Security issue summary"],
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "per seat / month",
    description: "For developers who want repeatable QA reports before every merge.",
    features: ["Unlimited scans", "Test generation", "Exportable reports", "Scan history"],
    featured: true,
  },
  {
    name: "Team",
    price: "$99",
    cadence: "per team / month",
    description: "For teams coordinating reviews, risk tracking, and delivery workflows.",
    features: ["Shared dashboard", "Priority workflows", "Role-based access", "Team reports"],
  },
];

function PricingPage({ openLanding, openPricing, openAbout, openDashboard, openLogin }) {
  return (
    <section className="marketingPage pricingPage">
      <MarketingNav
        activePage="pricing"
        openLanding={openLanding}
        openPricing={openPricing}
        openAbout={openAbout}
        openDashboard={openDashboard}
        openLogin={openLogin}
      />

      <main className="marketingMain">
        <section className="pageHero compactHero">
          <h1>Plans for cleaner QA handoffs.</h1>
          <p>
            Choose a mock plan while the billing model is still being shaped. These prices are
            placeholders and can be swapped once you finalize the offer.
          </p>
        </section>

        <section className="pricingGrid" aria-label="Pricing plans">
          {plans.map((plan) => (
            <article
              className={`pricingCard ${plan.featured ? "featured" : ""}`}
              key={plan.name}
            >
              <div>
                <span className="planName">{plan.name}</span>
                <p>{plan.description}</p>
              </div>

              <div className="priceLine">
                <strong>{plan.price}</strong>
                <span>{plan.cadence}</span>
              </div>

              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>

              <button
                className={plan.featured ? "orangeButton fullWidth" : "ghostButton fullWidth"}
                onClick={openDashboard}
              >
                {plan.featured ? "Start Pro Trial" : "Choose Plan"}
              </button>
            </article>
          ))}
        </section>
      </main>
    </section>
  );
}

export default PricingPage;
