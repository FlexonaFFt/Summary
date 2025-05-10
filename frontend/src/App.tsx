import { useState, useEffect, useRef } from 'react'
import { setupTextareaAutosize } from './utils/textareaAutoResize'
import TypewriterText from './components/TypewriterText'
import { askQuestionToFile } from './utils/api'
import './styles/index.css'

const pollStatus = async (requestId: string, maxAttempts = 30, interval = 1000) => {
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    try {
      const response = await fetch(`http://localhost:8000/status/${requestId}`, {
        method: 'GET'
      });
      
      if (!response.ok) {
        throw new Error(`Ошибка HTTP: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'done') {
        return result;
      }
      
      if (result.status === 'not_found') {
        return { error: 'Запрос не найден' };
      }
      
      // Ждем перед следующей попыткой
      await new Promise(resolve => setTimeout(resolve, interval));
      attempts++;
    } catch (error) {
      console.error('Ошибка при проверке статуса:', error);
      return { error: 'Произошла ошибка при проверке статуса' };
    }
  }
  
  return { error: 'Превышено время ожидания ответа' };
};

type MessageType = 'user' | 'model' | 'file';
type ActionType = 'continue' | 'question' | null;
type ThemeType = 'light' | 'dark';

interface Message {
  type: MessageType;
  text: string;
  fileInfo?: {
    name: string;
    size: number;
    type: string;
  };
}

function App() {
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [activeFile, setActiveFile] = useState<File | null>(null)
  const [activeAction, setActiveAction] = useState<ActionType>(null)
  const [messagesAfterAction, setMessagesAfterAction] = useState<Message[]>([])
  const [theme, setTheme] = useState<ThemeType>(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      return savedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const initTextareaResize = useRef<() => void>()

  useEffect(() => {
    initTextareaResize.current = setupTextareaAutosize();
  }, []);

  useEffect(() => {
    if (initTextareaResize.current) {
      initTextareaResize.current();
    }
  }, [inputText]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, messagesAfterAction, isTyping]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };
    
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange);
    }
    
    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputText.trim() || isLoading || isTyping) return
    const userMessage = inputText.trim();
    
    if (activeAction) {
      setMessagesAfterAction(prev => [...prev, { type: 'user', text: userMessage }]);
    } else {
      setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    }
    
    setInputText('');
    setIsLoading(true);
    
    try {
      if (activeAction === 'question' && activeFile) {
        // Используем новый API для вопросов к файлу
        const data = await askQuestionToFile(activeFile, userMessage);
        
        setIsLoading(false);
        setIsTyping(true);
        
        // Проверяем, нужно ли опрашивать статус
        if (data.request_id) {
          const result = await pollStatus(data.request_id);
          if (result.error) {
            throw new Error(result.error);
          }
          setMessagesAfterAction(prev => [...prev, { type: 'model', text: result.summary || 'Не удалось получить ответ' }]);
        } else {
          setMessagesAfterAction(prev => [...prev, { type: 'model', text: data.summary || 'Не удалось получить ответ' }]);
        }
      } else {
        // Для обычной суммаризации текста
        const response = await fetch('http://localhost:8000/summarize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: userMessage })
        });
        
        if (!response.ok) {
          throw new Error(`Ошибка HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Проверяем, нужно ли опрашивать статус
        if (data.request_id) {
          const result = await pollStatus(data.request_id);
          if (result.error) {
            throw new Error(result.error);
          }
          
          setIsLoading(false);
          setIsTyping(true);
          
          if (activeAction) {
            setMessagesAfterAction(prev => [...prev, { type: 'model', text: result.summary || 'Не удалось получить ответ' }]);
          } else {
            setMessages(prev => [...prev, { type: 'model', text: result.summary || 'Не удалось получить ответ' }]);
          }
        } else {
          setIsLoading(false);
          setIsTyping(true);
          
          if (activeAction) {
            setMessagesAfterAction(prev => [...prev, { type: 'model', text: data.summary || 'Не удалось получить ответ' }]);
          } else {
            setMessages(prev => [...prev, { type: 'model', text: data.summary || 'Не удалось получить ответ' }]);
          }
        }
      }
    } catch (error) {
      console.error('Ошибка при получении ответа:', error);
      setIsTyping(true);
      
      const errorMessage = { 
        type: 'model' as MessageType, 
        text: 'Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова.' 
      };
      
      if (activeAction) {
        setMessagesAfterAction(prev => [...prev, errorMessage]);
      } else {
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
  
    setActiveAction(null);
    setMessagesAfterAction([]);
    setActiveFile(file);
    setMessages(prev => [...prev, { 
      type: 'file', 
      text: `Вами был загружен файл ${file.name} для суммаризации`,
      fileInfo: {
        name: file.name,
        size: file.size,
        type: file.type
      }
    }]);
  
    handleFileSubmit(file);
  }

  const handleFileSubmit = async (file: File) => {
    setIsLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('http://localhost:8000/summarize-file', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Ошибка HTTP: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Проверяем, нужно ли опрашивать статус
      if (data.request_id) {
        const result = await pollStatus(data.request_id);
        if (result.error) {
          throw new Error(result.error);
        }
        setIsLoading(false);
        setIsTyping(true);
        setMessages(prev => [...prev, { type: 'model', text: result.summary || 'Не удалось получить ответ' }]);
      } else {
        setIsLoading(false);
        setIsTyping(true);
        setMessages(prev => [...prev, { type: 'model', text: data.summary || 'Не удалось получить ответ' }]);
      }
    } catch (error) {
      console.error('Ошибка при обработке файла:', error);
      setIsTyping(true);
      setMessages(prev => [...prev, { 
        type: 'model', 
        text: 'Произошла ошибка при обработке файла. Пожалуйста, попробуйте снова.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  }
  
  const handleContinueSummarization = () => {
    if (!activeFile) return;
    
    setActiveAction('continue');
    setIsLoading(true);
    
    const fetchContinueSummary = async () => {
      try {
        const formData = new FormData();
        formData.append('file', activeFile);
        // Поскольку в бэкенде нет специального маршрута для продолжения суммаризации,
        // используем тот же маршрут для суммаризации файла
        
        const response = await fetch('http://localhost:8000/summarize-file', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          throw new Error(`Ошибка HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Проверяем, нужно ли опрашивать статус
        if (data.request_id) {
          const result = await pollStatus(data.request_id);
          if (result.error) {
            throw new Error(result.error);
          }
          setIsLoading(false);
          setIsTyping(true);
          setMessagesAfterAction(prev => [...prev, { type: 'model', text: result.summary || 'Не удалось получить ответ' }]);
        } else {
          setIsLoading(false);
          setIsTyping(true);
          setMessagesAfterAction(prev => [...prev, { type: 'model', text: data.summary || 'Не удалось получить ответ' }]);
        }
      } catch (error) {
        console.error('Ошибка при продолжении суммаризации:', error);
        setIsTyping(true);
        setMessagesAfterAction(prev => [...prev, { 
          type: 'model', 
          text: 'Произошла ошибка при продолжении суммаризации. Пожалуйста, попробуйте снова.' 
        }]);
        setIsLoading(false);
      }
    };
    
    fetchContinueSummary();
  }

  const handleAskQuestion = () => {
    if (!activeFile) return;
    
    setActiveAction('question');
    setMessagesAfterAction([]);
    setMessages(prev => [...prev, { 
      type: 'model', 
      text: 'Задайте вопрос по содержимому файла, и я постараюсь на него ответить.' 
    }]);

    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.placeholder = `Задайте вопрос по файлу "${activeFile.name}"...`;
      textareaRef.current.focus();
    }
  }
  
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };
  
  const toggleTheme = () => {
    setTheme(prev => {
      const newTheme = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', newTheme);
      return newTheme;
    });
  };
  
  return (
    <div className={`app-container ${theme}`}>
      {/* Хедер с минималистичными кнопками */}
      <header className="app-header minimal-header">
        <button className="header-button theme-toggle" onClick={toggleTheme} aria-label="Переключить тему">
          {theme === 'light' ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </button>
      </header>
      
      <div className="logo-container">
        <div className="logo">
          <div className="logo-top"></div>
          <div className="logo-bottom"></div>
        </div>
      </div>
      
      <div className="chat-container" ref={chatContainerRef}>
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>Суммаризатор текста</h1>
            <p>Введите текст для суммаризации или загрузите файл</p>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}-message`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : message.type === 'file' ? '📄' : '🤖'}
                </div>
                <div className="message-content">
                  {message.type === 'model' && index === messages.length - 1 && isTyping && !activeAction ? (
                    <TypewriterText 
                      text={message.text} 
                      speed={20} 
                      onComplete={() => setIsTyping(false)} 
                    />
                  ) : (
                    message.text
                  )}
                </div>
              </div>
            ))}
            
            {messages.length > 0 && 
             messages[messages.length - 1].type === 'model' && 
             !isTyping && 
             activeFile && 
             !activeAction && (
              <div className="model-actions">
                <button 
                  className="action-button"
                  onClick={handleContinueSummarization}
                >
                  Продолжить суммаризацию
                </button>
                <button 
                  className="action-button"
                  onClick={handleAskQuestion}
                >
                  Задать вопрос по файлу
                </button>
              </div>
            )}
            
            {activeAction && (
              <div className="action-divider">
                <div className="divider-line"></div>
                <div className="divider-text">
                  {activeAction === 'continue' ? 'Продолжение суммаризации' : 'Вопрос по файлу'}
                </div>
                <div className="divider-line"></div>
              </div>
            )}
            
            {messagesAfterAction.map((message, index) => (
              <div key={`after-${index}`} className={`message ${message.type}-message`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : message.type === 'file' ? '📄' : '🤖'}
                </div>
                <div className="message-content">
                  {message.type === 'model' && index === messagesAfterAction.length - 1 && isTyping ? (
                    <TypewriterText 
                      text={message.text} 
                      speed={20} 
                      onComplete={() => setIsTyping(false)} 
                    />
                  ) : (
                    message.text
                  )}
                </div>
              </div>
            ))}
          </>
        )}
        {isLoading && (
          <div className="message model-message">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="input-wrapper">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Введите текст для суммаризации..."
            className="modern-input"
            rows={1}
            disabled={isLoading || isTyping}
          />
          <div className="input-actions">
            <label className="file-upload-label">
              <input 
                type="file" 
                accept=".txt,.doc,.docx,.pdf" 
                onChange={handleFileUpload}
                className="file-input"
                disabled={isLoading || isTyping}
              />
              <svg className="attachment-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21.44 11.05l-9.19 9.19a6.003 6.003 0 01-8.49-8.49l9.19-9.19a4.002 4.002 0 015.66 5.66l-9.2 9.19a2.001 2.001 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </label>
            <button 
              type="submit" 
              className="send-button"
              disabled={isLoading || !inputText.trim() || isTyping}
            >
              {isLoading ? (
                <div className="loading-spinner"></div>
              ) : (
                <span className="send-icon-text">➤</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Вспомогательные функции
function getFileIcon(fileType: string): string {
  if (fileType.includes('pdf')) return 'PDF';
  if (fileType.includes('word') || fileType.includes('docx')) return 'DOC';
  if (fileType.includes('text')) return 'TXT';
  return 'FILE';
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default App
