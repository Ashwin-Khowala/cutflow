import type { FC, ReactNode } from 'react';
import { X, Keyboard, Play, Scissors, Navigation, Layout } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ShortcutItem {
  keys: string[];
  description: string;
}

interface ShortcutGroup {
  title: string;
  icon: ReactNode;
  shortcuts: ShortcutItem[];
}

export const KeyboardShortcutsModal: FC<KeyboardShortcutsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const groups: ShortcutGroup[] = [
    {
      title: 'Playback & Scrubbing',
      icon: <Play size={16} color="#818cf8" />,
      shortcuts: [
        { keys: ['Space'], description: 'Play / Pause video' },
        { keys: ['J'], description: 'Step back 2 seconds' },
        { keys: ['K'], description: 'Pause playback' },
        { keys: ['L'], description: 'Step forward 2 seconds' },
        { keys: ['←'], description: 'Scrub back 1 second' },
        { keys: ['→'], description: 'Scrub forward 1 second' },
        { keys: ['Shift', '← / →'], description: 'Fine scrub 0.1s (1 frame)' },
        { keys: ['Home / 0'], description: 'Jump to beginning (00:00)' },
        { keys: ['End'], description: 'Jump to end of timeline' },
        { keys: ['M'], description: 'Toggle video mute' },
        { keys: ['F'], description: 'Toggle fullscreen video' },
      ],
    },
    {
      title: 'Cut & Take Editing',
      icon: <Scissors size={16} color="#f43f5e" />,
      shortcuts: [
        { keys: ['C'], description: 'Cut / Toggle take at playhead or selection' },
        { keys: ['X'], description: 'Alternate Cut / Toggle shortcut' },
        { keys: ['Delete'], description: 'Cut selected take' },
        { keys: ['Backspace'], description: 'Cut selected take' },
        { keys: ['R'], description: 'Restore take (un-cut)' },
        { keys: ['Shift', 'Delete'], description: 'Clean jittery short clips (≤2.5s)' },
        { keys: ['A'], description: 'Toggle Smart Auto-Skip mode' },
        { keys: ['Esc'], description: 'Deselect clip / close modal' },
      ],
    },
    {
      title: 'Take Navigation',
      icon: <Navigation size={16} color="#34d399" />,
      shortcuts: [
        { keys: ['↑'], description: 'Select & seek to Previous Take' },
        { keys: ['↓'], description: 'Select & seek to Next Take' },
        { keys: ['['], description: 'Seek to start of active take' },
        { keys: [']'], description: 'Seek to end of active take' },
      ],
    },
    {
      title: 'Studio & Views',
      icon: <Layout size={16} color="#38bdf8" />,
      shortcuts: [
        { keys: ['P'], description: 'Open Video Projects Manager' },
        { keys: ['E'], description: 'Inspect Edit Plan IR & EDL' },
        { keys: ['?'], description: 'Open this Keyboard Shortcuts cheat sheet' },
      ],
    },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#0f172a',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '780px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2))',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#818cf8',
              }}
            >
              <Keyboard size={18} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600, color: '#f8fafc' }}>
                CutFlow Keyboard Shortcuts
              </h2>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
                Full NLE-grade hotkey controls for lightning-fast rough cutting
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div
          style={{
            padding: '1.5rem',
            overflowY: 'auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {groups.map((group) => (
            <div
              key={group.title}
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                borderRadius: '12px',
                padding: '1rem',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  color: '#f1f5f9',
                  marginBottom: '0.85rem',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                  paddingBottom: '0.5rem',
                }}
              >
                {group.icon}
                <span>{group.title}</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                {group.shortcuts.map((sc, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      fontSize: '0.82rem',
                    }}
                  >
                    <span style={{ color: '#cbd5e1' }}>{sc.description}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {sc.keys.map((k, kIdx) => (
                        <kbd
                          key={kIdx}
                          style={{
                            background: 'rgba(255, 255, 255, 0.08)',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            borderBottom: '2px solid rgba(255, 255, 255, 0.3)',
                            borderRadius: '5px',
                            padding: '2px 7px',
                            fontFamily: 'monospace',
                            fontSize: '0.75rem',
                            color: '#f8fafc',
                            fontWeight: 600,
                            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.4)',
                          }}
                        >
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '0.85rem 1.5rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(0, 0, 0, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
            color: '#94a3b8',
          }}
        >
          <span>Tip: Press <kbd style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 5px', borderRadius: '4px' }}>?</kbd> anytime to open this guide</span>
          <button
            onClick={onClose}
            style={{
              background: '#6366f1',
              border: 'none',
              color: '#ffffff',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.8rem',
            }}
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};
