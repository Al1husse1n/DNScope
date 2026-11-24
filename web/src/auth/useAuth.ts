import { useContext } from 'react';
import { AuthContext, AuthContextType } from './AuthContext';

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
