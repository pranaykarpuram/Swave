import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/api/client';
import type { User, LoginRequest, RegisterRequest } from '@/api/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;
  
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadProfile: () => Promise<void>;
  enterDemoMode: () => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      isDemoMode: false,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.auth.login(credentials);
          set({ 
            user: response.user, 
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false 
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.auth.register(data);
          set({ 
            user: response.user, 
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false 
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          // Only call API logout if not in demo mode
          if (!get().isDemoMode) {
            await api.auth.logout();
          }
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          set({ 
            user: null, 
            isAuthenticated: false, 
            isDemoMode: false,
            isLoading: false 
          });
        }
      },

      loadProfile: async () => {
        set({ isLoading: true });
        try {
          const user = await api.auth.getProfile();
          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          });
        }
      },

      enterDemoMode: () => {
        const demoUser: User = {
          id: 999,
          username: 'demo_user',
          email: 'demo@swave.com',
          display_name: 'Demo User',
          date_joined: new Date().toISOString(),
          profile: {
            favorite_genres: ['pop', 'rock', 'electronic'],
            favorite_artists: ['Demo Artist 1', 'Demo Artist 2'],
            auto_play_previews: true,
            swipe_sensitivity: 0.5,
            total_swipes: 0,
            total_likes: 0,
            total_rejects: 0,
          }
        };
        
        set({ 
          user: demoUser, 
          isAuthenticated: true, 
          isDemoMode: true,
          isLoading: false,
          error: null 
        });
      },

      clearError: () => set({ error: null }),
      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);
