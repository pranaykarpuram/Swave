import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/auth';
import { LoginForm } from '@/components/auth/LoginForm';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { Button } from '@/components/ui/button';
import { Loader2, Play } from 'lucide-react';

type AuthMode = 'login' | 'register';

export const AuthScreen = () => {
  const [mode, setMode] = useState<AuthMode>('login');
  const { loadProfile, isLoading, enterDemoMode } = useAuthStore();

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
            
            {/* Demo Mode Button */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-blue-300/30" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 px-2 text-blue-200">
                    Or
                  </span>
                </div>
              </div>
              
              <Button
                onClick={enterDemoMode}
                variant="outline"
                className="w-full mt-4 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
              >
                <Play className="w-4 h-4 mr-2" />
                Try Demo Mode
              </Button>
              
              <p className="text-xs text-blue-200/70 text-center mt-2">
                Skip login and explore the app
              </p>
            </div>
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
