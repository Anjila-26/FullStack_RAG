'use client'

import React, { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  text: string;
  isUser: boolean;
}

const LoadingDots = () => (
  <div className="flex space-x-2">
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
  </div>
);

export default function ChatbotPage() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!message.trim() || isLoading) return;

    const userMessage = message.trim();
    setMessage('');
    setMessages(prev => [...prev, { text: userMessage, isUser: true }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage,
          n_results: 5
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response from server');
      }

      const data = await response.json();
      setMessages(prev => [...prev, { text: data.answer, isUser: false }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error. Please try again later.',
        isUser: false 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 flex flex-col">
      <div className="flex-1 max-w-4xl mx-auto w-full p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800 tracking-tight">
            CHATBOT
          </h1>
        </div>

        {/* Chat Messages Area */}
        <div className={messages.length === 0 ? "" : "flex-1 pb-32"}>
          {messages.length === 0 ? (
            <div className="min-h-[60vh] flex flex-col items-center justify-center text-center space-y-8">
              <h2 className="text-2xl font-semibold text-slate-700">
                What can I help you with?
              </h2>
              
              {/* Centered Input Area (when no messages) */}
              <div className="w-full max-w-4xl">
                <div className="w-full flex items-center bg-slate-50 rounded-2xl border border-slate-200 p-2 hover:bg-slate-100 transition-colors duration-200">
                  <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask questions related to the pdf ....."
                    className="flex-1 bg-transparent px-4 py-3 text-slate-700 placeholder-slate-400 focus:outline-none"
                  />
                  <button
                    onClick={handleSendMessage}
                    className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 transition-colors duration-200 shadow-lg hover:shadow-xl"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`p-4 rounded-lg ${
                      msg.isUser
                        ? 'max-w-[50%] text-white rounded-br-sm'
                        : 'w-full text-black'
                    }`}
                    style={msg.isUser ? { backgroundColor: '#627EEE' } : {}}
                  >
                    {msg.isUser ? (
                      msg.text
                    ) : (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="p-4 rounded-lg w-full text-black">
                    <LoadingDots />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Fixed Input Area at Bottom (only when messages exist) */}
      {messages.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-br from-slate-50 to-indigo-50 p-6">
          <div className="max-w-4xl mx-auto">
            <div className="w-full flex items-center bg-slate-50 rounded-2xl border border-slate-200 p-2 hover:bg-slate-100 transition-colors duration-200">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask questions related to the pdf ....."
                className="flex-1 bg-transparent px-4 py-3 text-slate-700 placeholder-slate-400 focus:outline-none"
              />
              <button
                onClick={handleSendMessage}
                className="bg-indigo-600 text-white p-3 rounded-lg hover:bg-indigo-700 transition-colors duration-200 shadow-lg hover:shadow-xl"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Character Avatar */}
      <div className="fixed bottom-20 right-8">
        <div className="w-50 h-80 relative">
          <img 
            src="/images/luffy.png" 
            alt="Luffy Character" 
            className="w-full h-full object-cover"
          />
        </div>
      </div>
    </div>
  );
}