import React from 'react';
import { CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, message, type = 'info', onConfirm, confirmText = 'Confirm' }) {
  if (!isOpen) return null;

  const isError = type === 'error';
  const isConfirm = type === 'confirm';
  const isSuccess = type === 'success';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="p-6">
          <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 rounded-full bg-emerald-50">
            {isSuccess && <CheckCircle className="w-6 h-6 text-emerald-500" />}
            {isError && <AlertCircle className="w-6 h-6 text-red-500" />}
            {isConfirm && <HelpCircle className="w-6 h-6 text-yellow-500" />}
            {type === 'info' && <AlertCircle className="w-6 h-6 text-emerald-500" />}
          </div>
          
          <h3 className="mb-2 text-lg font-semibold text-center text-gray-900">{title}</h3>
          <p className="text-sm text-center text-gray-500">{message}</p>
          
          <div className="flex gap-3 mt-6">
            {isConfirm ? (
              <>
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    onConfirm();
                    onClose();
                  }}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors"
                >
                  {confirmText}
                </button>
              </>
            ) : (
              <button
                onClick={onClose}
                className={`w-full px-4 py-2 text-sm font-medium text-white rounded-xl transition-colors ${
                  isError ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                Okay
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
