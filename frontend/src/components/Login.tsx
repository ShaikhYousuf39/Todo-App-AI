import React, { useMemo, useState } from 'react';
import { signIn, signUp } from '../lib/auth';

interface LoginProps {
  onSuccess: () => void;
}

const featureBullets = [
  {
    icon: 'AI',
    title: 'Natural-language task control',
    text: 'Create, complete, update, and list tasks with plain English.',
  },
  {
    icon: 'HX',
    title: 'Conversation memory',
    text: 'Keep context across turns so follow-up requests feel natural.',
  },
  {
    icon: 'DB',
    title: 'Persistent workspace',
    text: 'Your tasks and chats stay available with PostgreSQL storage.',
  },
];

export default function Login({ onSuccess }: LoginProps) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const modeTitle = isSignUp ? 'Create your workspace' : 'Welcome back';
  const modeSubtitle = isSignUp
    ? 'Set up your account to start managing tasks with AI.'
    : 'Sign in to continue your task conversations.';
  const ctaLabel = loading ? (isSignUp ? 'Creating account...' : 'Signing in...') : isSignUp ? 'Create Account' : 'Sign In';

  const passwordHint = useMemo(() => {
    if (!isSignUp) return null;
    if (password.length === 0) return 'Use at least 8 characters.';
    return password.length >= 8 ? 'Password length looks good.' : 'Password must be at least 8 characters.';
  }, [isSignUp, password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignUp) {
        const result = await signUp.email({
          email,
          password,
          name,
        });
        if (result.error) {
          setError(result.error.message || 'Sign up failed');
        } else {
          onSuccess();
        }
      } else {
        const result = await signIn.email({
          email,
          password,
        });
        if (result.error) {
          setError(result.error.message || 'Sign in failed');
        } else {
          onSuccess();
        }
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="ambient-orb ambient-orb--one" />
      <div className="ambient-orb ambient-orb--two" />
      <div className="ambient-orb ambient-orb--three" />

      <div className="auth-layout">
        <section className="auth-hero panel-float">
          <div className="auth-hero__badge">
            <span className="auth-hero__badge-dot" />
            AI Task Workspace
          </div>
          <h1>Turn conversations into completed tasks.</h1>
          <p>
            A fast, clean workspace for planning your day, tracking progress, and managing todos
            with a chat-based assistant.
          </p>

          <div className="auth-hero__cards">
            {featureBullets.map((feature, index) => (
              <div
                key={feature.title}
                className="auth-feature-card"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <div className="auth-feature-card__icon">{feature.icon}</div>
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="auth-hero__stats">
            <div>
              <span>Fast chat flow</span>
              <strong>Optimized</strong>
            </div>
            <div>
              <span>Session auth</span>
              <strong>Better Auth</strong>
            </div>
            <div>
              <span>Task memory</span>
              <strong>Persistent</strong>
            </div>
          </div>
        </section>

        <section className="auth-panel panel-float">
          <div className="auth-card">
            <div className="auth-card__header">
              <div className="auth-logo">
                <span className="auth-logo__core">T</span>
                <span className="auth-logo__ring" />
              </div>
              <div>
                <h2>{modeTitle}</h2>
                <p>{modeSubtitle}</p>
              </div>
            </div>

            <div className="auth-mode-toggle" role="tablist" aria-label="Authentication mode">
              <button
                type="button"
                className={!isSignUp ? 'is-active' : ''}
                onClick={() => setIsSignUp(false)}
                disabled={loading}
              >
                Sign In
              </button>
              <button
                type="button"
                className={isSignUp ? 'is-active' : ''}
                onClick={() => setIsSignUp(true)}
                disabled={loading}
              >
                Sign Up
              </button>
            </div>

            <form onSubmit={handleSubmit} className="auth-form">
              {isSignUp && (
                <label className="auth-field">
                  <span>Name</span>
                <div className="auth-input-shell">
                    <span className="auth-input-icon">U</span>
                    <input
                      type="text"
                      placeholder="Alex Johnson"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      disabled={loading}
                    />
                  </div>
                </label>
              )}

              <label className="auth-field">
                <span>Email</span>
                <div className="auth-input-shell">
                  <span className="auth-input-icon">@</span>
                  <input
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
              </label>

              <label className="auth-field">
                <span>Password</span>
                <div className="auth-input-shell">
                  <span className="auth-input-icon">#</span>
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    disabled={loading}
                  />
                </div>
              </label>

              {passwordHint && (
                <p
                  className={`auth-helper ${password.length > 0 && password.length < 8 ? 'is-error' : ''}`}
                >
                  {passwordHint}
                </p>
              )}

              {error && (
                <div className="auth-error" role="alert" aria-live="polite">
                  <span>!</span>
                  <p>{error}</p>
                </div>
              )}

              <button type="submit" className="auth-submit" disabled={loading}>
                {loading && <span className="button-spinner" aria-hidden="true" />}
                <span>{ctaLabel}</span>
              </button>
            </form>

            <p className="auth-footer-copy">
              {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                className="auth-footer-link"
                onClick={() => setIsSignUp((prev) => !prev)}
                disabled={loading}
              >
                {isSignUp ? 'Sign In' : 'Create one'}
              </button>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
