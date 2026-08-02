import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './Layout';
import Login from './pages/Login';
import Eat from './pages/Eat';
import Stores from './pages/Stores';
import AlreadyHave from './pages/AlreadyHave';
import Plan from './pages/Plan';
import Shopping from './pages/Shopping';
import Steps from './pages/Steps';
import History from './pages/History';
import Chat from './pages/Chat';
import Profile from './pages/Profile';
import { useUser } from './UserContext';
import Community from './pages/Community';

function App() {
  const { user } = useUser();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to={user ? '/eat' : '/login'} />} />
        <Route path="/eat" element={<Eat />} />
        <Route path="/stores" element={<Stores />} />
        <Route path="/have" element={<AlreadyHave />} />
        <Route path="/plan" element={<Plan />} />
        <Route path="/shopping" element={<Shopping />} />
        <Route path="/steps" element={<Steps />} />
        <Route path="/history" element={<History />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/community" element={<Community />} />
      </Route>
    </Routes>
  );
}

export default App;