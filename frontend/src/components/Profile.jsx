import React, { useState, useEffect, useRef } from 'react';
import { Upload, Trash2, Loader2, FileText, User } from 'lucide-react';

import { supabase } from '../supabaseClient';
import Modal from './Modal';

export default function Profile({ session }) {
  const [modalState, setModalState] = useState({ isOpen: false, title: '', message: '', type: 'info', onConfirm: null, confirmText: 'Confirm' });

  const showAlert = (title, message, type = 'info') => {
    setModalState({ isOpen: true, title, message, type, onConfirm: null, confirmText: 'Confirm' });
  };
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [profile, setProfile] = useState({ display_name: '', age: '', gender: '', major: '' });
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const fileInputRef = useRef(null);
  const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

  const fetchDocuments = async () => {
    const userId = session?.user?.id;
    if (!userId) return;
    setIsFetching(true);
    try {
      const response = await fetch(`${API_URL}/api/documents/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setIsFetching(false);
    }
  };

  const fetchProfile = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const { data } = await supabase.from('profiles').select('*').eq('id', user.id).single();
      if (data) setProfile({ display_name: data.display_name || '', age: data.age || '', gender: data.gender || '', major: data.major || '' });
    }
  };

  useEffect(() => {
    if (session?.user?.id) {
      fetchDocuments();
      fetchProfile();
    }
  }, [session]);

  const saveProfile = async () => {
    setIsSavingProfile(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      await supabase.from('profiles').upsert({ id: user.id, ...profile, updated_at: new Date() });
      showAlert("Success", "Profile saved successfully!", "success");
    } catch (error) {
      console.error("Error saving profile:", error);
      showAlert("Error", "Failed to save profile.", "error");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showAlert('Invalid File', 'Only PDF files are allowed.', 'error');
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', session.user.id);

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = 'Failed to upload document';
        try {
          const errorData = await response.json();
          if (errorData.detail) errorMsg = errorData.detail;
          if (errorData.message) errorMsg = errorData.message;
        } catch (e) {
          console.error('Upload error (non-JSON):', response.statusText);
        }
        throw new Error(errorMsg);
      }

      await fetchDocuments(); // Even if this fails, the finally block will run
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      showAlert('Upload Failed', error.response?.data?.message || error.message || "Something went wrong. Please check the console.", 'error');
    } finally {
      setIsUploading(false); // THIS STOPS THE SPINNER PERMANENTLY
    }
  };

  const handleDelete = async (filename) => {
    const userId = session?.user?.id;
    if (!userId) return;

    setModalState({
      isOpen: true,
      title: 'Confirm Deletion',
      message: `Are you sure you want to delete ${filename}?`,
      type: 'confirm',
      confirmText: 'Delete',
      onConfirm: async () => {
        try {
          const response = await fetch(`${API_URL}/documents/${userId}/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
          });
          if (!response.ok) throw new Error('Failed to delete document');
          await fetchDocuments();
        } catch (error) {
          console.error('Error deleting document:', error);
          showAlert('Deletion Failed', 'Failed to delete document. Please try again.', 'error');
        }
      }
    });
  };

  return (
    <div className="flex-1 overflow-y-auto w-full p-6 sm:p-10 bg-transparent">
      <Modal 
        {...modalState} 
        onClose={() => setModalState(prev => ({ ...prev, isOpen: false }))} 
      />
      <div className="max-w-3xl mx-auto space-y-8">

        {/* User Info Section */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-emerald-500" />
            User Profile
          </h2>
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-4 text-gray-600">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 font-bold text-lg">
                {profile.display_name ? profile.display_name.charAt(0).toUpperCase() : (session?.user?.email?.charAt(0).toUpperCase() || 'U')}
              </div>
              <div>
                <p className="text-sm text-gray-500">Email Address</p>
                <p className="font-medium text-gray-800">{session?.user?.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-500 mb-1">Display Name</label>
                <input
                  type="text"
                  value={profile.display_name}
                  onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                  placeholder="Enter your name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Age</label>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => setProfile({ ...profile, age: e.target.value })}
                  placeholder="Enter your age"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Gender</label>
                <select
                  value={profile.gender}
                  onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all bg-white"
                >
                  <option value="">Select gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-500 mb-1">Major</label>
                <input
                  type="text"
                  value={profile.major}
                  onChange={(e) => setProfile({ ...profile, major: e.target.value })}
                  placeholder="e.g. Computer Science"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                />
              </div>
            </div>

            <div className="flex justify-end mt-2">
              <button
                onClick={saveProfile}
                disabled={isSavingProfile}
                className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-emerald-400 flex items-center justify-center gap-2"
              >
                {isSavingProfile ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Save Profile
              </button>
            </div>
          </div>
        </section>

        {/* Document Management Section */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-500" />
              My Documents
            </h2>

            {/* Upload Button */}
            <div>
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                ref={fileInputRef}
                onChange={handleFileUpload}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-emerald-400 disabled:cursor-not-allowed shadow-sm"
              >
                {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {isUploading ? 'Uploading...' : 'Upload PDF'}
              </button>
            </div>
          </div>

          {/* Document List */}
          <div className="space-y-3">
            {isFetching ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-emerald-500 animate-spin" />
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                No documents uploaded yet.
              </div>
            ) : (
              documents.map((doc, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200 hover:border-emerald-200 transition-colors group">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-700 font-medium truncate">{doc.filename || doc}</span>
                    {doc.isUploading && (
                      <span className="flex items-center gap-1 text-xs text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <Loader2 className="w-3 h-3 animate-spin" /> Uploading...
                      </span>
                    )}
                  </div>
                  {!doc.isUploading && (
                    <button
                      onClick={() => handleDelete(doc.filename || doc)}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0 opacity-100"
                      title="Delete document"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </section>

      </div>
    </div>
  );
}
