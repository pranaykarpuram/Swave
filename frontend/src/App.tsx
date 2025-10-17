import { useEffect } from 'react';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { AuthScreen } from "./screens/AuthScreen";
import { Feed } from "./screens/Feed";

const queryClient = new QueryClient();

const AppContent = () => {
  const { isAuthenticated, loadProfile } = useAuthStore();

  // Try to load profile on app start
  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  if (isAuthenticated) {
    return <Feed />;
  }

  return <AuthScreen />;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AppContent />
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
