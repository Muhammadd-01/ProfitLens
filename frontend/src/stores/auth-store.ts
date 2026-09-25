import { create } from 'zustand';
import type { User, Organization } from '@/types';

interface AuthState {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setAuth: (user: User, organization: Organization, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  organization: null,
  token: localStorage.getItem('profitlens_token'),
  isAuthenticated: !!localStorage.getItem('profitlens_token'),
  isLoading: true,

  setAuth: (user, organization, token) => {
    localStorage.setItem('profitlens_token', token);
    set({
      user,
      organization,
      token,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: () => {
    localStorage.removeItem('profitlens_token');
    set({
      user: null,
      organization: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  setLoading: (loading) => set({ isLoading: loading }),
}));
