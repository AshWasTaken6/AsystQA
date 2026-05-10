function SettingsPage({ user, logout }) {
  return (
    <div className="simplePageCard">
      <h2>Settings</h2>
      <p>Manage your demo account session.</p>

      <div className="settingsBox">
        <strong>{user?.name}</strong>
        <span>{user?.email}</span>
        <span>{user?.role}</span>
      </div>

      <button className="logoutButton" onClick={logout}>
        Log Out
      </button>
    </div>
  );
}

export default SettingsPage;
