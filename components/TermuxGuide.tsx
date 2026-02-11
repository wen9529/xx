import React, { useState } from 'react';
import { CodeBlock } from './CodeBlock';
import { TERMUX_SETUP_SCRIPT, PYTHON_BOT_SCRIPT, GITHUB_WORKFLOW_TEMPLATE, DEFAULT_STREAM_CONFIG } from '../constants';
import { StreamConfig } from '../types';
import { Terminal, Bot, Github, Save, Lock } from 'lucide-react';

export const TermuxGuide: React.FC = () => {
  const [config, setConfig] = useState<StreamConfig>(DEFAULT_STREAM_CONFIG);
  const [activeTab, setActiveTab] = useState<'setup' | 'bot' | 'workflow'>('setup');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: value }));
  };

  const setupCode = TERMUX_SETUP_SCRIPT(config);
  const botCode = PYTHON_BOT_SCRIPT;
  const workflowCode = GITHUB_WORKFLOW_TEMPLATE(config);

  return (
    <div className="max-w-6xl mx-auto p-6 h-full flex flex-col md:flex-row gap-6 animate-fade-in">
      {/* Config Panel */}
      <div className="w-full md:w-1/3 bg-gray-800 p-6 rounded-xl border border-gray-700 overflow-y-auto">
        <div className="flex items-center gap-2 mb-6 text-primary-500">
          <Save size={24} />
          <h2 className="text-xl font-bold text-white">Project Config</h2>
        </div>
        
        <p className="text-xs text-gray-400 mb-6">
          填写以下信息，我们将为您生成所有 Termux 和 GitHub 所需的代码。
        </p>

        <div className="space-y-4">
          <div className="border-b border-gray-700 pb-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Github size={16} /> GitHub Details
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Username (Owner)</label>
                <input type="text" name="githubUser" value={config.githubUser} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Repository Name</label>
                <input type="text" name="githubRepo" value={config.githubRepo} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Personal Access Token (PAT)</label>
                <input type="password" name="githubPat" value={config.githubPat} onChange={handleChange} placeholder="github_pat_..." className="input-field" />
                <p className="text-[10px] text-gray-500 mt-1">Needed for the Bot to trigger Actions.</p>
              </div>
            </div>
          </div>

          <div className="border-b border-gray-700 pb-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Bot size={16} /> Telegram Bot
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Bot Token</label>
                <input type="password" name="telegramBotToken" value={config.telegramBotToken} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Admin User ID</label>
                <input type="text" name="telegramAdminId" value={config.telegramAdminId} onChange={handleChange} className="input-field" />
              </div>
            </div>
          </div>

          <div>
             <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Terminal size={16} /> Stream Target
            </h3>
            <label className="block text-xs text-gray-400 mb-1">Telegram RTMP URL</label>
            <input type="text" name="telegramRtmpUrl" value={config.telegramRtmpUrl} onChange={handleChange} className="input-field" />
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      <div className="w-full md:w-2/3 flex flex-col">
        <div className="flex gap-2 mb-4 bg-gray-800 p-1 rounded-lg w-fit">
          <button 
            onClick={() => setActiveTab('setup')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'setup' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            setup.sh (Termux)
          </button>
          <button 
            onClick={() => setActiveTab('bot')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'bot' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            bot.py (Manager)
          </button>
          <button 
            onClick={() => setActiveTab('workflow')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'workflow' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            stream.yml (GitHub)
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          {activeTab === 'setup' && (
            <div className="space-y-2">
              <div className="bg-blue-900/20 border border-blue-900/50 p-4 rounded-lg text-sm text-blue-200">
                <p className="font-bold mb-1">部署指南:</p>
                <ol className="list-decimal list-inside space-y-1 text-gray-300">
                  <li>在 GitHub 创建仓库 <code>{config.githubRepo}</code></li>
                  <li>将这3个文件上传到仓库根目录 (yml文件放 <code>.github/workflows/</code>)</li>
                  <li>在 GitHub Settings &gt; Secrets 添加 <code>TELEGRAM_STREAM_KEY</code></li>
                  <li>在 Termux 运行: <code>git clone https://github.com/{config.githubUser}/{config.githubRepo} && cd {config.githubRepo} && bash setup.sh</code></li>
                </ol>
              </div>
              <CodeBlock code={setupCode} language="bash" title="setup.sh" />
            </div>
          )}

          {activeTab === 'bot' && (
             <div className="space-y-2">
                <p className="text-sm text-gray-400">这个机器人会自动读取 setup.sh 生成的环境变量。把它和 setup.sh 放在同一个目录下。</p>
                <CodeBlock code={botCode} language="python" title="bot.py" />
             </div>
          )}

          {activeTab === 'workflow' && (
            <div className="space-y-2">
               <p className="text-sm text-gray-400">确保在 GitHub Secrets 中配置了推流密钥 (STREAM_KEY)。</p>
               <CodeBlock code={workflowCode} language="yaml" title=".github/workflows/stream.yml" />
            </div>
          )}
        </div>
      </div>
      
      <style>{`
        .input-field {
          width: 100%;
          background-color: rgb(17 24 39);
          border: 1px solid rgb(55 65 81);
          border-radius: 0.375rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          line-height: 1.25rem;
          color: white;
          transition: border-color 0.2s;
        }
        .input-field:focus {
          outline: none;
          border-color: rgb(59 130 246);
        }
      `}</style>
    </div>
  );
};
