import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/api/client';
import type { User, LoginRequest, RegisterRequest } from '@/api/types';
import { auth } from '@/lib/firebase';
import { firestoreService } from '@/lib/firestore';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword, 
  signOut,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';

interface AuthState {
  user: User | null;
  firebaseUser: FirebaseUser | null;
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
      firebaseUser: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      isDemoMode: false,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          // Use Firebase to sign in (authentication)
          const userCredential = await signInWithEmailAndPassword(
            auth, 
            credentials.email, 
            credentials.password
          );
          
          // Get Django JWT tokens (for API authentication)
          const response = await api.auth.login(credentials);
          
          // Try to load user data from Firestore (if exists)
          try {
            const firestoreUser = await firestoreService.getUser(userCredential.user.uid);
            if (firestoreUser) {
              set({ 
                user: firestoreUser,
                firebaseUser: userCredential.user,
                isAuthenticated: true, 
                isLoading: false 
              });
              return;
            }
          } catch (error) {
            console.log('No Firestore data found, using Django data');
          }
          
          set({ 
            user: response.user,
            firebaseUser: userCredential.user,
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';
          set({ 
            error: errorMessage,
            isLoading: false 
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          // Use Firebase to create user (authentication)
          const userCredential = await createUserWithEmailAndPassword(
            auth, 
            data.email, 
            data.password
          );
          
          // Create Django user (for API access)
          const response = await api.auth.register(data);
          
          // Save user data to Firestore (shared across team)
          await firestoreService.saveUser(userCredential.user.uid, {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email,
            display_name: response.user.display_name,
            date_joined: response.user.date_joined,
            profile: response.user.profile,
          });
          
          // Save profile to Firestore
          await firestoreService.saveProfile(userCredential.user.uid, response.user.profile);
          
          set({ 
            user: response.user,
            firebaseUser: userCredential.user,
            isAuthenticated: true, 
            isLoading: false 
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';
          set({ 
            error: errorMessage,
            isLoading: false 
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          // Sign out from Firebase
          if (get().firebaseUser) {
            await signOut(auth);
          }
          
          // Only call API logout if not in demo mode
          if (!get().isDemoMode) {
            try {
              await api.auth.logout();
            } catch (error) {
              console.error('API logout error:', error);
            }
          }
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          set({ 
            user: null,
            firebaseUser: null,
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
        isAuthenticated: state.isAuthenticated,
        isDemoMode: state.isDemoMode
      }),
    }
  )
);
