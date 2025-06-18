'use client'

import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ChatbotUI() {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear document context when component mounts
  useEffect(() => {
    const clearContext = async () => {
      try {
        const response = await fetch('http://localhost:8000/clear', {
          method: 'DELETE',
        });
        
        if (!response.ok) {
          console.error('Failed to clear document context');
        }
      } catch (error) {
        console.error('Error clearing document context:', error);
      }
    };

    clearContext();
  }, []); // Empty dependency array means this runs once when component mounts

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files ? Array.from(e.target.files) : [];
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleProcessPDF = async () => {
    if (files.length === 0) {
      setError('Please select at least one file to process');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Failed to upload ${file.name}`);
        }
      }

      // If all uploads are successful, navigate to chat
      router.push('/chatbot');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process files');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800 tracking-tight">
            CHATBOT
          </h1>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-2xl border border-slate-200 p-8">
          {/* Upload Area */}
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${
              dragOver
                ? 'border-indigo-400 bg-indigo-50'
                : 'border-slate-300 hover:border-indigo-300 hover:bg-slate-50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="space-y-6">
              <div className="flex justify-center">
                <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center">
                  <Upload className="w-8 h-8 text-indigo-600" />
                </div>
              </div>
              
              <div>
                <p className="text-lg text-slate-600 mb-4">
                  Drag and Drop PDF, or click to select files
                </p>
                
                <button
                  onClick={handleUploadClick}
                  className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors duration-200 shadow-lg hover:shadow-xl"
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Upload
                </button>
              </div>
            </div>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">
                Uploaded Files ({files.length})
              </h3>
              <div className="space-y-2">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200"
                  >
                    <div className="flex items-center space-x-3">
                      <FileText className="w-5 h-5 text-slate-500" />
                      <span className="text-slate-700 font-medium">
                        {file.name}
                      </span>
                      <span className="text-slate-500 text-sm">
                        ({Math.round(file.size / 1024)} KB)
                      </span>
                    </div>
                    <button
                      onClick={() => removeFile(index)}
                      className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {/* Process PDF Button */}
                <button 
                  onClick={handleProcessPDF}
                  disabled={isProcessing}
                  className={`w-50 bg-indigo-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl text-sm cursor-pointer ${
                    isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-indigo-700'
                  }`}
                >
                  {isProcessing ? 'Processing...' : 'Process PDF'}
                </button>
                {error && (
                  <p className="text-red-500 mt-2 text-sm">{error}</p>
                )}
              </div>
            </div>
          )}

          {/* No Documents State */}
          {files.length === 0 && (
            <div className="mt-12 text-center">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl mb-6">
                <div className="w-12 h-16 bg-gradient-to-b from-blue-500 to-indigo-600 rounded-md relative">
                  <div className="absolute inset-x-2 top-2 space-y-1">
                    <div className="h-0.5 bg-white/70 rounded"></div>
                    <div className="h-0.5 bg-white/70 rounded"></div>
                    <div className="h-0.5 bg-white/70 rounded"></div>
                  </div>
                </div>
              </div>
              
              <h2 className="text-2xl font-bold text-slate-800 mb-2">
                No Documents
              </h2>
              <p className="text-slate-600">
                Start by uploading a document first
              </p>
            </div>
          )}

          {/* Character Avatar */}
          <div className="fixed bottom-8 right-8">
            <div className="w-50 h-80 relative mb-4">
              <img 
                src="/images/luffy.png" 
                alt="Luffy Character" 
                className="w-full h-full object-cover"
              />
            </div>
            
          </div>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.doc,.docx,.txt"
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
}