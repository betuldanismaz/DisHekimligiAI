/**
 * API Client Configuration
 * ========================
 * Axios instance configured for FastAPI backend communication.
 * Automatically handles JWT token attachment and error responses.
 */

import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// API base URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

console.log('🔌 API_URL Configured as:', API_URL); // Debug log

// Create axios instance
const apiClient: AxiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds
});

// Request interceptor - Automatically attach JWT token
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // Get token from localStorage
        const token = localStorage.getItem('access_token');

        if (token && config.headers) {
            // Attach Bearer token to Authorization header
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response) {
            // Server responded with error status
            const status = error.response.status;

            if (status === 401) {
                // Unauthorized - clear token and redirect to login
                localStorage.removeItem('access_token');
                localStorage.removeItem('student_id');
                localStorage.removeItem('name');

                // Only redirect if not already on login page
                if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
                    window.location.href = '/login';
                }
            }
        }

        return Promise.reject(error);
    }
);

// ==================== API FUNCTIONS ====================

/**
 * Authentication API
 */
export const authAPI = {
    /**
     * Register a new student account
     */
    register: async (data: {
        student_id: string;
        name: string;
        password: string;
        email?: string;
    }) => {
        const response = await apiClient.post('/api/auth/register', data);
        return response.data;
    },

    /**
     * Login with student credentials
     */
    login: async (student_id: string, password: string) => {
        const response = await apiClient.post('/api/auth/login', {
            student_id,
            password,
        });
        return response.data; // { access_token, token_type, student_id, name }
    },

    /**
     * Get current user information
     */
    getCurrentUser: async () => {
        const response = await apiClient.get('/api/auth/me');
        return response.data;
    },
};

/**
 * Chat API
 */
export const chatAPI = {
    /**
     * Send a chat message (requires authentication)
     */
    sendMessage: async (message: string, case_id: string) => {
        const response = await apiClient.post('/api/chat/send', {
            message,
            case_id,
        });
        return response.data;
    },

    /**
     * Get chat history for a session
     */
    getHistory: async (student_id: string, case_id: string) => {
        const response = await apiClient.get(`/api/chat/history/${student_id}/${case_id}`);
        return response.data;
    },
};

export default apiClient;
