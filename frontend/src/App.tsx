import { useMemo } from 'react';
import { useSession } from './lib/auth';
import Login from './components/Login';
import Chat from './components/Chat';

interface Session {
  user: {
    id: string;
    email: string;
    name: string;
  };
  session: {
    token: string;
  };
}

export default function App() {
  const { data: session, isPending } = useSession() as {
    data: Session | null;
    isPending: boolean;
  };
  const isAuthenticated = useMemo(() => Boolean(session?.user), [session]);

  if (isPending) {
    return (
      <div className="app-loading-screen">
        <div className="ambient-orb ambient-orb--one" />
        <div className="ambient-orb ambient-orb--two" />
        <div className="ambient-orb ambient-orb--three" />
        <div className="loading-panel">
          <div className="loading-spinner" />
          <h2>Preparing your workspace</h2>
          <p>Loading session and syncing your todo assistant.</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !session) {
    return <Login onSuccess={() => window.location.reload()} />;
  }

  return (
    <Chat
      userId={session.user.id}
      userName={session.user.name}
      userEmail={session.user.email}
      token={session.session.token}
      onLogout={() => window.location.reload()}
    />
  );
}
