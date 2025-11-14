import { useEffect } from 'react';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged } from "firebase/auth";
import { AuthScreen } from "./screens/AuthScreen";
import { Feed } from "./screens/Feed";

const queryClient = new QueryClient();

const AppContent = () => {
  const { isAuthenticated, loadProfile } = useAuthStore();

  // Listen to Firebase auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // User is signed in, load profile from backend
        try {
          await loadProfile();
        } catch (error) {
          console.error('Failed to load profile:', error);
        }
      } else {
        // User is signed out
        useAuthStore.setState({
          firebaseUser: null,
          user: null,
          isAuthenticated: false,
          isDemoMode: false
        });
      }
    });

    return () => unsubscribe();
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
