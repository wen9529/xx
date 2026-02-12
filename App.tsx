import React, { useState } from 'react';
import { Terminal, Bot, Github, FileText, Clipboard, Check } from 'lucide-react';
import { DEFAULT_STREAM_CONFIG, PYTHON_BOT_SCRIPT, GITHUB_WORKFLOW_TEMPLATE, GENERATE_ENV_CONTENT, GENERATE_SETUP_SCRIPT } from './constants';
import { StreamConfig } from './types';

const CodeBlock: React.FC<{ code: string; language?: string; filename?: string }> = ({ code, language = 'bash', filename }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 my-4 shadow-lg">
      <div className="flex justify-between items-center px-4 py-2 bg-gray-700/50 border-b border-gray-700">
        <span className="text-xs font-mono text-gray-300 uppercase">{filename}</span>
        <button onClick={handleCopy} className="p-1 text-gray-400 hover:text-white transition-colors">
          {copied ? <Check size={16} className="text-green-400" /> : <Clipboard size={16} />}
        </button>
      </div>
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-sm text-gray-200 whitespace-pre">{code}</pre>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const [config, setConfig] = useState<StreamConfig>(DEFAULT_STREAM_CONFIG);
  const [activeTab, setActiveTab] = useState<'setup' | 'bot' | 'workflow' | 'env'>('setup');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: value }));
  };

  // Generate contents dynamically
  const envCode = GENERATE_ENV_CONTENT(config);
  const botCode = PYTHON_BOT_SCRIPT;
  // NOTE: In the file system, setup.sh now contains the hardcoded bot.py for standalone usage. 
  // For the UI preview, we generate it dynamically to reflect any potential config changes if needed, 
  // or we can just display the raw script. 
  const setupCode = GENERATE_SETUP_SCRIPT(envCode, botCode);
  const workflowCode = GITHUB_WORKFLOW_TEMPLATE(config);

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white font-sans">
      <header className="h-16 border-b border-gray-800 bg-gray-900 flex items-center px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Terminal className="text-blue-500 h-6 w-6" />
          <h1 className="text-xl font-bold">StreamForge</h1>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-6">
          <div className="w-full lg:w-1/3 bg-gray-800 p-6 rounded-xl border border-gray-700 h-fit">
            <h2 className="font-bold mb-4 text-blue-400">Settings</h2>
            <div className="space-y-4">
               <div>
                <label className="text-xs text-gray-400">GitHub</label>
                <input name="githubUser" placeholder="User" value={config.githubUser} onChange={handleChange} className="input-field mb-2" />
                <input name="githubRepo" placeholder="Repo" value={config.githubRepo} onChange={handleChange} className="input-field mb-2" />
                <input name="githubPat" type="password" placeholder="PAT" value={config.githubPat} onChange={handleChange} className="input-field" />
              </div>
               <div>
                <label className="text-xs text-gray-400">Telegram</label>
                <input name="telegramBotToken" type="password" placeholder="Bot Token" value={config.telegramBotToken} onChange={handleChange} className="input-field mb-2" />
                <input name="telegramAdminId" placeholder="Admin ID" value={config.telegramAdminId} onChange={handleChange} className="input-field mb-2" />
                <input name="telegramRtmpUrl" placeholder="RTMP URL" value={config.telegramRtmpUrl} onChange={handleChange} className="input-field" />
              </div>
            </div>
          </div>

          <div className="w-full lg:w-2/3 flex flex-col bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[600px]">
            <div className="flex border-b border-gray-700 bg-gray-900/50">
              <button onClick={() => setActiveTab('setup')} className={`tab-btn ${activeTab === 'setup' ? 'active' : ''}`}><Terminal size={16} /> setup.sh</button>
              <button onClick={() => setActiveTab('env')} className={`tab-btn ${activeTab === 'env' ? 'active' : ''}`}><FileText size={16} /> .env</button>
              <button onClick={() => setActiveTab('bot')} className={`tab-btn ${activeTab === 'bot' ? 'active' : ''}`}><Bot size={16} /> bot.py</button>
              <button onClick={() => setActiveTab('workflow')} className={`tab-btn ${activeTab === 'workflow' ? 'active' : ''}`}><Github size={16} /> stream.yml</button>
            </div>
            <div className="flex-1 overflow-auto bg-[#1e1e1e] p-0">
               {activeTab === 'setup' && <div className="p-4"><CodeBlock code={setupCode} language="bash" filename="setup.sh" /></div>}
               {activeTab === 'env' && <div className="p-4"><CodeBlock code={envCode} language="bash" filename=".env" /></div>}
               {activeTab === 'bot' && <div className="p-4"><CodeBlock code={botCode} language="python" filename="bot.py" /></div>}
               {activeTab === 'workflow' && <div className="p-4"><CodeBlock code={workflowCode} language="yaml" filename="stream.yml" /></div>}
            </div>
          </div>
        </div>
      </main>
      <style>{`
        .input-field { width: 100%; background: #111827; border: 1px solid #374151; color: white; padding: 8px; border-radius: 4px; font-size: 13px; }
        .tab-btn { padding: 16px; font-size: 14px; display: flex; align-items: center; gap: 8px; color: #9ca3af; }
        .tab-btn.active { background: #1f2937; color: #3b82f6; border-top: 2px solid #3b82f6; }
      `}</style>
    </div>
  );
};

export default App;
