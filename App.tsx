import React, { useState } from 'react';
import { TermuxGuide } from './components/TermuxGuide';
import { WorkflowGenerator } from './components/WorkflowGenerator';
import { GeminiChat } from './components/GeminiChat';
import { AppView } from './types';
import { Terminal, Bot, Workflow, Layers } from 'lucide-react';

const App: React.FC = () => {
  const [view, setView] = useState<AppView>(AppView.TERMUX_GUIDE);

  const renderView = () => {
    switch (view) {
      case AppView.TERMUX_GUIDE:
        return <TermuxGuide />; // Now acts as the Repository Generator
      case AppView.WORKFLOW_GENERATOR:
        return <WorkflowGenerator />;
      case AppView.AI_ASSISTANT:
        return <GeminiChat />;
      default:
        return <TermuxGuide />;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="h-16 border-b border-gray-800 bg-gray-900 flex items-center justify-between px-6 flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2 rounded-lg shadow-lg shadow-blue-500/20">
            <Layers className="text-white h-5 w-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            StreamForge
          </h1>
        </div>
        <div className="text-xs text-gray-500 font-mono hidden md:block">
          v2.0.0 | One-Click Deploy • Bot Control
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="w-64 bg-gray-800/30 border-r border-gray-800 flex flex-col hidden md:flex">
          <div className="p-4 space-y-2">
            <button
              onClick={() => setView(AppView.TERMUX_GUIDE)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                view === AppView.TERMUX_GUIDE
                  ? 'bg-primary-600/10 text-primary-500 border border-primary-500/20'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Terminal size={18} />
              Deploy Generator
            </button>

            <button
              onClick={() => setView(AppView.WORKFLOW_GENERATOR)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                view === AppView.WORKFLOW_GENERATOR
                  ? 'bg-primary-600/10 text-primary-500 border border-primary-500/20'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Workflow size={18} />
              Manual Workflow
            </button>

            <button
              onClick={() => setView(AppView.AI_ASSISTANT)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                view === AppView.AI_ASSISTANT
                  ? 'bg-primary-600/10 text-primary-500 border border-primary-500/20'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Bot size={18} />
              AI Assistant
            </button>
          </div>
          
          <div className="mt-auto p-4 border-t border-gray-800">
            <div className="bg-gray-900 rounded-lg p-3">
              <p className="text-xs text-gray-500 leading-relaxed">
                <strong className="text-gray-300">Tip:</strong> The Deployment Generator creates a complete repository structure for Termux.
              </p>
            </div>
          </div>
        </nav>

        {/* Mobile Nav Tabs */}
        <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-gray-900 border-t border-gray-800 flex justify-around items-center z-50">
           <button onClick={() => setView(AppView.TERMUX_GUIDE)} className={`p-2 ${view === AppView.TERMUX_GUIDE ? 'text-primary-500' : 'text-gray-400'}`}><Terminal /></button>
           <button onClick={() => setView(AppView.WORKFLOW_GENERATOR)} className={`p-2 ${view === AppView.WORKFLOW_GENERATOR ? 'text-primary-500' : 'text-gray-400'}`}><Workflow /></button>
           <button onClick={() => setView(AppView.AI_ASSISTANT)} className={`p-2 ${view === AppView.AI_ASSISTANT ? 'text-primary-500' : 'text-gray-400'}`}><Bot /></button>
        </div>

        {/* Main Content */}
        <main className="flex-1 overflow-auto bg-gray-900 relative">
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>
          {renderView()}
        </main>
      </div>
    </div>
  );
};

export default App;
