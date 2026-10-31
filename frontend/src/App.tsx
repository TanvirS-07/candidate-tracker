import { useState } from "react";
import CandidateDetailView from "./components/CandidateDetail";
import CandidateForm from "./components/CandidateForm";
import CandidateList from "./components/CandidateList";

type View = { name: "list" } | { name: "new" } | { name: "detail"; id: number };

export default function App() {
  const [view, setView] = useState<View>({ name: "list" });
  const toList = () => setView({ name: "list" });

  return (
    <main>
      <header className="row">
        <h1 onClick={toList} style={{ cursor: "pointer" }}>
          Candidate Tracker
        </h1>
        {view.name === "list" && <button onClick={() => setView({ name: "new" })}>+ Add candidate</button>}
      </header>
      {view.name === "list" && <CandidateList onOpen={(id) => setView({ name: "detail", id })} />}
      {view.name === "new" && <CandidateForm onCreated={(id) => setView({ name: "detail", id })} onCancel={toList} />}
      {view.name === "detail" && <CandidateDetailView id={view.id} onBack={toList} />}
    </main>
  );
}
