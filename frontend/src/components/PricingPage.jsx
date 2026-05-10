import { useState } from "react";
import MarketingNav from "./MarketingNav";

const monthlyPlans = [
  {
    name: "Starter",
    price: "$0",
    period: "free",
    description:
      "For students, demos, and solo developers exploring structured QA workflows.",
    highlight: "",
    button: "Start Free",
    buttonType: "secondary",
    features: [
      "5 scans per month",
      "Paste code analysis",
      "Basic QA score",
      "Issue summary",
      "Suggested test ideas",
      "Community support",
    ],
  },
  {
    name: "Pro",
    price: "$24",
    period: "per user / month",
    description:
      "For developers who want repeatable QA reviews before every push or merge.",
    highlight: "Most Popular",
    button: "Start Pro Trial",
    buttonType: "primary",
    features: [
      "Unlimited scans",
      "Upload file analysis",
      "Security scan agent",
      "Downloadable QA reports",
      "Scan history",
      "Priority report generation",
    ],
  },
  {
    name: "Team",
    price: "$99",
    period: "per team / month",
    description:
      "For startups and engineering teams coordinating reviews, risks, and handoffs.",
    highlight: "",
    button: "Choose Team",
    buttonType: "secondary",
    features: [
      "Everything in Pro",
      "Shared team dashboard",
      "Role-based access",
      "Team report history",
      "Priority workflows",
      "Collaboration-ready QA reviews",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "contact sales",
    description:
      "For organizations that need advanced governance, integrations, and deployment flexibility.",
    highlight: "",
    button: "Talk to Sales",
    buttonType: "secondary",
    features: [
      "Private deployment options",
      "Advanced security rules",
      "Custom QA policies",
      "CI/CD integration roadmap",
      "GitHub workflow integration",
      "Dedicated onboarding support",
    ],
  },
];

const annualPlans = [
  {
    name: "Starter",
    price: "$0",
    period: "free",
    description:
      "For students, demos, and solo developers exploring structured QA workflows.",
    highlight: "",
    button: "Start Free",
    buttonType: "secondary",
    features: [
      "5 scans per month",
      "Paste code analysis",
      "Basic QA score",
      "Issue summary",
      "Suggested test ideas",
      "Community support",
    ],
  },
  {
    name: "Pro",
    price: "$19",
    period: "per user / month, billed annually",
    description:
      "For developers who want repeatable QA reviews before every push or merge.",
    highlight: "Most Popular",
    button: "Start Pro Trial",
    buttonType: "primary",
    features: [
      "Unlimited scans",
      "Upload file analysis",
      "Security scan agent",
      "Downloadable QA reports",
      "Scan history",
      "Priority report generation",
    ],
  },
  {
    name: "Team",
    price: "$79",
    period: "per team / month, billed annually",
    description:
      "For startups and engineering teams coordinating reviews, risks, and handoffs.",
    highlight: "",
    button: "Choose Team",
    buttonType: "secondary",
    features: [
      "Everything in Pro",
      "Shared team dashboard",
      "Role-based access",
      "Team report history",
      "Priority workflows",
      "Collaboration-ready QA reviews",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "contact sales",
    description:
      "For organizations that need advanced governance, integrations, and deployment flexibility.",
    highlight: "",
    button: "Talk to Sales",
    buttonType: "secondary",
    features: [
      "Private deployment options",
      "Advanced security rules",
      "Custom QA policies",
      "CI/CD integration roadmap",
      "GitHub workflow integration",
      "Dedicated onboarding support",
    ],
  },
];

function PricingPage({
  openDashboard,
  openLogin,
  openLanding,
  openPricing,
  openAbout,
}) {
  const [annual, setAnnual] = useState(false);
  const plans = annual ? annualPlans : monthlyPlans;

  return (
    <section className="pricingPage">
      <MarketingNav
        activePage="pricing"
        openLanding={openLanding}
        openPricing={openPricing}
        openAbout={openAbout}
        openDashboard={openDashboard}
        openLogin={openLogin}
      />

      <main className="pricingHero">
        <div className="pricingBadge">Pricing</div>

        <h1>
          Flexible plans for <span>modern software QA teams.</span>
        </h1>

        <p>
          Start free, scale when ready, and choose the level of QA automation
          that matches your workflow — from solo reviews to team-wide command
          center operations.
        </p>

        <div className="billingToggle">
          <button
            className={!annual ? "active" : ""}
            onClick={() => setAnnual(false)}
          >
            Monthly
          </button>

          <button
            className={annual ? "active" : ""}
            onClick={() => setAnnual(true)}
          >
            Annual
          </button>

          <span>Save 20%</span>
        </div>
      </main>

      <section className="pricingGrid">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`pricingCard ${plan.highlight ? "featuredPlan" : ""}`}
          >
            {plan.highlight && (
              <div className="planTag">{plan.highlight}</div>
            )}

            <div className="planTop">
              <h3>{plan.name}</h3>
              <p>{plan.description}</p>
            </div>

            <div className="planPrice">
              <strong>{plan.price}</strong>
              <span>{plan.period}</span>
            </div>

            <ul className="planFeatures">
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>

            <button
              className={
                plan.buttonType === "primary"
                  ? "planButton primaryPlanButton"
                  : "planButton secondaryPlanButton"
              }
              onClick={
                plan.name === "Starter"
                  ? openLogin
                  : plan.name === "Enterprise"
                  ? openAbout
                  : openDashboard
              }
            >
              {plan.button}
            </button>
          </div>
        ))}
      </section>

      <section className="pricingFootnote">
        <div className="pricingMiniCard">
          <h4>Built for real workflows</h4>
          <p>
            Every plan is designed around code review, security scanning, test
            generation, and final report delivery.
          </p>
        </div>

        <div className="pricingMiniCard">
          <h4>Scale when your team grows</h4>
          <p>
            Start with lightweight individual use, then move into shared team
            review and advanced governance.
          </p>
        </div>

        <div className="pricingMiniCard">
          <h4>Enterprise-ready direction</h4>
          <p>
            Our long-term roadmap includes GitHub connections, CI/CD flows, and
            deeper AI-assisted QA automation.
          </p>
        </div>
      </section>
    </section>
  );
}

export default PricingPage;