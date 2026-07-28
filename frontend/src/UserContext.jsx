import { createContext, useContext, useState, useEffect } from 'react';

const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUserState] = useState(() => {
    const saved = localStorage.getItem('borrowed_pantry_user');
    return saved ? JSON.parse(saved) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('borrowed_pantry_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('borrowed_pantry_user');
    }
  }, [user]);

  return (
    <UserContext.Provider value={{ user, setUser: setUserState, logout: () => setUserState(null) }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}