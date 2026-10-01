export default function Header({ toggleTheme }) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-card border-b border-border">
      <h1 className="font-bold text-lg">🐙 RepoMind</h1>

      <button
        onClick={toggleTheme}
        className="px-3 py-1 rounded bg-border hover:bg-primary transition"
      >
        🌗
      </button>
    </div>
  );
}
