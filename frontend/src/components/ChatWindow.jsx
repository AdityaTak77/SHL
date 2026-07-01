import React, { useRef, useEffect } from 'react';
import { Bot, User as UserIcon } from 'lucide-react';

// Helper to format cells (handles links, brackets, etc.)
const formatCellContent = (content) => {
  content = content.trim();
  if (!content) return '—';

  // Handle URL inside brackets or angle brackets: <https://...>
  const urlRegex = /(?:https?:\/\/|www\.)[^\s\)\>]+/g;
  const match = content.match(urlRegex);
  
  if (match) {
    let url = match[0];
    // Clean up trailing slash/brackets
    url = url.replace(/[\>\)\s]+$/, '');
    if (!url.startsWith('http')) url = 'https://' + url;
    
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: '600' }}>
        LINK
      </a>
    );
  }

  return content;
};

// Custom Markdown Table Parser
const parseMessageContent = (text) => {
  if (!text) return null;

  const lines = text.split('\n');
  const renderedElements = [];
  let currentTable = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check if the line is part of a markdown table
    if (line.startsWith('|') && line.endsWith('|')) {
      const parts = line.split('|').map(p => p.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      
      // Check if it's the divider row: |---|---|
      if (line.includes('---') || line.includes('===') || parts.every(p => /^[-=]+$/.test(p))) {
        continue;
      }

      if (!currentTable) {
        // Start new table
        currentTable = {
          headers: parts,
          rows: []
        };
      } else {
        // Add row to existing table
        currentTable.rows.push(parts);
      }
    } else {
      // If we were parsing a table, close it first
      if (currentTable) {
        renderedElements.push(renderTable(currentTable, renderedElements.length));
        currentTable = null;
      }

      // Add normal line text (skip empty lines if not separating paragraphs)
      if (line) {
        renderedElements.push(
          <p key={`p-${i}`} style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.6', marginBottom: '8px' }}>
            {line}
          </p>
        );
      }
    }
  }

  // If table remains open at the end
  if (currentTable) {
    renderedElements.push(renderTable(currentTable, renderedElements.length));
  }

  return renderedElements;
};

// Render Table Object to JSX
const renderTable = (table, index) => {
  return (
    <div key={`table-${index}`} className="markdown-table-wrapper">
      <table className="markdown-table">
        <thead>
          <tr>
            {table.headers.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx}>{formatCellContent(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default function ChatWindow({ messages, isTyping }) {
  const bottomRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="chat-pane">
      {messages.length === 0 ? (
        <div className="chat-empty">
          <div className="chat-empty-icon">
            <Bot size={28} />
          </div>
          <h3 className="chat-empty-title">
            Welcome to the SHL Assessment Recommender!
          </h3>
          <p className="chat-empty-desc">
            Tell me about the role you are hiring for. For example, try typing: 
            <span className="chat-empty-sample">
              "We need to hire a senior Java developer with AWS and Spring experience."
            </span>
          </p>
        </div>
      ) : (
        messages.map((msg, index) => (
          <div 
            key={index} 
            className={`message-container animate-message ${msg.role === 'user' ? 'user' : 'assistant'}`}
          >
            {/* Avatar */}
            <div className="message-avatar">
              {msg.role === 'user' ? <UserIcon size={16} /> : <Bot size={16} />}
            </div>

            {/* Bubble */}
            <div className="message-bubble">
              {parseMessageContent(msg.content)}
            </div>
          </div>
        ))
      )}

      {/* Loading Indicator */}
      {isTyping && (
        <div className="message-container assistant">
          <div className="message-avatar">
            <Bot size={16} />
          </div>
          <div className="message-bubble" style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 16px' }}>
            <span className="pulse-dot"></span>
            <span className="pulse-dot"></span>
            <span className="pulse-dot"></span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
