import { TLoginResponse } from '@/api/auth/type';

interface TogglePreferencesType {
  is_company: boolean;
  is_browse: boolean;
  is_general: boolean;
}

export const SessionUser = {
  set: (val: { user: TLoginResponse['data']['userdata'] }) =>
    localStorage.setItem('users', JSON.stringify(val)),

  get: (): { user: TLoginResponse['data']['userdata'] } | undefined => {
    const users = localStorage.getItem('users');
    return users ? JSON.parse(users) : undefined;
  },

  remove: () => localStorage.removeItem('users')
};

export const TogglePreferences = {
  set: (preferences: TogglePreferencesType) =>
    localStorage.setItem('toggle_preferences', JSON.stringify(preferences)),

  get: (): TogglePreferencesType | null => {
    const preferences = localStorage.getItem('toggle_preferences');
    return preferences ? JSON.parse(preferences) : null;
  },

  getWithDefaults: (): TogglePreferencesType => {
    const stored = TogglePreferences.get();
    return (
      stored || {
        is_company: true,
        is_browse: false,
        is_general: false
      }
    );
  },

  remove: () => localStorage.removeItem('toggle_preferences')
};
