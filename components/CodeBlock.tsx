import React, { useState } from 'react';
import { Clipboard, Check } from 'lucide-react';

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ code, language = 'bash', title }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 my-4 shadow-lg">
      <div className="flex justify-between items-center px-4 py-2 bg-gray-700/50 border-b border-gray-700">
        <span className="text-xs font-mono text-gray-300 uppercase">{title || language}</span>
        <button
          onClick={handleCopy}
          className="text-gray-400 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check size={16} className="text-green-400" /> : <Clipboard size={16} />}
        </button>
      </div>
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-sm text-gray-200 whitespace-pre">
          {code}
        </pre>
      </div>
    </div>
  );
};
