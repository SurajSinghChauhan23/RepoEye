import { useNavigate } from "react-router-dom";

export default function TopBar() {
  const navigate = useNavigate();

  return (
    <div className="flex items-center gap-4 px-6 py-3 border-b border-slate-800 bg-[#0b1220]">
      <button
        onClick={() => navigate("/")}
        className="text-slate-400 hover:text-slate-100"
      >
        ← Back
      </button>

      <span className="font-medium text-slate-300">
        Yashika-web16 / SMART-MESS
      </span>
    </div>
  );
}
