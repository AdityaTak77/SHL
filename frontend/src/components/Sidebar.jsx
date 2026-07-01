import React from 'react';
import { 
  Briefcase, 
  Award, 
  Cpu, 
  Globe, 
  ShieldAlert, 
  Info,
  PanelLeftClose
} from 'lucide-react';

const TEST_TYPES = [
  { code: 'A', name: 'Ability & Aptitude', desc: 'Cognitive, numerical, verbal reasoning' },
  { code: 'B', name: 'Biodata & SJT', desc: 'Situational judgment scenarios' },
  { code: 'C', name: 'Competencies', desc: 'Structured behavioral competency maps' },
  { code: 'D', name: 'Development & 360', desc: 'Coaching & feedback tools' },
  { code: 'K', name: 'Knowledge & Skills', desc: 'Technical tests (Java, Docker, SQL, etc.)' },
  { code: 'P', name: 'Personality & Behavior', desc: 'OPQ32 workplace styles' },
  { code: 'S', name: 'Simulations', desc: 'Interactive or live-coding tasks' },
];

export default function Sidebar({ extractedState, turnCount, isOpen, onToggle }) {
  const isWarning = turnCount >= 6;

  return (
    <aside className={`app-sidebar${isOpen ? '' : ' sidebar-closed'}`}>
      {/* App Header */}
      <div>
        <div className="app-logo-container">
          <div className="logo-badge" style={{ width: '48px', fontSize: '13px' }}>SHL</div>
          <h1 className="logo-text">Recommender</h1>
          {/* Hide sidebar button */}
          <button
            onClick={onToggle}
            className="btn-reset"
            title="Hide sidebar"
            style={{ marginLeft: 'auto', padding: '4px 6px' }}
          >
            <PanelLeftClose size={14} />
          </button>
        </div>
        <p className="sidebar-desc">Conversational AI Agent • Catalog v1.0</p>
      </div>

      {/* Turn Tracker */}
      <div className="glass-panel">
        <div className="tracker-header">
          <span>Turn Budget</span>
          <span className={`tracker-badge ${isWarning ? 'warning' : ''}`}>
            {turnCount} / 8 turns
          </span>
        </div>
        <div className="progress-bar-bg">
          <div 
            className={`progress-bar-fill ${isWarning ? 'warning' : ''}`} 
            style={{ width: `${(turnCount / 8) * 100}%` }}
          />
        </div>
      </div>

      {/* Extracted Context (Hiring State) */}
      <div>
        <h2 className="section-title">
          <Cpu size={14} style={{ color: 'var(--accent-green)' }} />
          Extracted Hiring Profile
        </h2>

        <div className="profile-list">
          {/* Role */}
          <div className="profile-item">
            <Briefcase size={16} className="profile-icon role" />
            <div>
              <div className="profile-item-label">Target Role</div>
              <div className="profile-item-value">
                {extractedState.role || 'Not detected yet'}
              </div>
            </div>
          </div>

          {/* Seniority */}
          <div className="profile-item">
            <Award size={16} className="profile-icon seniority" />
            <div>
              <div className="profile-item-label">Seniority / Exp</div>
              <div className="profile-item-value">
                {extractedState.seniority || 'Not detected yet'}
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="profile-item">
            <Cpu size={16} className="profile-icon skills" />
            <div style={{ width: '100%' }}>
              <div className="profile-item-label">Technical Skills</div>
              <div style={{ marginTop: '2px' }}>
                {extractedState.skills.length > 0 ? (
                  extractedState.skills.map((skill, i) => (
                    <span key={i} className="skill-tag">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="empty-italic">No skills listed yet</span>
                )}
              </div>
            </div>
          </div>

          {/* Constraints */}
          <div className="profile-item">
            <Globe size={16} className="profile-icon constraints" />
            <div style={{ width: '100%' }}>
              <div className="profile-item-label">Focus & Constraints</div>
              <div className="constraints-details">
                <div className="constraint-row">
                  <span>Personality:</span>
                  <span className={`constraint-status ${extractedState.personality ? 'active' : ''}`}>
                    {extractedState.personality ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="constraint-row">
                  <span>Cognitive:</span>
                  <span className={`constraint-status ${extractedState.cognitive ? 'active' : ''}`}>
                    {extractedState.cognitive ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="constraint-row">
                  <span>Language:</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
                    {extractedState.language || 'English (USA)'}
                  </span>
                </div>
                {extractedState.safety && (
                  <div className="safety-badge">
                    <ShieldAlert size={12} />
                    <span>Safety Critical Role</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Whitelisted Test Types Guide */}
      <div className="whitelist-guide">
        <h2 className="section-title">
          <Info size={14} style={{ color: 'var(--accent-green)' }} />
          Test Type Whitelist
        </h2>
        <div className="whitelist-list">
          {TEST_TYPES.map((t, idx) => (
            <div key={idx} className="whitelist-item">
              <span className="whitelist-code">{t.code}</span>
              <div>
                <div className="whitelist-name">{t.name}</div>
                <div className="whitelist-desc">{t.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
