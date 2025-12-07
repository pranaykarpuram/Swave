import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useAuthStore } from "@/store/auth";
import { auth } from "@/lib/firebase";
import { onAuthStateChanged } from "firebase/auth";

import { AuthScreen } from "./screens/AuthScreen";
import { ConnectSpotify } from "./screens/ConnectSpotify";
import { Feed } from "./screens/Feed";

const queryClient = new QueryClient();

const AppShell = () => {
  const { isAuthenticated, loadProfile } = useAuthStore();

  // Listen to Firebase auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          await loadProfile();
        } catch (error) {
          console.error('Failed to load profile:', error);
        }
      } else {
        useAuthStore.setState({
          firebaseUser: null,
          user: null,
          isAuthenticated: false,
          isDemoMode: false,
        });
      }
    });

    return () => unsubscribe();
  }, [loadProfile]);

  return (
    <Routes>
      {/* Spotify callback landing page – ALWAYS show this component
          regardless of auth state (backend uses demo user anyway) */}
      <Route path="/connect-spotify" element={<ConnectSpotify />} />

      {/* Main app route: if authed show Feed, else show AuthScreen */}
      <Route path="/*" element={isAuthenticated ? <Feed /> : <AuthScreen />} />
    </Routes>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
