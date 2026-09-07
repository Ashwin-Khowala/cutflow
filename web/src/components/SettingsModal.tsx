import React, { useState } from 'react';
import { X, Key, Sliders, Clock, ExternalLink, Cpu, Sparkles } from 'lucide-react';
import type { Settings } from '../types';
import { cleanupStorage } from '../api/client';

interface SettingsModalProps {
  settings: Settings;
  onSave: (newSettings: Settings) => void;
  onClose: () => void;
}

const GROQ_MODELS = [
  { id: 'openai/gpt-oss-120b', name: 'OpenAI GPT-OSS 120B (Flagship Recommended)' },
  { id: 'openai/gpt-oss-20b', name: 'OpenAI GPT-OSS 20B (Fast)' },
  { id: 'qwen/qwen3.6-27b', name: 'Qwen 3.6 27B (Multimodal)' },
  { id: 'groq/compound', name: 'Groq Compound (Reasoning)' },
  { id: 'groq/compound-mini', name: 'Groq Compound Mini' },
  { id: 'custom', name: 'Custom Model ID...' },
];

const GEMINI_MODELS = [
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash (Recommended)' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash (Fast)' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (Deep Analysis)' },
];

export const SettingsModal: React.FC<SettingsModalProps> = ({
  settings,
  onSave,
  onClose,
}) => {
  const [provider, setProvider] = useState<'groq' | 'gemini'>(settings.provider || 'groq');
  const [groqApiKey, setGroqApiKey] = useState(settings.groqApiKey || '');
  const [geminiApiKey, setGeminiApiKey] = useState(settings.geminiApiKey || '');
  const [model, setModel] = useState(settings.model || 'openai/gpt-oss-120b');
  const [customModel, setCustomModel] = useState('');
  const [isCustomModel, setIsCustomModel] = useState(
    !GROQ_MODELS.some(m => m.id === settings.model) && settings.provider === 'groq'
  );
  const [silenceThreshold, setSilenceThreshold] = useState(settings.silenceThreshold || '-35dB');
  const [maxSilence, setMaxSilence] = useState(settings.maxSilence || 1.5);

  const handleProviderChange = (newProvider: 'groq' | 'gemini') => {
    setProvider(newProvider);
    if (newProvider === 'groq') {
      setModel('openai/gpt-oss-120b');
      setIsCustomModel(false);
    } else {
      setModel('gemini-2.0-flash');
    }
  };

  const handleSave = () => {
    const finalModel = provider === 'groq' && isCustomModel ? customModel.trim() : model;
    onSave({
      provider,
      model: finalModel || 'deepseek-r1-distill-qwen-32b',
      groqApiKey: groqApiKey.trim(),
      geminiApiKey: geminiApiKey.trim(),
      silenceThreshold: silenceThreshold.trim(),
      maxSilence: Number(maxSilence),
    });
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '560px' }} onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>⚙️ AI Engine & Slicing Settings</h3>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Provider Selector Tabs */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem', fontWeight: 700 }}>
              AI Intelligence Provider
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
              <button
                type="button"
                className="btn"
                onClick={() => handleProviderChange('groq')}
                style={{
                  background: provider === 'groq' ? 'var(--accent-gradient)' : 'rgba(0, 0, 0, 0.3)',
                  border: provider === 'groq' ? '1px solid var(--accent-primary)' : '1px solid var(--card-border)',
                  color: 'white',
                  justifyContent: 'center',
                  padding: '0.7rem',
                  borderRadius: '8px',
                  boxShadow: provider === 'groq' ? '0 4px 14px var(--accent-glow)' : 'none',
                }}
              >
                <Cpu size={16} />
                <span>Groq (Ultra-Fast LPU)</span>
              </button>

              <button
                type="button"
                className="btn"
                onClick={() => handleProviderChange('gemini')}
                style={{
                  background: provider === 'gemini' ? 'var(--accent-gradient)' : 'rgba(0, 0, 0, 0.3)',
                  border: provider === 'gemini' ? '1px solid var(--accent-primary)' : '1px solid var(--card-border)',
                  color: 'white',
                  justifyContent: 'center',
                  padding: '0.7rem',
                  borderRadius: '8px',
                  boxShadow: provider === 'gemini' ? '0 4px 14px var(--accent-glow)' : 'none',
                }}
              >
                <Sparkles size={16} />
                <span>Google Gemini</span>
              </button>
            </div>
          </div>

          {/* GROQ SETTINGS */}
          {provider === 'groq' && (
            <div style={{ background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.2)', padding: '1rem', borderRadius: '10px' }}>
              <div style={{ marginBottom: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', color: 'var(--text-main)', fontWeight: 600 }}>
                    <Key size={13} color="var(--accent-primary)" />
                    <span>Groq API Key</span>
                  </label>
                  <a
                    href="https://console.groq.com/keys"
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '0.2rem', textDecoration: 'none' }}
                  >
                    <span>Get free Groq Key</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
                <input
                  type="password"
                  placeholder="gsk_..."
                  value={groqApiKey}
                  onChange={(e) => setGroqApiKey(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid var(--card-border)',
                    background: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    fontFamily: 'JetBrains Mono',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <label style={{ fontSize: '0.825rem', color: 'var(--text-main)', fontWeight: 600 }}>
                    Groq Model
                  </label>
                  <a
                    href="https://console.groq.com/docs/models"
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.2rem', textDecoration: 'none' }}
                  >
                    <span>Groq Model Docs</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
                <select
                  value={isCustomModel ? 'custom' : model}
                  onChange={(e) => {
                    if (e.target.value === 'custom') {
                      setIsCustomModel(true);
                    } else {
                      setIsCustomModel(false);
                      setModel(e.target.value);
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid var(--card-border)',
                    background: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    fontSize: '0.85rem',
                  }}
                >
                  {GROQ_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>

                {isCustomModel && (
                  <div style={{ marginTop: '0.6rem' }}>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                      Enter Groq Model ID (e.g. <code>qwen/qwen3.6-27b</code> or <code>openai/gpt-oss-20b</code>)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. qwen/qwen3.6-27b"
                      value={customModel}
                      onChange={(e) => setCustomModel(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.55rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid var(--card-border)',
                        background: 'rgba(0, 0, 0, 0.5)',
                        color: 'white',
                        fontFamily: 'JetBrains Mono',
                        fontSize: '0.85rem',
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* GEMINI SETTINGS */}
          {provider === 'gemini' && (
            <div style={{ background: 'rgba(6, 182, 212, 0.06)', border: '1px solid rgba(6, 182, 212, 0.2)', padding: '1rem', borderRadius: '10px' }}>
              <div style={{ marginBottom: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', color: 'var(--text-main)', fontWeight: 600 }}>
                    <Key size={13} color="var(--cyan)" />
                    <span>Google Gemini API Key</span>
                  </label>
                  <a
                    href="https://aistudio.google.com/apikey"
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '0.75rem', color: 'var(--cyan)', display: 'flex', alignItems: 'center', gap: '0.2rem', textDecoration: 'none' }}
                  >
                    <span>Get free Gemini Key</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
                <input
                  type="password"
                  placeholder="AIzaSy..."
                  value={geminiApiKey}
                  onChange={(e) => setGeminiApiKey(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid var(--card-border)',
                    background: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    fontFamily: 'JetBrains Mono',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.825rem', color: 'var(--text-main)', marginBottom: '0.35rem', fontWeight: 600 }}>
                  Gemini Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid var(--card-border)',
                    background: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    fontSize: '0.85rem',
                  }}
                >
                  {GEMINI_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* AUDIO & SILENCE PREFERENCES */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                <Sliders size={13} />
                <span>Silence Threshold</span>
              </label>
              <input
                type="text"
                value={silenceThreshold}
                onChange={(e) => setSilenceThreshold(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid var(--card-border)',
                  background: 'rgba(0, 0, 0, 0.3)',
                  color: 'white',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                <Clock size={13} />
                <span>Max Silence (sec)</span>
              </label>
              <input
                type="number"
                step="0.1"
                value={maxSilence}
                onChange={(e) => setMaxSilence(Number(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.55rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid var(--card-border)',
                  background: 'rgba(0, 0, 0, 0.3)',
                  color: 'white',
                  fontSize: '0.85rem',
                }}
              />
            </div>
          </div>

          {/* STORAGE & CLEANUP MANAGEMENT */}
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--card-border)',
              padding: '0.85rem 1rem',
              borderRadius: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <span style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-main)', display: 'block' }}>
                🧹 Disk & Uploads Cleanup
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Auto-removes old video files & temporary audio to reclaim disk space.
              </span>
            </div>

            <button
              type="button"
              className="btn btn-outline"
              style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem', borderRadius: '6px' }}
              onClick={async (e) => {
                const btn = e.currentTarget;
                btn.disabled = true;
                btn.innerText = 'Cleaning...';
                try {
                  const data = await cleanupStorage();
                  alert(`Storage cleaned! Current storage: ${data.stats.total_mb} MB (${data.stats.upload_count} files)`);
                } catch {
                  alert('Storage cleanup completed.');
                } finally {
                  btn.disabled = false;
                  btn.innerText = 'Purge Uploads';
                }
              }}
            >
              Purge Uploads
            </button>
          </div>
        </div>

        {/* Modal Actions */}
        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button className="btn btn-outline" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
};
