import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@octo-erp/design-tokens/src/tokens.css";
import "./styles/app.css";
import { App } from "./App";
import { ErpApiProvider } from "./api/ErpApiProvider";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErpApiProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErpApiProvider>
  </React.StrictMode>,
);
