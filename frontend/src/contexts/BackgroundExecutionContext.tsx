import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface ExecutionState {
  conversationId: string;
  isExecuting: boolean;
  controller?: AbortController;
}

interface BackgroundExecutionContextType {
  executingConversations: Set<string>;
  startExecution: (conversationId: string, controller: AbortController) => void;
  stopExecution: (conversationId: string) => void;
  isExecuting: (conversationId: string) => boolean;
}

const BackgroundExecutionContext = createContext<BackgroundExecutionContextType | undefined>(undefined);

export const BackgroundExecutionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [executions, setExecutions] = useState<Map<string, ExecutionState>>(new Map());

  const startExecution = useCallback((conversationId: string, controller: AbortController) => {
    setExecutions(prev => {
      const newMap = new Map(prev);
      newMap.set(conversationId, {
        conversationId,
        isExecuting: true,
        controller
      });
      return newMap;
    });
  }, []);

  const stopExecution = useCallback((conversationId: string) => {
    setExecutions(prev => {
      const newMap = new Map(prev);
      const execution = newMap.get(conversationId);
      if (execution?.controller) {
        execution.controller.abort();
      }
      newMap.delete(conversationId);
      return newMap;
    });
  }, []);

  const isExecuting = useCallback((conversationId: string) => {
    return executions.has(conversationId);
  }, [executions]);

  const executingConversations = new Set(executions.keys());

  return (
    <BackgroundExecutionContext.Provider
      value={{
        executingConversations,
        startExecution,
        stopExecution,
        isExecuting,
      }}
    >
      {children}
    </BackgroundExecutionContext.Provider>
  );
};

export const useBackgroundExecution = () => {
  const context = useContext(BackgroundExecutionContext);
  if (!context) {
    throw new Error('useBackgroundExecution must be used within BackgroundExecutionProvider');
  }
  return context;
};


