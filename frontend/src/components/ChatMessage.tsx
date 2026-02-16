import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ChatMessage.css';

interface ToolMetadata {
  tool_used: boolean;
  tool_name?: string;
  tool_code?: string;
  tool_output?: string;
  tool_error?: string;
  tool_metadata?: Record<string, any>;
}

// Legacy support
interface ExecutionMetadata {
  code_executed: boolean;
  execution_code?: string;
  execution_output?: string;
  execution_error?: string;
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  executionMetadata?: ExecutionMetadata;
  toolMetadata?: ToolMetadata;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ role, content, executionMetadata, toolMetadata }) => {
  const [showDebug, setShowDebug] = useState(false);

  // Detect if a tool was used based on content patterns
  // BUT exclude search results (which start with 🔍 or contain search-related text)
  // AND exclude global search denial messages
  // AND exclude product search results
  const isSearchResult = content.includes('🔍') && (
    content.includes('result(s) for') || 
    content.includes('SEARCH HISTORY FOR') ||
    content.includes('No conversations found') ||
    content.includes('Prompt:') ||
    content.includes('Response:')
  );
  const isGlobalSearchDenial = content.includes('Global search is admin-only') || content.includes('I can only search your own conversations');
  const isProductSearchResult = content.includes('AwesomeGear') || 
    content.includes('product(s) in our') ||
    content.includes('No products found') ||
    (content.includes('apparel') && content.includes('drinkware') && content.includes('accessories'));
  const toolPatterns = [
    /🔧 Using .* tool/i,
    /Curl stderr:/i,
    /Tool executed/i,
    /curl:/i,
    /Command:/i,
    /execution result/i,
  ];
  const hasToolIndicator = !isSearchResult && !isGlobalSearchDenial && !isProductSearchResult && role === 'assistant' && toolPatterns.some(p => p.test(content));

  // Extract metadata from content if embedded
  let displayContent = content;
  let metadata: ToolMetadata | ExecutionMetadata | undefined = toolMetadata || executionMetadata;

  // Check for new tool metadata format - use regex with dotall flag for multiline JSON
  if (!metadata && content.includes('<!-- TOOL_METADATA:')) {
    const metadataMatch = content.match(/<!-- TOOL_METADATA: ([\s\S]*?) -->/);
    if (metadataMatch) {
      try {
        metadata = JSON.parse(metadataMatch[1]);
      } catch (e) {
        console.error('Failed to parse tool metadata:', e);
      }
    }
  }
  
  // Always strip TOOL_METADATA comments and tool progress messages from display
  // These should never be shown to the user
  displayContent = displayContent
    .replace(/<!-- TOOL_METADATA:[\s\S]*?-->/g, '')  // Remove metadata comments
    .replace(/🔧 Using .* tool\.{3}\n*/gi, '')       // Remove "Using X tool..."
    .replace(/⚙️ Executing\.{3}\n*/g, '')           // Remove "Executing..."
    .replace(/✅ Tool executed successfully\n*/g, '') // Remove "Tool executed successfully"
    .replace(/\n{3,}/g, '\n\n')                      // Collapse multiple newlines
    .trim();
  
  // Check for legacy execution metadata - use regex with [\s\S] for multiline
  if (!metadata && content.includes('<!-- EXECUTION_METADATA:')) {
    const metadataMatch = content.match(/<!-- EXECUTION_METADATA: ([\s\S]*?) -->/);
    if (metadataMatch) {
      try {
        const legacyMetadata = JSON.parse(metadataMatch[1]) as ExecutionMetadata;
        // Convert to new format
        metadata = {
          tool_used: legacyMetadata.code_executed,
          tool_name: 'math',
          tool_code: legacyMetadata.execution_code,
          tool_output: legacyMetadata.execution_output,
          tool_error: legacyMetadata.execution_error,
        };
        displayContent = content.replace(/<!-- EXECUTION_METADATA:[\s\S]*?-->/, '').trim();
      } catch (e) {
        console.error('Failed to parse execution metadata:', e);
        // Even if parsing fails, still remove the comment from display
        displayContent = content.replace(/<!-- EXECUTION_METADATA:[\s\S]*?-->/, '').trim();
      }
    }
  }

  const hasExecution = metadata && ((metadata as ToolMetadata).tool_used || (metadata as ExecutionMetadata).code_executed);
  const toolName = (metadata as ToolMetadata)?.tool_name || 'tool';
  const toolCode = (metadata as ToolMetadata)?.tool_code || (metadata as ExecutionMetadata)?.execution_code;
  const toolOutput = (metadata as ToolMetadata)?.tool_output || (metadata as ExecutionMetadata)?.execution_output;
  const toolError = (metadata as ToolMetadata)?.tool_error || (metadata as ExecutionMetadata)?.execution_error;

  // Show debug button if we have metadata OR if content indicates tool usage
  // BUT not for search results, global search denial messages, conversation_memory, product_search, math, debug, webpage_summary, or mcp tool
  const isConversationMemory = toolName === 'conversation_memory';
  const isProductSearch = toolName === 'product_search';
  const isMathTool = toolName === 'math';
  const isDebugTool = toolName === 'debug';
  const isWebpageSummary = toolName === 'webpage_summary';
  const isMCPTool = toolName === 'mcp';
  const showDebugButton = (hasExecution || hasToolIndicator) && !isSearchResult && !isGlobalSearchDenial && !isConversationMemory && !isProductSearch && !isProductSearchResult && !isMathTool && !isDebugTool && !isWebpageSummary && !isMCPTool;

  // For math tool: extract just the numeric result (strip code blocks and markdown)
  if (isMathTool && toolOutput) {
    // Extract just the numeric result from the tool output (last non-empty line)
    const lines = toolOutput.trim().split('\n');
    const numericResult = lines[lines.length - 1].trim();
    displayContent = numericResult;
  }

  // For product search: strip ALL markdown and JSON - show only plain text
  if (isProductSearch || isProductSearchResult) {
    displayContent = displayContent
      // Remove code blocks (```json...``` or ```...```)
      .replace(/```[\s\S]*?```/g, '')
      // Remove bold markdown
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      // Remove italic markdown
      .replace(/\*([^*]+)\*/g, '$1')
      // Remove any remaining JSON-like structures
      .replace(/\{[\s\S]*?\}/g, '')
      // Remove bullet points
      .replace(/^[\s]*[-*•]\s*/gm, '')
      // Remove numbered lists
      .replace(/^[\s]*\d+\.\s*/gm, '')
      // Collapse multiple newlines
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    
    // If we have tool output, prefer showing that directly
    if (toolOutput && !displayContent.includes('Found') && !displayContent.includes('product')) {
      displayContent = toolOutput;
    }
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '🐵' : '🤖'}
      </div>
      <div className="message-content">
        {/* Simple debug button - always visible when tool detected */}
        {showDebugButton && (
          <div className="debug-badge">
            <button
              className="debug-toggle"
              onClick={() => setShowDebug(!showDebug)}
              title="Show raw tool output"
            >
              🐛 Debug {showDebug ? '▼' : '▶'}
            </button>
          </div>
        )}

        {showDebug && (
          <div className="debug-panel">
            <h4>🔍 Raw Tool Output:</h4>
            <div className="debug-content">
              {toolOutput && (
                <div className="debug-section">
                  <h5>✅ Standard Output:</h5>
                  <pre className="debug-output">{toolOutput}</pre>
                </div>
              )}
              {toolError && (
                <div className="debug-section">
                  <h5>❌ Error Output:</h5>
                  <pre className="debug-error">{toolError}</pre>
                </div>
              )}
              {(metadata as ToolMetadata)?.tool_metadata && (
                <div className="debug-section">
                  <h5>ℹ️ Metadata:</h5>
                  <pre className="debug-metadata">{JSON.stringify((metadata as ToolMetadata).tool_metadata, null, 2)}</pre>
                </div>
              )}
              {toolCode && (
                <div className="debug-section">
                  <h5>📝 Generated Code:</h5>
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  customStyle={{ 
                    margin: '8px 0', 
                    borderRadius: '4px',
                    whiteSpace: 'pre-wrap',
                    wordWrap: 'break-word',
                    wordBreak: 'break-all',
                    overflowX: 'hidden'
                  }}
                  wrapLongLines={true}
                >
                  {toolCode}
                </SyntaxHighlighter>
                </div>
              )}
              {!toolOutput && !toolError && !toolCode && (
                <p className="debug-empty">No detailed tool output available. The AI processed the tool result internally.</p>
              )}
            </div>
          </div>
        )}

        <ReactMarkdown
          components={{
            code({ node, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              const isInline = (props as any).inline;
              // Use SyntaxHighlighter for code blocks (not inline), otherwise use <code>
              return !isInline && match ? (
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    whiteSpace: 'pre-wrap',
                    wordWrap: 'break-word',
                    wordBreak: 'break-all',
                    overflowX: 'hidden',
                    maxWidth: '100%'
                  }}
                  wrapLongLines={true}
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {displayContent}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default ChatMessage;
