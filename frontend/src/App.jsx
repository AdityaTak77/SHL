import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import StatusBar from './components/StatusBar';
import { RotateCcw, AlertCircle, Sun, Moon } from 'lucide-react';

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

  // Extract Role
  if (userText.includes('frontend') || userText.includes('front end')) state.role = 'Frontend Developer';
  else if (userText.includes('backend') || userText.includes('back end')) state.role = 'Backend Developer';
  else if (userText.includes('full stack') || userText.includes('fullstack')) state.role = 'Full Stack Developer';
  else if (userText.includes('java')) state.role = 'Java Developer';
  else if (userText.includes('sales')) state.role = 'Sales Professional';
  else if (userText.includes('contact centre') || userText.includes('call center') || userText.includes('customer service')) state.role = 'Customer Service Representative';
  else if (userText.includes('devops') || userText.includes('sre') || userText.includes('docker') || userText.includes('kubernetes')) state.role = 'DevOps / SRE Engineer';
  else if (userText.includes('data scientist') || userText.includes('machine learning') || userText.includes('ml')) state.role = 'Data Scientist';
  else if (userText.includes('data engineer')) state.role = 'Data Engineer';
  else if (userText.includes('python')) state.role = 'Python Developer';
  else if (userText.includes('marketing') || userText.includes('digital marketing')) state.role = 'Marketing Professional';
  else if (userText.includes('manager') || userText.includes('lead')) state.role = 'Management / Team Leader';
  else if (userText.includes('leadership') || userText.includes('executive') || userText.includes('director') || userText.includes('cxo')) state.role = 'Executive Leadership';
  else if (userText.includes('qa ') || userText.includes('quality assurance') || userText.includes('tester')) state.role = 'QA Engineer';
  else if (userText.includes('software engineer') || userText.includes('developer') || userText.includes('swe')) state.role = 'Software Engineer';
  else {
    // Try to guess first few words from initial prompt
    const firstUserMsg = messages.find(m => msgRole(m) === 'user');
    if (firstUserMsg) {
      const match = firstUserMsg.content.match(/(?:hire|hiring|need a|for a)\s+([a-zA-Z\s\-]+?)(?:\.|\,|$|\s+with|\s+who)/i);
      if (match && match[1]) state.role = match[1].trim().replace(/\b\w/g, c => c.toUpperCase());
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
        friendlyError = 'Gemini API limit exceeded. Please wait 45-60 seconds for the daily/minute cooldown to reset and retry!';
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
      <Sidebar extractedState={extractedState} turnCount={turnCount} />

      {/* Main Content Area */}
      <div className="app-workspace">
        {/* Status indicator bar */}
        <StatusBar />

        {/* Chat Header */}
        <header className="app-header">
          <div>
            <h2 className="header-title">
              Conversational Battery Design
            </h2>
            <p className="header-subtitle">
              Interactive session with candidate requirements evaluation
            </p>
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
