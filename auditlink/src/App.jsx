import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SettingsProvider } from "./contexts/SettingsContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Engagements from "./pages/Engagements";
import Templates from "./pages/Templates";
import ICFR from "./pages/ICFR";
import Settings from "./pages/Settings";

function App() {
  return (
    <BrowserRouter>
      <SettingsProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="engagements" element={<Engagements />} />
            <Route path="templates" element={<Templates />} />
            <Route path="icfr" element={<ICFR />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </SettingsProvider>
    </BrowserRouter>
  );
}

export default App;
