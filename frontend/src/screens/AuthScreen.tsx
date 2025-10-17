import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { LoginForm } from '@/components/auth/LoginForm';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { Loader2 } from 'lucide-react';

type AuthMode = 'login' | 'register';

export const AuthScreen = () => {
  const [mode, setMode] = useState<AuthMode>('login');
  const { loadProfile, isLoading } = useAuthStore();

  // Try to load profile on mount (if tokens exist)
  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Swave</h1>
          <p className="text-blue-200">Discover your next favorite song</p>
        </div>

        {/* Auth Forms */}
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-white" />
          </div>
        ) : (
          <>
            {mode === 'login' ? (
              <LoginForm onSwitchToRegister={() => switchMode('register')} />
            ) : (
              <RegisterForm onSwitchToLogin={() => switchMode('login')} />
            )}
          </>
        )}

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-sm text-blue-200">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
};
