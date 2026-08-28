import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Menu, X, BookOpen, GraduationCap, ChevronRight, MessageSquare, FileText, Check, Copy, LogOut } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import Auth from './components/Auth';
import Profile from './components/Profile';
import { supabase } from './supabaseClient';
export default function App() {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

  const fetchSessions = async (userId) => {
    try {
      const response = await fetch(`${API_URL}/sessions/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
    }
  };

  const loadSession = async (sessionId) => {
    setActiveSessionId(sessionId);
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionId}/messages`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
        if (window.innerWidth < 768) {
          setIsSidebarOpen(false);
        }
      }
    } catch (error) {
      console.error("Error fetching session messages:", error);
    }
  };

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session?.user) {
        fetchSessions(session.user.id);
      }
    });
    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session?.user) {
        fetchSessions(session.user.id);
      }
    });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const { data: { user }, error: authError } = await supabase.auth.getUser();

      if (authError || !user) {
        throw new Error('Authentication failed');
      }

      const userName = user?.user_metadata?.display_name || "Student";

      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          user_name: userName,
          user_id: user.id,
          session_id: activeSessionId,
          rag_mode: true
        }),
      });

      if (!response.ok) {
        let errorDetail = "";
        try {
            const errorObj = await response.json();
            errorDetail = errorObj.detail || errorObj.message || "Unknown error";
        } catch(e) {
            errorDetail = response.statusText;
        }
        throw new Error(`Failed to fetch response: ${response.status} - ${errorDetail}`);
      }

      const data = await response.json();

      const assistantMessage = {
        role: 'assistant',
        content: data.response || data.answer,
        sources: data.sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (!activeSessionId && data.session_id) {
        setActiveSessionId(data.session_id);
        fetchSessions(user.id);
      }
    } catch (error) {
      console.error('Error:', error);
      let errorMsg = error.message || 'Sorry, I encountered an error while trying to fetch the answer. Please try again later.';

      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        errorMsg = `Unable to connect to the backend server. Please ensure the backend is running at ${API_URL}.`;
      } else if (error.message.includes('Authentication failed')) {
        errorMsg = 'Your session may have expired. Please try signing out and signing back in.';
      }

      const errorMessage = {
        role: 'assistant',
        content: errorMsg,
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!session) {
    return <Auth />;
  }

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden font-sans">
      {/* Sidebar Overlay */}
      {!isSidebarOpen && (
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="md:hidden fixed z-50 top-4 left-4 p-2 bg-white rounded-md shadow-md border border-gray-200"
        >
          <Menu className="w-5 h-5 text-gray-600" />
        </button>
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:static z-40 inset-y-0 left-0 transform ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform duration-300 ease-in-out w-72 bg-white border-r border-gray-200 flex flex-col`}
      >
        <div className="p-4 flex items-center justify-between border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg tracking-tight text-gray-800">CollegeBuddy</span>
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-4 text-xs font-semibold text-gray-400 uppercase tracking-wider flex justify-between items-center">
            <span>Recent Chats</span>
            <button
              onClick={() => {
                setActiveSessionId(null);
                setMessages([]);
                if (window.innerWidth < 768) {
                  setIsSidebarOpen(false);
                }
              }}
              className="text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded-md transition-colors font-medium"
            >
              + New Chat
            </button>
          </div>
          <div className="space-y-2">
            {sessions.length > 0 ? (
              sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSession(s.id)}
                  className={`w-full text-left p-3 rounded-lg flex items-center gap-3 transition-colors border shadow-sm ${activeSessionId === s.id ? 'bg-indigo-50 text-indigo-700 border-indigo-100' : 'bg-white text-gray-700 border-gray-100 hover:bg-gray-50'}`}
                >
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate text-sm font-medium">{s.title || "New Session"}</span>
                </button>
              ))
            ) : (
              <div className="text-sm text-gray-400 italic px-2">No recent chats</div>
            )}
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 text-xs text-gray-400 flex items-center justify-center gap-1.5 bg-gray-50/50">
          Powered by Gemini 3.7 Flash & pgvector
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full bg-white md:bg-gray-50/50 relative">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-gray-200 bg-white/80 backdrop-blur-md shadow-sm z-10 md:pl-6 pl-16">
          <h1 className="font-semibold text-gray-800 tracking-tight md:hidden">CollegeBuddy</h1>
          <div className="hidden md:flex gap-1 bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'chat'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('profile')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'profile'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              Profile
            </button>
          </div>
          <button onClick={() => supabase.auth.signOut()} className="flex items-center gap-2 text-sm text-gray-600 hover:text-red-600 transition-colors">
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </header>

        {activeTab === 'profile' ? (
          <Profile session={session} />
        ) : (
          <>
            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto w-full scroll-smooth">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-700 zoom-in-95">
                  <div className="w-24 h-24 bg-gradient-to-tr from-indigo-100 to-purple-50 rounded-2xl flex items-center justify-center mb-8 shadow-sm border border-white">
                    <GraduationCap className="w-12 h-12 text-indigo-600" />
                  </div>
                  <h2 className="text-3xl md:text-4xl font-bold text-gray-800 mb-4 tracking-tight">Welcome to CollegeBuddy</h2>
                  <p className="text-gray-500 max-w-md text-lg leading-relaxed mb-10">
                    Hello! I am CollegeBuddy, your intelligent student ecosystem. Upload your lecture PDFs, PYQs, or college brochures in the Profile section, and let's start studying!
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                    {[
                      "What are the admission requirements for computer science?",
                      "Tell me about the library hours.",
                      "How do I apply for financial aid?",
                      "What sports facilities are available on campus?"
                    ].map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => setInput(suggestion)}
                        className="p-4 text-left border border-gray-200 bg-white rounded-xl hover:border-indigo-300 hover:bg-indigo-50/50 hover:shadow-md transition-all duration-200 text-sm text-gray-700 font-medium flex items-center justify-between group"
                      >
                        <span className="line-clamp-2 pr-4">{suggestion}</span>
                        <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-indigo-500 flex-shrink-0 transition-colors" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="max-w-4xl mx-auto w-full py-8 px-4 sm:px-6">
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 sm:gap-4 mb-8 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-300`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex-shrink-0 flex items-center justify-center shadow-md">
                          <Bot className="w-5 h-5 text-white" />
                        </div>
                      )}

                      <div className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 sm:p-5 shadow-sm ${msg.role === 'user'
                        ? 'bg-indigo-600 text-white rounded-br-none'
                        : msg.isError
                          ? 'bg-red-50 border border-red-200 text-red-800 rounded-bl-none'
                          : 'bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm'
                        }`}>
                        {msg.role === 'user' ? (
                          <div className="prose prose-sm sm:prose-base max-w-none prose-p:leading-relaxed text-white">
                            {msg.content.split('\n').map((line, i) => (
                              <p key={i} className="mb-2 last:mb-0 min-h-[1rem]">{line}</p>
                            ))}
                          </div>
                        ) : (
                          <div className={`prose prose-sm sm:prose-base max-w-none ${msg.isError ? 'text-red-800' : 'text-gray-800'}`}>
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </div>
                        )}

                        {msg.sources && msg.sources.length > 0 && !msg.content.includes("I do not have that specific information") && (
                          <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-gray-100">
                            <div className="flex items-center gap-1 text-xs text-gray-400 uppercase font-semibold mr-1">
                              <BookOpen size={12} /> Sources:
                            </div>
                            {[...new Map(msg.sources.map(s => [`${s.document}-${s.page}`, s])).values()].map((source, idx) => (
                              <a key={idx} href="#" className="inline-flex items-center gap-1 text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-1 rounded-md hover:bg-blue-100 transition-colors">
                                <FileText size={12} />
                                {source.document} (Pg. {source.page})
                              </a>
                            ))}
                          </div>
                        )}
                      </div>

                      {msg.role === 'user' && (
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center shadow-inner border border-gray-300">
                          <User className="w-5 h-5 text-gray-500" />
                        </div>
                      )}
                    </div>
                  ))}

                  {isLoading && (
                    <div className="flex gap-3 sm:gap-4 mb-8 justify-start animate-in fade-in">
                      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-400 flex-shrink-0 flex items-center justify-center shadow-sm">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none p-5 shadow-sm flex items-center h-[52px]">
                        <div className="flex space-x-1.5">
                          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} className="h-4" />
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="p-3 sm:p-4 bg-white/90 backdrop-blur-xl border-t border-gray-200 shadow-sm relative z-20">
              <div className="max-w-4xl mx-auto">
                <form
                  onSubmit={handleSubmit}
                  className="relative flex items-end bg-white rounded-2xl border border-gray-300 shadow-sm focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500 transition-all overflow-hidden"
                >
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit(e);
                      }
                    }}
                    placeholder="Ask about college policies, courses, or facilities..."
                    className="w-full max-h-32 min-h-[56px] py-4 pl-4 pr-14 bg-transparent border-0 focus:ring-0 resize-none outline-none text-gray-800 placeholder-gray-400 text-base"
                    rows="1"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className="absolute right-2 bottom-2 p-2 sm:p-2.5 rounded-xl bg-indigo-600 text-white disabled:bg-gray-100 disabled:text-gray-300 hover:bg-indigo-700 transition-all shadow-sm disabled:shadow-none transform active:scale-95 disabled:active:scale-100"
                  >
                    {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 ml-0.5" />}
                  </button>
                </form>
                <div className="mt-2 text-center text-[11px] text-gray-400 font-medium">
                  CollegeBuddy can make mistakes. Consider verifying important information with official sources.
                </div>
              </div>
            </div>
          </>
        )}
      </div>


    </div>
  );
}
