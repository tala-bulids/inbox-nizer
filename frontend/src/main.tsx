import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import "./styles/theme.css";
const root = createRoot(document.getElementById("root")!);
if (import.meta.env.VITE_PUBLIC_DEMO === "true") {
  void import("./demo/DemoApp").then(({ DemoApp }) => {
    root.render(
      <HashRouter>
        <DemoApp />
      </HashRouter>,
    );
  });
} else {
  void import("./app/App").then(({ App }) => {
    root.render(
      <BrowserRouter>
        <App />
      </BrowserRouter>,
    );
  });
}
