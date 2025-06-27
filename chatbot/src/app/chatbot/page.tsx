'use client'

import React, { useState, useEffect, useRef } from 'react';
import { Send, BarChart3, Settings } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  text: string;
  isUser: boolean;
  evaluation?: {
    overall_score: number;
    correctness?: { correct: boolean; explanation: string };
    relevance?: { score: number; explanation: string };
    groundedness?: { grounded: boolean; explanation: string };
    retrieval_relevance?: { score: number; explanation: string };
  };
}

const LoadingDots = () => (
  <div className="flex space-x-2">
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
  </div>
);

// Evaluation results component
const EvaluationResults = ({ evaluation }: { evaluation: any }) => (
  <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
    <div className="flex items-center gap-2 mb-2">
      <BarChart3 className="w-4 h-4 text-indigo-600" />
      <span className="text-sm font-semibold text-gray-800">
        Evaluation Results (Overall: {evaluation.overall_score?.toFixed(1)}/5)
      </span>
    </div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
      {evaluation.correctness && (
        <div className="p-2 bg-white rounded border">
          <div className="flex items-center gap-1 mb-1">
            <span className="font-medium">Correctness:</span>
            <span className={`px-1 py-0.5 rounded text-xs ${
              evaluation.correctness.correct 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'
            }`}>
              {evaluation.correctness.correct ? 'Correct' : 'Incorrect'}
            </span>
          </div>
          <p className="text-gray-600">{evaluation.correctness.explanation}</p>
        </div>
      )}
      
      {evaluation.relevance && (
        <div className="p-2 bg-white rounded border">
          <div className="flex items-center gap-1 mb-1">
            <span className="font-medium">Relevance:</span>
            <span className="px-1 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
              {evaluation.relevance.score}/5
            </span>
          </div>
          <p className="text-gray-600">{evaluation.relevance.explanation}</p>
        </div>
      )}
      
      {evaluation.groundedness && (
        <div className="p-2 bg-white rounded border">
          <div className="flex items-center gap-1 mb-1">
            <span className="font-medium">Groundedness:</span>
            <span className={`px-1 py-0.5 rounded text-xs ${
              evaluation.groundedness.grounded 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'
            }`}>
              {evaluation.groundedness.grounded ? 'Grounded' : 'Not Grounded'}
            </span>
          </div>
          <p className="text-gray-600">{evaluation.groundedness.explanation}</p>
        </div>
      )}
      
      {evaluation.retrieval_relevance && (
        <div className="p-2 bg-white rounded border">
          <div className="flex items-center gap-1 mb-1">
            <span className="font-medium">Retrieval:</span>
            <span className="px-1 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
              {evaluation.retrieval_relevance.score}/5
            </span>
          </div>
          <p className="text-gray-600">{evaluation.retrieval_relevance.explanation}</p>
        </div>
      )}
    </div>
  </div>
);

export default function ChatbotPage() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluationEnabled, setEvaluationEnabled] = useState(false);
  const [groundTruth, setGroundTruth] = useState('');
  const [showEvaluationPanel, setShowEvaluationPanel] = useState(false);
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
      const endpoint = evaluationEnabled ? '/query_with_evaluation' : '/query';
      const requestBody = evaluationEnabled 
        ? { 
            question: userMessage, 
            n_results: 5,
            ground_truth: groundTruth.trim() || undefined
          }
        : { 
            question: userMessage, 
            n_results: 5 
          };

      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error('Failed to get response from server');
      }

      const data = await response.json();
      
      if (evaluationEnabled && data.query_response) {
        // Handle evaluated response
        setMessages(prev => [...prev, { 
          text: data.query_response.answer, 
          isUser: false,
          evaluation: data.evaluation
        }]);
      } else {
        // Handle regular response
        setMessages(prev => [...prev, { text: data.answer, isUser: false }]);
      }
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
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-4xl font-bold text-slate-800 tracking-tight">
            CHATBOT
          </h1>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowEvaluationPanel(!showEvaluationPanel)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                showEvaluationPanel 
                  ? 'bg-indigo-100 border-indigo-300 text-indigo-700' 
                  : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <Settings className="w-4 h-4" />
              Evaluation
            </button>
            <button
              onClick={() => setEvaluationEnabled(!evaluationEnabled)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                evaluationEnabled 
                  ? 'bg-green-100 border-green-300 text-green-700' 
                  : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              {evaluationEnabled ? 'Evaluation ON' : 'Evaluation OFF'}
            </button>
          </div>
        </div>

        {/* Evaluation Panel */}
        {showEvaluationPanel && (
          <div className="mb-6 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-3">Evaluation Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Enable Evaluation
                </label>
                <button
                  onClick={() => setEvaluationEnabled(!evaluationEnabled)}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    evaluationEnabled 
                      ? 'bg-green-100 border-green-300 text-green-700' 
                      : 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {evaluationEnabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>
              
              {evaluationEnabled && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Ground Truth (Optional)
                  </label>
                  <textarea
                    value={groundTruth}
                    onChange={(e) => setGroundTruth(e.target.value)}
                    placeholder="Enter the expected correct answer for evaluation..."
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                    rows={3}
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Providing ground truth enables correctness evaluation
                  </p>
                </div>
              )}
              
              <div className="text-sm text-slate-600">
                <p><strong>Evaluation Metrics:</strong></p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li><strong>Correctness:</strong> Compares against ground truth (if provided)</li>
                  <li><strong>Relevance:</strong> How well the answer addresses the question (1-5)</li>
                  <li><strong>Groundedness:</strong> Whether the answer is supported by context</li>
                  <li><strong>Retrieval Relevance:</strong> Quality of retrieved documents (1-5)</li>
                </ul>
              </div>
            </div>
          </div>
        )}

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
                      <div>
                        <div className="prose prose-sm max-w-none">
                          <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>
                        {msg.evaluation && <EvaluationResults evaluation={msg.evaluation} />}
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