import { useState, useEffect, useRef } from 'react'
import { setupTextareaAutosize } from './utils/textareaAutoResize'
import TypewriterText from './components/TypewriterText'
import HomePage from './components/HomePage'
import './styles/index.css'

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
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [theme, setTheme] = useState<ThemeType>('light')
  const [showHomePage, setShowHomePage] = useState(true)
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
        setTimeout(() => {
          const modelResponse = `Ответ на ваш вопрос "${userMessage}" по файлу "${activeFile.name}": ...`;
          setIsLoading(false);
          setIsTyping(true);
          setMessagesAfterAction(prev => [...prev, { type: 'model', text: modelResponse }]);
        }, 1500);
      } else {
        setTimeout(() => {
          const modelResponse = `Это пример суммаризации текста: "${userMessage.substring(0, 50)}..."`;
          setIsLoading(false);
          setIsTyping(true);
          
          if (activeAction) {
            setMessagesAfterAction(prev => [...prev, { type: 'model', text: modelResponse }]);
          } else {
            setMessages(prev => [...prev, { type: 'model', text: modelResponse }]);
          }
        }, 1000);
      }
      
      // Реальный запрос будет выглядеть примерно так:
      // const response = await fetch('ваш_api_endpoint', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ 
      //     text: userMessage,
      //     fileId: activeFile?.name,
      //     actionType: activeAction
      //   })
      // });
      // const data = await response.json();
      // setIsTyping(true);
      // setMessages(prev => [...prev, { type: 'model', text: data.summary }]);
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
      setTimeout(() => {
        const modelResponse = `Это пример суммаризации файла "${file.name}". Документ содержит информацию о...`;
        setIsLoading(false);
        setIsTyping(true);
        setMessages(prev => [...prev, { type: 'model', text: modelResponse }]);
      }, 1500);
      
      // Реальный запрос будет выглядеть примерно так:
      // const formData = new FormData();
      // formData.append('file', file);
      // const response = await fetch('ваш_api_endpoint/upload', {
      //   method: 'POST',
      //   body: formData
      // });
      // const data = await response.json();
      // setIsTyping(true);
      // setMessages(prev => [...prev, { type: 'model', text: data.summary }]);
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
    
    setTimeout(() => {
      const modelResponse = `Продолжение суммаризации файла "${activeFile.name}". Дополнительно можно отметить, что...`;
      setIsLoading(false);
      setIsTyping(true);
      setMessagesAfterAction(prev => [...prev, { type: 'model', text: modelResponse }]);
    }, 1500);
  }

  const handleAskQuestion = () => {
    if (!activeFile) return;
    
    setActiveAction('question');
    
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
  
  // Функция для переключения меню
  const toggleMenu = () => {
    setIsMenuOpen(prev => !prev);
  };
  
  // Функция для переключения темы
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };
  
  // Применяем тему к документу
  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
  }, [theme]);
  
  // Функция для переключения между главной страницей и приложением
  const handleStartApp = () => {
    setShowHomePage(false);
  };

  return (
    <>
      {showHomePage ? (
        <HomePage onStart={handleStartApp} />
      ) : (
        <div className="app-container" data-theme={theme}>
          {/* Здесь весь остальной контент приложения */}
          {/* ... */}
        </div>
      )}
    </>
  );
}

export default App;
