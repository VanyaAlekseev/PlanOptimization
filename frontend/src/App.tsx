import { Box } from "@mui/material";
import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { PlanningPage } from "./pages/PlanningPage";
import { ReportsPage } from "./pages/ReportsPage";
import { StructureEditorPage } from "./pages/StructureEditorPage";
import { AlgorithmsComparePage } from "./pages/AlgorithmsComparePage";

const App = () => {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/structure" element={<StructureEditorPage />} />
          <Route path="/planning" element={<PlanningPage />} />
          <Route path="/algorithms" element={<AlgorithmsComparePage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </Layout>
    </Box>
  );
};

export default App;

