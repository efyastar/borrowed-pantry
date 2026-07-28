import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './Layout';
import Login from './pages/Login';
import Stores from './pages/Stores';
import Cook from './pages/Cook';
import Chat from './pages/Chat';
import History from './pages/History';
import { useUser } from './UserContext';

function App() {
  const { user } = useUser();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to={user ? '/stores' : '/login'} />} />
        <Route path="/stores" element={<Stores />} />
        <Route path="/cook" element={<Cook />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/history" element={<History />} />
      </Route>
    </Routes>
  );
}

export default App;