import { useEffect, useRef, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Chat.css';

function Chat() {
  const { user } = useUser();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedStore, setSelectedStore] = useState(
    localStorage.getItem('borrowed_pantry_selected_store') || ''
  );

  const bottomRef = useRef(null);
  const hasAutoSent = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (!user || hasAutoSent.current) return;

    const pendingRecipe = localStorage.getItem('borrowed_pantry_pending_recipe');
    if (pendingRecipe) {
      hasAutoSent.current = true;
      localStorage.removeItem('borrowed_pantry_pending_recipe');

      const alreadyHaveRaw = localStorage.getItem('borrowed_pantry_already_have');
      localStorage.removeItem('borrowed_pantry_already_have');
      const alreadyHave = alreadyHaveRaw ? JSON.parse(alreadyHaveRaw) : [];

      const storeText = selectedStore ? ` at ${selectedStore}` : '';
      const haveText = alreadyHave.length ? ` I already have: ${alreadyHave.join(', ')}.` : '';
      sendMessage(`I want to make ${pendingRecipe}${storeText}.${haveText}`, alreadyHave);
    }
  }, [user]);

  const sendMessage = async (text, alreadyHave = []) => {
    if (!text.trim() || !user) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const res = await api.sendChat({
        email: user.email,
        name: user.name,
        message: text,
        conversation_id: conversationId,
        already_have: alreadyHave,
      });
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.reply }]);
      if (!conversationId) {
        setConversationId(res.data.conversation_id);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong reaching the kitchen. Try again in a moment.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = input;
    setInput('');
    sendMessage(text);
  };

  if (!user) {
    return <Navigate to="/login" />;
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h2 className="page-title">Chat</h2>
        {selectedStore && <span className="chat-store-tag">Shopping at {selectedStore}</span>}
      </div>

      <div className="chat-thread">
        {messages.length === 0 && !loading && (
          <p className="chat-empty">
            Name the dish. Name the store. We'll handle the rest.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'bubble bubble-user' : 'bubble bubble-agent'}>
            {msg.content}
          </div>
        ))}

        {loading && (
          <div className="bubble bubble-agent bubble-loading">Thinking...</div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="I want to make garden egg stew..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default Chat;