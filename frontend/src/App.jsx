import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import StatusBar from './components/StatusBar';
import { RotateCcw, AlertCircle, Sun, Moon, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

// Helper to extract hiring context on client-side for visualization
const extractHiringContext = (messages) => {
  const state = {
    role: '',
    seniority: '',
    skills: [],
    personality: false,
    cognitive: false,
    safety: false,
    language: 'English (USA)'
  };

  const userText = messages
    .filter(m => msgRole(m) === 'user')
    .map(m => m.content.toLowerCase())
    .join(' ');

  if (!userText) return state;

  // ── Role: prioritised keyword map ──────────────────────────────────────
  const ROLE_MAP = [
    { keywords: ['frontend', 'front end', 'front-end'],                          label: 'Frontend Developer' },
    { keywords: ['backend', 'back end', 'back-end'],                             label: 'Backend Developer' },
    { keywords: ['full stack', 'fullstack', 'full-stack'],                       label: 'Full Stack Developer' },
    { keywords: ['devops', 'sre', 'platform engineer', 'site reliability'],      label: 'DevOps / SRE Engineer' },
    { keywords: ['data scientist', 'data science'],                              label: 'Data Scientist' },
    { keywords: ['machine learning', 'ml engineer'],                             label: 'ML Engineer' },
    { keywords: ['data engineer', 'data pipeline', 'etl'],                      label: 'Data Engineer' },
    { keywords: ['java developer', 'java engineer'],                             label: 'Java Developer' },
    { keywords: ['python developer', 'python engineer'],                         label: 'Python Developer' },
    { keywords: ['software engineer', 'software developer', 'swe'],             label: 'Software Engineer' },
    { keywords: ['sales representative', 'sales rep', 'account executive', 'bdr', 'sdr'], label: 'Sales Representative' },
    { keywords: ['sales manager', 'sales lead'],                                 label: 'Sales Manager' },
    { keywords: ['sales'],                                                       label: 'Sales Professional' },
    { keywords: ['contact centre', 'contact center', 'call centre', 'call center', 'customer service', 'customer support'], label: 'Customer Service Agent' },
    { keywords: ['digital marketing', 'content marketer', 'seo specialist'],    label: 'Digital Marketing Specialist' },
    { keywords: ['marketing'],                                                   label: 'Marketing Professional' },
    { keywords: ['financial analyst', 'finance analyst'],                        label: 'Financial Analyst' },
    { keywords: ['accountant', 'accounting', 'bookkeeper'],                      label: 'Accountant' },
    { keywords: ['finance'],                                                     label: 'Finance Professional' },
    { keywords: ['recruiter', 'talent acquisition', 'hrbp'],                    label: 'HR / Recruiter' },
    { keywords: ['human resources', ' hr '],                                    label: 'HR Professional' },
    { keywords: ['nurse', 'nursing', 'registered nurse'],                        label: 'Nurse' },
    { keywords: ['doctor', 'physician', 'medical officer'],                      label: 'Physician' },
    { keywords: ['pharmacist', 'pharmacy'],                                      label: 'Pharmacist' },
    { keywords: ['healthcare', 'clinical', 'patient care'],                      label: 'Healthcare Professional' },
    { keywords: ['civil engineer'],                                              label: 'Civil Engineer' },
    { keywords: ['mechanical engineer'],                                         label: 'Mechanical Engineer' },
    { keywords: ['electrical engineer'],                                         label: 'Electrical Engineer' },
    { keywords: ['qa engineer', 'quality assurance', 'test engineer', 'tester'], label: 'QA Engineer' },
    { keywords: ['product manager', 'product lead'],                             label: 'Product Manager' },
    { keywords: ['project manager', 'project lead'],                             label: 'Project Manager' },
    { keywords: ['ceo', 'cto', 'cfo', 'coo', 'cxo', 'chief executive'],         label: 'C-Suite Executive' },
    { keywords: ['executive', 'senior leadership'],                              label: 'Executive Leader' },
    { keywords: ['director'],                                                    label: 'Director' },
    { keywords: ['plant operator', 'factory worker', 'line worker'],             label: 'Manufacturing Operator' },
    { keywords: ['manufacturing', 'industrial operator'],                        label: 'Manufacturing Professional' },
    { keywords: ['retail', 'store associate', 'cashier'],                        label: 'Retail Associate' },
    { keywords: ['lawyer', 'attorney', 'paralegal'],                             label: 'Legal Professional' },
    { keywords: ['admin', 'administrative assistant', 'secretary'],              label: 'Administrative Assistant' },
    { keywords: ['manager', 'team lead', 'team leader'],                         label: 'Manager / Team Lead' },
    { keywords: ['developer', 'programmer'],                                     label: 'Software Developer' },
    { keywords: ['java'],                                                        label: 'Java Developer' },
    { keywords: ['python'],                                                      label: 'Python Developer' },
  ];

  for (const { keywords, label } of ROLE_MAP) {
    if (keywords.some(kw => userText.includes(kw))) {
      state.role = label;
      break;
    }
  }

  // ── Role fallback: regex extraction from raw user messages ─────────────
  if (!state.role) {
    const rawPatterns = [
      /(?:hiring|hire)\s+(?:for\s+)?(?:a\s+|an\s+)?([A-Za-z][A-Za-z\s\-\/]{2,35}?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)/i,
      /(?:need\s+a|need\s+an|looking\s+for\s+a|looking\s+for\s+an)\s+([A-Za-z][A-Za-z\s\-\/]{2,35}?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)/i,
      /(?:for\s+a|for\s+an)\s+([A-Za-z][A-Za-z\s\-\/]{2,35}?)(?:\s+role|\s+position|\s+with|\s+who|\s+that|[.,!?]|$)/i,
      /(?:role|position)[:\s]+([A-Za-z][A-Za-z\s\-\/]{2,35}?)(?:\s+with|\s+who|\s+that|[.,!?]|$)/i,
    ];
    for (const msg of messages.filter(m => msgRole(m) === 'user')) {
      for (const pattern of rawPatterns) {
        const match = msg.content.match(pattern);
        if (match && match[1]) {
          const candidate = match[1].trim();
          const words = candidate.split(/\s+/);
          if (words.length >= 1 && words.length <= 5) {
            state.role = candidate.replace(/\b\w/g, c => c.toUpperCase());
            break;
          }
        }
      }
      if (state.role) break;
    }
  }

  // Extract Seniority & Experience
  let yrs = null;
  const userMessages = messages.filter(m => msgRole(m) === 'user').map(m => m.content.toLowerCase());
  
  userMessages.forEach(msg => {
    const expMatch = msg.match(/(\d+)\+?\s*(year|yr|month|mo)s?/);
    if (expMatch) {
      const num = parseFloat(expMatch[1]);
      const unit = expMatch[2];
      yrs = unit.startsWith('m') ? num / 12 : num;
    } else if (/^\d+$/.test(msg.trim())) {
      yrs = parseFloat(msg.trim());
    }
  });

  if (yrs !== null && yrs < 40) {
    const displayStr = yrs < 1 ? Math.round(yrs * 12) + ' Months' : yrs + (yrs === 1 ? ' Year' : ' Years');
    if (yrs >= 15) state.seniority = `Executive (${displayStr})`;
    else if (yrs >= 8) state.seniority = `Director (${displayStr})`;
    else if (yrs >= 2) state.seniority = `Professional (${displayStr})`;
    else state.seniority = `Entry-level (${displayStr})`;
  } else {
    if (userText.includes('executive') || userText.includes('cxo') || userText.includes('ceo')) state.seniority = 'Executive (15+ yrs)';
    else if (userText.includes('director') || userText.includes('vp')) state.seniority = 'Director / Head level';
    else if (userText.includes('manager') || userText.includes('lead')) state.seniority = 'Manager / Lead';
    else if (userText.includes('graduate') || userText.includes('trainee')) state.seniority = 'Graduate Trainee';
    else if (userText.includes('junior') || userText.includes('entry') || userText.includes('intern') || userText.includes('fresher')) state.seniority = 'Entry-level / Junior';
    else if (userText.includes('senior') || userText.includes('professional') || userText.includes('ic')) state.seniority = 'Senior / Mid-Professional';
    else if (userText.includes('mid')) state.seniority = 'Professional Individual Contributor';
  }

  // Extract Skills
  const skillKeywords = [
    'java', 'python', 'javascript', 'typescript', 'react', 'angular', 'spring', 
    'aws', 'docker', 'kubernetes', 'sql', 'excel', 'word', 'salesforce', 'sap',
    'testing', 'c++', 'c#', 'ruby', 'php', 'go', 'rust'
  ];
  let skillsSet = new Set();
  userMessages.forEach(msg => {
    if (msg.includes('only ')) {
      skillsSet.clear();
    }
    skillKeywords.forEach(skill => {
      if (msg.includes(skill)) {
        skillsSet.add(skill.replace(/\b\w/g, c => c.toUpperCase()));
      }
    });
  });
  state.skills = Array.from(skillsSet);

  // Extract Focus
  if (userText.includes('personality') || userText.includes('behavior') || userText.includes('behaviour') || userText.includes('opq') || userText.includes('traits') || userText.includes('soft skills')) {
    state.personality = true;
  }
  if (userText.includes('cognitive') || userText.includes('aptitude') || userText.includes('reasoning') || userText.includes('ability') || userText.includes('verify') || userText.includes('g+')) {
    state.cognitive = true;
  }

  // Extract Safety Critical
  if (userText.includes('safety') || userText.includes('safe') || userText.includes('plant operator') || userText.includes('industrial') || userText.includes('manufacturing')) {
    state.safety = true;
  }

  // Extract Language
  if (userText.includes('spanish')) state.language = 'Spanish';
  else if (userText.includes('french')) state.language = 'French';
  else if (userText.includes('german')) state.language = 'German';
  else if (userText.includes('uk english') || userText.includes('british')) state.language = 'English (UK)';
  else if (userText.includes('english international')) state.language = 'English (International)';
  else if (userText.includes('us') || userText.includes('american')) state.language = 'English (USA)';

  return state;
};

// Handle checking role structure in messages safely
const msgRole = (msg) => {
  return msg.role || msg.get?.('role') || '';
};

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isFinal, setIsFinal] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [theme, setTheme] = useState('light');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [extractedState, setExtractedState] = useState({
    role: '',
    seniority: '',
    skills: [],
    personality: false,
    cognitive: false,
    safety: false,
    language: 'English (USA)'
  });

  // Recalculate extracted state on message updates
  useEffect(() => {
    setExtractedState(extractHiringContext(messages));
  }, [messages]);

  // Synchronise active theme class on document html element
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark-theme');
      document.documentElement.classList.remove('light-theme');
    } else {
      document.documentElement.classList.add('light-theme');
      document.documentElement.classList.remove('dark-theme');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleSendMessage = async (text) => {
    const newMessages = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setIsTyping(true);
    setErrorMsg('');

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ messages: newMessages }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Internal Server Error');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      setIsFinal(data.end_of_conversation);
    } catch (error) {
      console.error('Error fetching chat response:', error);
      
      let friendlyError = error.message;
      if (friendlyError.includes('429') || friendlyError.includes('RESOURCE_EXHAUSTED')) {
        friendlyError = 'Rate limit exceeded. Please wait a moment and retry!';
      }
      
      setErrorMsg(friendlyError);
      setMessages(prev => prev.slice(0, -1)); // Rollback user message
    } finally {
      setIsTyping(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
    setIsFinal(false);
    setErrorMsg('');
  };

  const turnCount = messages.filter(m => msgRole(m) === 'user').length;

  return (
    <>
      {/* Sidebar Navigation */}
      <Sidebar
        extractedState={extractedState}
        turnCount={turnCount}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(p => !p)}
      />

      {/* Main Content Area */}
      <div className={`app-workspace${sidebarOpen ? '' : ' sidebar-hidden'}`}>
        {/* Status indicator bar */}
        <StatusBar />

        {/* Chat Header */}
        <header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Show-sidebar button (only visible when sidebar is closed) */}
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="btn-reset"
                title="Show sidebar"
                style={{ padding: '6px 8px' }}
              >
                <PanelLeftOpen size={14} />
              </button>
            )}
            <div>
              <h2 className="header-title">SHL Assessment Recommender</h2>
              <p className="header-subtitle">
                AI-powered test battery suggestions tailored to your hiring needs
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={toggleTheme} className="btn-reset">
              {theme === 'light' ? <Moon size={12} /> : <Sun size={12} />}
              <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
            </button>

            <button onClick={handleReset} className="btn-reset">
              <RotateCcw size={12} />
              <span>Reset Agent</span>
            </button>
          </div>
        </header>

        {/* Global Error Banner */}
        {errorMsg && (
          <div className="error-banner">
            <AlertCircle size={14} className="shrink-0" />
            <span style={{ flex: 1 }}>{errorMsg}</span>
            <button onClick={() => setErrorMsg('')} className="error-close">
              ✕
            </button>
          </div>
        )}

        {/* Chat Scroll Window */}
        <ChatWindow messages={messages} isTyping={isTyping} />

        {/* Chat Bottom Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isFinal}
          isFinal={isFinal}
          isTyping={isTyping}
        />
      </div>
    </>
  );
}
