import React, { useEffect, useMemo, useRef, useState } from 'react';
import { signOut } from '../lib/auth';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: number;
  error?: boolean;
  latencyMs?: number;
  toolCount?: number;
}

interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  result?: Record<string, unknown>;
}

interface ChatApiResponse {
  conversation_id: number;
  response: string;
  tool_calls?: ToolCall[];
}

interface ChatProps {
  userId: string;
  token: string;
  userName?: string;
  userEmail?: string;
  onLogout: () => void;
}

const starterPrompts = [
  'Add a task to buy groceries',
  'Show me all my tasks',
  'What tasks are pending?',
  'Mark task 1 as complete',
  "Change task 1 to 'Call mom tonight'",
];

function getInitials(name?: string, fallback = 'U') {
  if (!name) return fallback;
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return fallback;
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

function formatMessageTime(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Chat({ userId, token, userName, userEmail, onLogout }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  const [lastToolCount, setLastToolCount] = useState<number>(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const userInitials = useMemo(() => getInitials(userName, 'ME'), [userName]);
  const userDisplayName = userName?.trim() || 'Workspace User';
  const completedCount = useMemo(
    () => messages.filter((message) => message.role === 'assistant' && !message.error).length,
    [messages],
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const sendMessage = async (rawMessage: string) => {
    const messageText = rawMessage.trim();
    if (!messageText || loading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    const startedAt = performance.now();

    try {
      const response = await fetch(`${apiUrl}/api/${userId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: messageText,
        }),
      });

      if (!response.ok) {
        let detail = 'Failed to send message';
        try {
          const errorBody = await response.json();
          if (typeof errorBody?.detail === 'string') {
            detail = errorBody.detail;
          }
        } catch {
          // Ignore JSON parsing errors and use generic message.
        }
        throw new Error(detail);
      }

      const data = (await response.json()) as ChatApiResponse;
      const latencyMs = Math.round(performance.now() - startedAt);
      setConversationId(data.conversation_id);
      setLastLatencyMs(latencyMs);
      setLastToolCount(Array.isArray(data.tool_calls) ? data.tool_calls.length : 0);

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        createdAt: Date.now(),
        latencyMs,
        toolCount: Array.isArray(data.tool_calls) ? data.tool_calls.length : 0,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: `assistant-error-${Date.now()}`,
        role: 'assistant',
        content:
          error instanceof Error
            ? `Request failed: ${error.message}. Check backend/auth server logs and try again.`
            : 'Sorry, I encountered an error. Please try again.',
        createdAt: Date.now(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendMessage(input);
  };

  const handleLogout = async () => {
    await signOut();
    onLogout();
  };

  const handleNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setLastLatencyMs(null);
    setLastToolCount(0);
    setInput('');
    setIsSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  return (
    <div className={`chat-shell ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="ambient-orb ambient-orb--one" />
      <div className="ambient-orb ambient-orb--two" />
      <div className="ambient-orb ambient-orb--three" />
      <button
        type="button"
        className="chat-sidebar-overlay"
        aria-label="Close sidebar"
        onClick={() => setIsSidebarOpen(false)}
      />

      <div className="chat-layout">
        <aside className="chat-sidebar panel-float">
          <div className="chat-sidebar__mobile-header">
            <div className="chat-sidebar__mobile-title">Workspace Menu</div>
            <button
              type="button"
              className="chat-sidebar__close"
              aria-label="Close sidebar"
              onClick={() => setIsSidebarOpen(false)}
            >
              x
            </button>
          </div>

          <div className="chat-sidebar__profile">
            <div className="avatar avatar--large">{userInitials}</div>
            <div>
              <p className="chat-sidebar__label">Signed in as</p>
              <h2>{userDisplayName}</h2>
              <p className="chat-sidebar__muted">{userEmail || 'Local workspace session'}</p>
            </div>
          </div>

          <div className="chat-sidebar__stats">
            <div className="stat-card">
              <span>Conversation</span>
              <strong>{conversationId ? `#${conversationId}` : 'New'}</strong>
            </div>
            <div className="stat-card">
              <span>Replies</span>
              <strong>{completedCount}</strong>
            </div>
            <div className="stat-card">
              <span>Last latency</span>
              <strong>{lastLatencyMs ? `${lastLatencyMs} ms` : '--'}</strong>
            </div>
          </div>

          <div className="chat-sidebar__section">
            <div className="section-title-row">
              <h3>Quick prompts</h3>
              <span>Fast path enabled</span>
            </div>
            <div className="quick-prompt-list">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="quick-prompt"
                  onClick={() => {
                    setIsSidebarOpen(false);
                    void sendMessage(prompt);
                  }}
                  disabled={loading}
                  title={prompt}
                >
                  <span className="quick-prompt__icon">+</span>
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="chat-sidebar__section chat-sidebar__note">
            <h3>Tips</h3>
            <p>
              Direct task commands now use a faster local parser before falling back to the AI agent.
            </p>
          </div>
        </aside>

        <main className="chat-panel panel-float">
          <header className="chat-header">
            <div className="chat-header__title-group">
              <button
                type="button"
                className="chat-mobile-trigger"
                aria-label="Open sidebar"
                onClick={() => setIsSidebarOpen(true)}
              >
                <span />
                <span />
                <span />
              </button>
              <div className="chat-header__eyebrow">Todo AI Chatbot</div>
              <h1>Task Command Center</h1>
            </div>
            <div className="chat-header__actions">
              <div className="chat-badge">
                <span className="chat-badge__dot" />
                {loading ? 'Processing' : 'Ready'}
              </div>
              {lastLatencyMs !== null && (
                <div className="chat-badge chat-badge--muted">{lastLatencyMs} ms</div>
              )}
              {lastToolCount > 0 && (
                <div className="chat-badge chat-badge--muted">{lastToolCount} tool call(s)</div>
              )}
              <button onClick={handleNewChat} className="ui-button ui-button--secondary" type="button">
                New Chat
              </button>
              <button onClick={handleLogout} className="ui-button ui-button--danger" type="button">
                Logout
              </button>
            </div>
          </header>

          <section className="messages-panel">
            {messages.length === 0 ? (
              <div className="chat-empty-state">
                <div className="chat-empty-state__icon">AI</div>
                <h2>Start with a task command</h2>
                <p>
                  Ask the assistant to create, list, update, complete, or delete tasks in plain English.
                </p>
                <div className="chat-empty-state__chips">
                  {starterPrompts.slice(0, 4).map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="prompt-chip"
                      onClick={() => setInput(prompt)}
                      disabled={loading}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="message-list">
                {messages.map((message, index) => {
                  const isUser = message.role === 'user';
                  const avatarLabel = isUser ? userInitials : 'AI';

                  return (
                    <div
                      key={message.id}
                      className={`message-row ${isUser ? 'is-user' : 'is-assistant'} ${message.error ? 'is-error' : ''}`}
                      style={{ animationDelay: `${Math.min(index * 45, 250)}ms` }}
                    >
                      <div className={`avatar ${isUser ? 'avatar--user' : 'avatar--assistant'}`}>
                        {avatarLabel}
                      </div>
                      <div className={`message-bubble ${isUser ? 'message-bubble--user' : 'message-bubble--assistant'}`}>
                        <div className="message-bubble__meta">
                          <span>{isUser ? userDisplayName : 'Todo Assistant'}</span>
                          <span>{formatMessageTime(message.createdAt)}</span>
                          {!isUser && message.toolCount ? <span>{message.toolCount} tools</span> : null}
                          {!isUser && message.latencyMs ? <span>{message.latencyMs} ms</span> : null}
                        </div>
                        <p>{message.content}</p>
                      </div>
                    </div>
                  );
                })}

                {loading && (
                  <div className="message-row is-assistant">
                    <div className="avatar avatar--assistant">AI</div>
                    <div className="message-bubble message-bubble--assistant typing-bubble">
                      <div className="message-bubble__meta">
                        <span>Todo Assistant</span>
                        <span>working...</span>
                      </div>
                      <div className="typing-dots" aria-label="Assistant is typing">
                        <span />
                        <span />
                        <span />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </section>

          <form onSubmit={handleSubmit} className="composer">
            <div className="composer__input-shell">
              <div className="composer__icon">{'>'}</div>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a task request... e.g., Add a task to review the PR"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="ui-button ui-button--primary composer__send"
              disabled={loading || !input.trim()}
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}
