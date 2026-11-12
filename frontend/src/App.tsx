import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { Toaster } from "sonner";
import { ThemeProvider, useTheme } from "@/lib/theme";
import { AppShell } from "@/components/shell";
import { TooltipProvider } from "@/components/ui/misc";
import DashboardPage from "@/pages/DashboardPage";
import ProjectPage from "@/pages/ProjectPage";
import SettingsPage from "@/pages/SettingsPage";
import CommentsPage from "@/pages/CommentsPage";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 5_000, retry: 1, refetchOnWindowFocus: true } },
});

function Toasts() {
  const { escuro } = useTheme();
  return <Toaster theme={escuro ? "dark" : "light"} position="bottom-right" closeButton toastOptions={{ duration: 3000 }} />;
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={qc}>
        {/* RUI-12: com prefers-reduced-motion, o Motion desliga transformações e mantém só opacidade. */}
        <MotionConfig reducedMotion="user">
          <TooltipProvider>
            <BrowserRouter>
              <AppShell>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/projetos/:id" element={<ProjectPage />} />
                  <Route path="/comentarios" element={<CommentsPage />} />
                  <Route path="/comentarios/:id" element={<CommentsPage />} />
                  <Route path="/configuracoes" element={<SettingsPage />} />
                  <Route path="*" element={<DashboardPage />} />
                </Routes>
              </AppShell>
            </BrowserRouter>
            <Toasts />
          </TooltipProvider>
        </MotionConfig>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
