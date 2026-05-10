import { useState } from "react";

function LoginModal({ login, register, closeLogin }) {
  const [mode, setMode] = useState("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);

  function handleSubmit(event) {
    event.preventDefault();

    if (mode === "signup") {
      register(email, password, name, rememberMe);
      return;
    }

    login(email, password, rememberMe);
  }

  return (
    <div className="loginOverlay">
      <form className="loginModal" onSubmit={handleSubmit}>
        <button type="button" className="closeLoginBtn" onClick={closeLogin}>
          ×
        </button>

        <img src="/logo.png" alt="AsystQA Logo" />

        <h2>
          {mode === "signin"
            ? "Sign in to AsystQA"
            : "Create your AsystQA account"}
        </h2>

        <p>
          {mode === "signin"
            ? "Access your command center and continue your QA workflow."
            : "Create an account to start reviewing code with AsystQA."}
        </p>

        {mode === "signup" && (
          <label>
            Name
            <input
              type="text"
              value={name}
              placeholder="Your name"
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            value={email}
            placeholder="you@example.com"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            placeholder="Enter your password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <label className="rememberMeRow">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
          />
          <span>Remember me on this device</span>
        </label>

        <button type="submit" className="loginSubmitBtn">
          {mode === "signin" ? "Sign In →" : "Sign Up →"}
        </button>

        <div className="authToggle">
          {mode === "signin" ? (
            <p>
              Don’t have an account?{" "}
              <button type="button" onClick={() => setMode("signup")}>
                Sign up
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{" "}
              <button type="button" onClick={() => setMode("signin")}>
                Sign in
              </button>
            </p>
          )}
        </div>
      </form>
    </div>
  );
}

export default LoginModal;