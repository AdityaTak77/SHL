import React, { useState } from 'react';
import { Send, Lock } from 'lucide-react';

export default function ChatInput({ onSendMessage, disabled, isFinal, isTyping }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled || isTyping) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="input-pane">
      <form onSubmit={handleSubmit} className="input-form">
        {isFinal ? (
          <div className="input-final-banner">
            <Lock size={15} />
            <span>Shortlist finalized. Conversation complete.</span>
          </div>
        ) : (
          <>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isTyping ? "Please wait..." : "Type your message here... (Press Enter to send)"}
              disabled={disabled || isTyping}
              rows={1}
              className="input-textarea"
            />
            <button
              type="submit"
              disabled={!input.trim() || disabled || isTyping}
              className="btn-send"
            >
              <Send size={16} />
            </button>
          </>
        )}
      </form>
    </div>
  );
}
