import { useEffect, useState } from "react";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
    // ============================================================
    // AUTH
    // ============================================================

    const [token, setToken] = useState(
        localStorage.getItem("token") || ""
    );

    const [user, setUser] = useState(null);

    const [authMode, setAuthMode] = useState("login");

    const [authForm, setAuthForm] = useState({
        name: "",
        email: "",
        password: "",
    });

    const [authLoading, setAuthLoading] = useState(false);
    const [authError, setAuthError] = useState("");
    const [loading, setLoading] = useState(true);

    // ============================================================
    // CHAT
    // ============================================================

    const [messages, setMessages] = useState([
        {
            role: "assistant",
            content:
                "Hello! I'm your personal AI assistant. How can I help you today?",
        },
    ]);

    const [messageInput, setMessageInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [conversationId, setConversationId] = useState(null);

    // ============================================================
    // MEMORY
    // ============================================================

    const [memories, setMemories] = useState([]);
    const [memoryLoading, setMemoryLoading] = useState(false);
    const [selectedMemoryId, setSelectedMemoryId] = useState("");
    const [showMemoryForm, setShowMemoryForm] = useState(false);

    const [memoryKey, setMemoryKey] = useState("");
    const [memoryValue, setMemoryValue] = useState("");
    const [memorySaving, setMemorySaving] = useState(false);

    const [editingMemoryId, setEditingMemoryId] = useState(null);
    const [editMemoryKey, setEditMemoryKey] = useState("");
    const [editMemoryValue, setEditMemoryValue] = useState("");
    const [memoryUpdating, setMemoryUpdating] = useState(false);

    // ============================================================
    // GMAIL
    // ============================================================

    const [pendingEmail, setPendingEmail] = useState(null);
    const [emailActionLoading, setEmailActionLoading] = useState(false);
    const [emailActionMessage, setEmailActionMessage] = useState("");

    // ============================================================
    // CALENDAR
    // ============================================================

    const [calendarEvents, setCalendarEvents] = useState([]);
    const [calendarLoading, setCalendarLoading] = useState(false);
    const [calendarError, setCalendarError] = useState("");
    const [selectedCalendarEvent, setSelectedCalendarEvent] =
        useState(null);

    const [meetingReminder, setMeetingReminder] = useState(null);

    const [remindedEventIds, setRemindedEventIds] = useState(() => {
        try {
            return JSON.parse(
                localStorage.getItem("remindedCalendarEvents") || "[]"
            );
        } catch {
            return [];
        }
    });

    // ============================================================
    // USER MEETING CHAT
    // ============================================================

    /*
     * IMPORTANT:
     *
     * The User-side meeting assistant now uses the same
     * backend AI /chat endpoint.
     *
     * Gemini is responsible for:
     *
     * - understanding meeting intent
     * - understanding dates/times
     * - checking availability through tools
     * - asking for confirmation
     * - creating the pending meeting request
     *
     * There is NO frontend meeting parser anymore.
     */

    const [meetingConversationId, setMeetingConversationId] =
        useState(null);

    const [meetingChatMessages, setMeetingChatMessages] = useState([
        {
            role: "assistant",
            content:
                "Hi! I can help you schedule a meeting with Admin. Tell me when you would like to meet.",
        },
    ]);

    const [meetingChatInput, setMeetingChatInput] = useState("");
    const [meetingChatLoading, setMeetingChatLoading] = useState(false);

    // ============================================================
    // USER MEETINGS
    // ============================================================

    const [myMeetings, setMyMeetings] = useState([]);
    const [myMeetingsLoading, setMyMeetingsLoading] = useState(false);
    const [myMeetingsError, setMyMeetingsError] = useState("");

    // ============================================================
    // ADMIN MEETING REQUESTS
    // ============================================================

    const [meetingRequests, setMeetingRequests] = useState([]);
    const [meetingRequestsLoading, setMeetingRequestsLoading] =
        useState(false);
    const [meetingRequestsError, setMeetingRequestsError] = useState("");
    const [meetingActionLoading, setMeetingActionLoading] = useState(null);
    const [meetingActionMessage, setMeetingActionMessage] = useState("");

    // ============================================================
    // FETCH CURRENT USER
    // ============================================================

    const fetchCurrentUser = async (authToken) => {
        try {
            const response = await fetch(
                `${API_URL}/auth/me`,
                {
                    headers: {
                        Authorization: `Bearer ${authToken}`,
                    },
                }
            );

            if (!response.ok) {
                throw new Error("Session expired");
            }

            const data = await response.json();

            setUser(data);

            await fetchMemories(authToken);

            if (data.role === "admin") {
                await fetchCalendarEvents(authToken);
                await fetchMeetingRequests(authToken);
            } else {
                await fetchMyMeetings(authToken);
            }

            setLoading(false);
        } catch (error) {
            console.error("Session error:", error);

            localStorage.removeItem("token");

            setToken("");
            setUser(null);
            setLoading(false);
        }
    };

    // ============================================================
    // FETCH CALENDAR EVENTS
    // ============================================================

    const fetchCalendarEvents = async (authToken) => {
        if (!authToken) {
            return;
        }

        setCalendarLoading(true);
        setCalendarError("");

        try {
            const response = await fetch(
                `${API_URL}/calendar/events?max_results=50`,
                {
                    method: "GET",
                    headers: {
                        Authorization: `Bearer ${authToken}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to fetch calendar events"
                );
            }

            const updatedEvents = data.events || [];

            setCalendarEvents(updatedEvents);

            if (
                selectedCalendarEvent &&
                !updatedEvents.some(
                    (event) =>
                        event.id === selectedCalendarEvent.id
                )
            ) {
                setSelectedCalendarEvent(null);
            }
        } catch (error) {
            console.error(
                "Calendar fetch error:",
                error
            );

            setCalendarError(
                error.message ||
                    "Failed to load calendar events."
            );
        } finally {
            setCalendarLoading(false);
        }
    };

    // ============================================================
    // FETCH USER'S OWN MEETINGS
    // ============================================================

    const fetchMyMeetings = async (authToken) => {
        if (!authToken) {
            return;
        }

        setMyMeetingsLoading(true);
        setMyMeetingsError("");

        try {
            const response = await fetch(
                `${API_URL}/meeting/my-requests`,
                {
                    headers: {
                        Authorization: `Bearer ${authToken}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Unable to load your meetings."
                );
            }

            setMyMeetings(data.requests || []);
        } catch (error) {
            console.error(
                "My meetings fetch error:",
                error
            );

            setMyMeetingsError(
                error.message ||
                    "Unable to load your meetings."
            );
        } finally {
            setMyMeetingsLoading(false);
        }
    };

    // ============================================================
    // FETCH ADMIN MEETING REQUESTS
    // ============================================================

    const fetchMeetingRequests = async (authToken) => {
        if (!authToken) {
            return;
        }

        setMeetingRequestsLoading(true);
        setMeetingRequestsError("");

        try {
            const response = await fetch(
                `${API_URL}/meeting/admin-requests`,
                {
                    headers: {
                        Authorization: `Bearer ${authToken}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Unable to load meeting requests."
                );
            }

            setMeetingRequests(
                (data.requests || []).filter(
                    (request) => request.status === "pending"
                )
            );
        } catch (error) {
            console.error(
                "Meeting requests fetch error:",
                error
            );

            setMeetingRequestsError(
                error.message ||
                    "Unable to load meeting requests."
            );
        } finally {
            setMeetingRequestsLoading(false);
        }
    };

    // ============================================================
    // APPROVE MEETING REQUEST
    // ============================================================

    const approveMeetingRequest = async (requestId) => {
        setMeetingActionLoading(requestId);
        setMeetingActionMessage("");
        setMeetingRequestsError("");

        try {
            const response = await fetch(
                `${API_URL}/meeting/${requestId}/approve`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Unable to approve meeting request."
                );
            }

            setMeetingActionMessage(
                data.message ||
                    "Meeting request approved successfully."
            );

            await fetchMeetingRequests(token);
            await fetchCalendarEvents(token);
        } catch (error) {
            console.error(
                "Approve meeting error:",
                error
            );

            setMeetingRequestsError(
                error.message ||
                    "Unable to approve meeting request."
            );
        } finally {
            setMeetingActionLoading(null);
        }
    };

    // ============================================================
    // REJECT MEETING REQUEST
    // ============================================================

    const rejectMeetingRequest = async (requestId) => {
        const confirmed = window.confirm(
            "Are you sure you want to reject this meeting request?"
        );

        if (!confirmed) {
            return;
        }

        setMeetingActionLoading(requestId);
        setMeetingActionMessage("");
        setMeetingRequestsError("");

        try {
            const response = await fetch(
                `${API_URL}/meeting/${requestId}/reject`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        message:
                            "Meeting request rejected by Admin.",
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Unable to reject meeting request."
                );
            }

            setMeetingActionMessage(
                data.message ||
                    "Meeting request rejected successfully."
            );

            await fetchMeetingRequests(token);
        } catch (error) {
            console.error(
                "Reject meeting error:",
                error
            );

            setMeetingRequestsError(
                error.message ||
                    "Unable to reject meeting request."
            );
        } finally {
            setMeetingActionLoading(null);
        }
    };

    // ============================================================
    // USER MEETING CHAT
    // ============================================================

    const addMeetingChatMessage = (role, content) => {
        setMeetingChatMessages((previous) => [
            ...previous,
            {
                role,
                content,
            },
        ]);
    };

    /*
     * Dynamic AI meeting chat.
     *
     * IMPORTANT:
     *
     * Do not parse meeting dates/times here.
     *
     * The backend Gemini agent handles:
     *
     * "tomorrow"
     * "Monday"
     * "7 PM"
     * "tomorrow evening"
     * "for 1 hour"
     * "yes"
     *
     * and calls the appropriate meeting tools.
     */

    const sendMeetingChatMessage = async (text) => {
        const trimmedMessage = text.trim();

        if (
            !trimmedMessage ||
            meetingChatLoading
        ) {
            return;
        }

        addMeetingChatMessage(
            "user",
            trimmedMessage
        );

        setMeetingChatInput("");
        setMeetingChatLoading(true);

        try {
            const response = await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        message: trimmedMessage,
                        conversation_id:
                            meetingConversationId,
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to get AI response."
                );
            }

            /*
             * IMPORTANT:
             *
             * Keep the conversation ID.
             *
             * This allows:
             *
             * User:
             * "Can I meet Admin tomorrow?"
             *
             * AI:
             * "What time?"
             *
             * User:
             * "7 PM"
             *
             * AI:
             * "Admin is available..."
             *
             * User:
             * "Yes"
             *
             * The backend receives the same conversation.
             */

            if (data.conversation_id) {
                setMeetingConversationId(
                    data.conversation_id
                );
            }

            addMeetingChatMessage(
                "assistant",
                data.response ||
                    data.message ||
                    "I couldn't generate a response."
            );

            /*
             * Refresh My Meetings after every AI response.
             *
             * This means that when Gemini creates a pending
             * meeting request, the User dashboard updates.
             */

            await fetchMyMeetings(token);
        } catch (error) {
            console.error(
                "Meeting chat error:",
                error
            );

            addMeetingChatMessage(
                "assistant",
                error.message ||
                    "Sorry, something went wrong while processing your meeting request."
            );
        } finally {
            setMeetingChatLoading(false);
        }
    };

    const handleMeetingChatSubmit = async (event) => {
        event.preventDefault();

        await sendMeetingChatMessage(
            meetingChatInput
        );
    };

    const startNewMeetingChat = () => {
        setMeetingConversationId(null);

        setMeetingChatMessages([
            {
                role: "assistant",
                content:
                    "Hi! I can help you schedule a meeting with Admin. Tell me when you would like to meet.",
            },
        ]);

        setMeetingChatInput("");
    };

    // ============================================================
    // MEETING REMINDER - 30 MINUTES BEFORE
    // ============================================================

    useEffect(() => {
        if (
            !token ||
            !user ||
            user.role !== "admin" ||
            calendarEvents.length === 0
        ) {
            return;
        }

        const checkMeetingReminders = () => {
            const now = new Date();

            for (const event of calendarEvents) {
                const startDateTime =
                    event.start?.dateTime;

                if (!startDateTime) {
                    continue;
                }

                const eventStart =
                    new Date(startDateTime);

                if (
                    Number.isNaN(
                        eventStart.getTime()
                    )
                ) {
                    continue;
                }

                const differenceInMinutes =
                    (eventStart.getTime() -
                        now.getTime()) /
                    (1000 * 60);

                if (
                    differenceInMinutes >= 29.5 &&
                    differenceInMinutes <= 30.5 &&
                    !remindedEventIds.includes(
                        event.id
                    )
                ) {
                    setMeetingReminder(event);

                    const updatedRemindedIds = [
                        ...remindedEventIds,
                        event.id,
                    ];

                    setRemindedEventIds(
                        updatedRemindedIds
                    );

                    localStorage.setItem(
                        "remindedCalendarEvents",
                        JSON.stringify(
                            updatedRemindedIds
                        )
                    );

                    break;
                }
            }
        };

        checkMeetingReminders();

        const reminderInterval =
            setInterval(
                checkMeetingReminders,
                30000
            );

        return () => {
            clearInterval(
                reminderInterval
            );
        };
    }, [
        token,
        user,
        calendarEvents,
        remindedEventIds,
    ]);

    // ============================================================
    // INITIAL AUTH CHECK
    // ============================================================

    useEffect(() => {
        if (token) {
            fetchCurrentUser(token);
        } else {
            setLoading(false);
        }
    }, []);

    // ============================================================
    // LOGIN / REGISTER
    // ============================================================

    const handleAuthSubmit = async (event) => {
        event.preventDefault();

        setAuthLoading(true);
        setAuthError("");

        try {
            const endpoint =
                authMode === "login"
                    ? "/auth/login"
                    : "/auth/register";

            const body =
                authMode === "login"
                    ? {
                          email:
                              authForm.email,
                          password:
                              authForm.password,
                      }
                    : {
                          name:
                              authForm.name,
                          email:
                              authForm.email,
                          password:
                              authForm.password,
                      };

            const response = await fetch(
                `${API_URL}${endpoint}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                    },
                    body: JSON.stringify(body),
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Authentication failed"
                );
            }

            if (
                authMode ===
                "register"
            ) {
                setAuthMode("login");

                setAuthForm({
                    name: "",
                    email:
                        authForm.email,
                    password: "",
                });

                setAuthError(
                    "Registration successful. Please login."
                );

                return;
            }

            const receivedToken =
                data.access_token;

            if (!receivedToken) {
                throw new Error(
                    "Login succeeded but no access token was returned."
                );
            }

            localStorage.setItem(
                "token",
                receivedToken
            );

            setToken(receivedToken);

            await fetchCurrentUser(
                receivedToken
            );
        } catch (error) {
            console.error(
                "Auth error:",
                error
            );

            setAuthError(
                error.message ||
                    "Something went wrong"
            );
        } finally {
            setAuthLoading(false);
        }
    };

    // ============================================================
    // MEMORY - GET
    // ============================================================

    const fetchMemories = async (authToken) => {
        setMemoryLoading(true);

        try {
            const response = await fetch(
                `${API_URL}/memory/`,
                {
                    headers: {
                        Authorization: `Bearer ${authToken}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to load memories"
                );
            }

            const updatedMemories =
                data.memories || [];

            setMemories(
                updatedMemories
            );

            if (
                selectedMemoryId &&
                !updatedMemories.some(
                    (memory) =>
                        String(memory.id) ===
                        String(
                            selectedMemoryId
                        )
                )
            ) {
                setSelectedMemoryId("");
            }
        } catch (error) {
            console.error(
                "Memory loading error:",
                error
            );
        } finally {
            setMemoryLoading(false);
        }
    };

    // ============================================================
    // MEMORY - CREATE
    // ============================================================

    const saveMemory = async (event) => {
        event.preventDefault();

        if (
            !memoryKey.trim() ||
            !memoryValue.trim()
        ) {
            return;
        }

        setMemorySaving(true);

        try {
            const params =
                new URLSearchParams();

            params.append(
                "key",
                memoryKey.trim()
            );

            params.append(
                "value",
                memoryValue.trim()
            );

            const response = await fetch(
                `${API_URL}/memory/?${params.toString()}`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to save memory"
                );
            }

            await fetchMemories(token);

            setMemoryKey("");
            setMemoryValue("");
            setShowMemoryForm(false);
            setSelectedMemoryId("");
        } catch (error) {
            console.error(
                "Memory save error:",
                error
            );
        } finally {
            setMemorySaving(false);
        }
    };

    // ============================================================
    // MEMORY - EDIT
    // ============================================================

    const startEditMemory = (memory) => {
        setEditingMemoryId(
            memory.id
        );

        setEditMemoryKey(
            memory.key
        );

        setEditMemoryValue(
            memory.value
        );
    };

    const updateMemory = async (event) => {
        event.preventDefault();

        if (
            !editMemoryKey.trim() ||
            !editMemoryValue.trim()
        ) {
            return;
        }

        setMemoryUpdating(true);

        try {
            const params =
                new URLSearchParams();

            params.append(
                "key",
                editMemoryKey.trim()
            );

            params.append(
                "value",
                editMemoryValue.trim()
            );

            const response = await fetch(
                `${API_URL}/memory/?${params.toString()}`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to update memory"
                );
            }

            await fetchMemories(token);

            setEditingMemoryId(null);
            setEditMemoryKey("");
            setEditMemoryValue("");
            setSelectedMemoryId("");
        } catch (error) {
            console.error(
                "Memory update error:",
                error
            );
        } finally {
            setMemoryUpdating(false);
        }
    };

    // ============================================================
    // MEMORY - DELETE
    // ============================================================

    const deleteMemory = async (
        memoryId
    ) => {
        try {
            const response = await fetch(
                `${API_URL}/memory/${memoryId}`,
                {
                    method: "DELETE",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to delete memory"
                );
            }

            await fetchMemories(token);

            setSelectedMemoryId("");
        } catch (error) {
            console.error(
                "Memory delete error:",
                error
            );
        }
    };

    // ============================================================
    // GMAIL - CONFIRM
    // ============================================================

    const confirmEmailAction = async () => {
        if (
            !pendingEmail?.action_id
        ) {
            return;
        }

        setEmailActionLoading(true);
        setEmailActionMessage("");

        try {
            const response = await fetch(
                `${API_URL}/chat/confirm-email/${pendingEmail.action_id}`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to send email"
                );
            }

            setEmailActionMessage(
                data.message ||
                    "Email sent successfully."
            );

            setPendingEmail(null);
        } catch (error) {
            console.error(
                "Email confirmation error:",
                error
            );

            setEmailActionMessage(
                error.message ||
                    "Failed to send email."
            );
        } finally {
            setEmailActionLoading(false);
        }
    };

    // ============================================================
    // GMAIL - CANCEL
    // ============================================================

    const cancelEmailAction = async () => {
        if (
            !pendingEmail?.action_id
        ) {
            return;
        }

        setEmailActionLoading(true);
        setEmailActionMessage("");

        try {
            const response = await fetch(
                `${API_URL}/chat/cancel/${pendingEmail.action_id}`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to cancel email"
                );
            }

            setEmailActionMessage(
                data.message ||
                    "Email action cancelled."
            );

            setPendingEmail(null);
        } catch (error) {
            console.error(
                "Email cancellation error:",
                error
            );

            setEmailActionMessage(
                error.message ||
                    "Failed to cancel email."
            );
        } finally {
            setEmailActionLoading(false);
        }
    };

    // ============================================================
    // GMAIL - REWRITE
    // ============================================================

    const rewriteEmailDraft = async () => {
        if (!pendingEmail) {
            return;
        }

        const rewritePrompt =
            "Rewrite the prepared email draft to make it clearer, more professional, and natural. " +
            "Keep the same recipient and overall purpose. " +
            "Do not send the email.";

        setPendingEmail(null);

        await sendMessage(
            rewritePrompt
        );
    };

    // ============================================================
    // MAIN AI CHAT
    // ============================================================

    const sendMessage = async (text) => {
        const trimmedMessage =
            text.trim();

        if (
            !trimmedMessage ||
            chatLoading
        ) {
            return;
        }

        setMessages(
            (previousMessages) => [
                ...previousMessages,
                {
                    role: "user",
                    content:
                        trimmedMessage,
                },
            ]
        );

        setMessageInput("");
        setChatLoading(true);

        try {
            const response = await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        message:
                            trimmedMessage,
                        conversation_id:
                            conversationId,
                    }),
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to get AI response"
                );
            }

            if (
                data.conversation_id
            ) {
                setConversationId(
                    data.conversation_id
                );
            }

            if (
                user?.role ===
                "admin"
            ) {
                await fetchCalendarEvents(
                    token
                );
            } else {
                await fetchMyMeetings(
                    token
                );
            }

            if (data.pending_action) {
                setPendingEmail(
                    data.pending_action
                );

                setEmailActionMessage(
                    ""
                );
            }

            setMessages(
                (previousMessages) => [
                    ...previousMessages,
                    {
                        role: "assistant",
                        content:
                            data.response ||
                            data.message ||
                            "I couldn't generate a response.",
                    },
                ]
            );
        } catch (error) {
            console.error(
                "Chat error:",
                error
            );

            setMessages(
                (previousMessages) => [
                    ...previousMessages,
                    {
                        role: "assistant",
                        content:
                            error.message ||
                            "Sorry, something went wrong while processing your message.",
                    },
                ]
            );
        } finally {
            setChatLoading(false);
        }
    };

    const handleSubmit = async (
        event
    ) => {
        event.preventDefault();

        await sendMessage(
            messageInput
        );
    };

    // ============================================================
    // NEW CHAT
    // ============================================================

    const startNewChat = () => {
        setConversationId(null);

        setMessages([
            {
                role: "assistant",
                content:
                    "Hello! I'm your personal AI assistant. How can I help you today?",
            },
        ]);

        setMessageInput("");
    };

    // ============================================================
    // LOGOUT
    // ============================================================

    const handleLogout = () => {
        localStorage.removeItem(
            "token"
        );

        setToken("");
        setUser(null);

        setConversationId(null);

        setMessages([
            {
                role: "assistant",
                content:
                    "Hello! I'm your personal AI assistant. How can I help you today?",
            },
        ]);

        // Memory
        setMemories([]);
        setSelectedMemoryId("");

        // Calendar
        setCalendarEvents([]);
        setSelectedCalendarEvent(
            null
        );
        setCalendarError("");

        setMeetingReminder(null);

        // Gmail
        setPendingEmail(null);
        setEmailActionMessage("");

        // User meeting chat
        setMeetingConversationId(
            null
        );

        setMeetingChatMessages([
            {
                role: "assistant",
                content:
                    "Hi! I can help you schedule a meeting with Admin. Tell me when you would like to meet.",
            },
        ]);

        setMeetingChatInput("");
        setMeetingChatLoading(false);

        // User meetings
        setMyMeetings([]);
        setMyMeetingsError("");

        // Admin meetings
        setMeetingRequests([]);
        setMeetingRequestsError("");
        setMeetingActionLoading(null);
        setMeetingActionMessage("");
    };

    // ============================================================
    // LOADING
    // ============================================================

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="loading-spinner"></div>

                <p>
                    Loading your assistant...
                </p>
            </div>
        );
    }

    // ============================================================
    // AUTH SCREEN
    // ============================================================

    if (!token || !user) {
        return (
            <div className="auth-page">
                <div className="auth-card">
                    <div className="auth-logo">
                        ✦
                    </div>

                    <h1>
                        Personal AI Assistant
                    </h1>

                    <p className="auth-subtitle">
                        Your intelligent personal workspace
                    </p>

                    <form
                        onSubmit={
                            handleAuthSubmit
                        }
                        className="auth-form"
                    >
                        {authMode ===
                            "register" && (
                            <input
                                type="text"
                                placeholder="Name"
                                value={
                                    authForm.name
                                }
                                onChange={(
                                    event
                                ) =>
                                    setAuthForm({
                                        ...authForm,
                                        name: event
                                            .target
                                            .value,
                                    })
                                }
                                required
                            />
                        )}

                        <input
                            type="email"
                            placeholder="Email"
                            value={
                                authForm.email
                            }
                            onChange={(
                                event
                            ) =>
                                setAuthForm({
                                    ...authForm,
                                    email: event
                                        .target
                                        .value,
                                })
                            }
                            required
                        />

                        <input
                            type="password"
                            placeholder="Password"
                            value={
                                authForm.password
                            }
                            onChange={(
                                event
                            ) =>
                                setAuthForm({
                                    ...authForm,
                                    password:
                                        event
                                            .target
                                            .value,
                                })
                            }
                            required
                        />

                        {authError && (
                            <div className="auth-error">
                                {authError}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={
                                authLoading
                            }
                        >
                            {authLoading
                                ? "Please wait..."
                                : authMode ===
                                  "login"
                                ? "Login"
                                : "Create Account"}
                        </button>
                    </form>

                    <div className="auth-switch">
                        {authMode ===
                        "login" ? (
                            <>
                                Don't have an account?{" "}
                                <button
                                    type="button"
                                    onClick={() => {
                                        setAuthMode(
                                            "register"
                                        );

                                        setAuthError(
                                            ""
                                        );
                                    }}
                                >
                                    Register
                                </button>
                            </>
                        ) : (
                            <>
                                Already have an account?{" "}
                                <button
                                    type="button"
                                    onClick={() => {
                                        setAuthMode(
                                            "login"
                                        );

                                        setAuthError(
                                            ""
                                        );
                                    }}
                                >
                                    Login
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    // ============================================================
    // NORMAL USER MEETING DASHBOARD
    // ============================================================

    if (user?.role === "user") {
        return (
            <div className="user-dashboard">
                <header className="user-dashboard-header">
                    <div className="user-dashboard-brand">
                        {/*  */}

                        <div className="user-dashboard-title">
                            <h1>
                                Meet with Admin
                            </h1>

                            <p>
                                Your conversational meeting assistant
                            </p>
                        </div>
                    </div>

                    <div className="user-header-profile">
                        <div className="user-avatar">
                            {user.name
                                ?.charAt(0)
                                ?.toUpperCase()}
                        </div>

                        <div className="user-header-info">
                            <strong>
                                {user.name}
                            </strong>

                            <span>
                                {user.email}
                            </span>
                        </div>

                        <button
                            className="user-logout-button"
                            onClick={
                                handleLogout
                            }
                        >
                            Logout
                        </button>
                    </div>
                </header>

                <main className="user-dashboard-content">
                    {/* ================================================== */}
                    {/* DYNAMIC AI MEETING CHAT */}
                    {/* ================================================== */}

                    <section className="user-meeting-chat-card">
                        <div className="user-meeting-chat-header">
                            <div>
                                <span className="user-card-label">
                                    MEETING ASSISTANT
                                </span>

                                <h2>
                                    Schedule a Meeting
                                </h2>

                                <p>
                                    Tell me when you would like to meet Admin. I will check availability for you.
                                </p>
                            </div>

                            <div className="meeting-chat-status">
                                <span></span>
                            
                            </div>
                        </div>

                        <div className="user-meeting-chat-messages">
                            {meetingChatMessages.map(
                                (
                                    message,
                                    index
                                ) => (
                                    <div
                                        key={
                                            index
                                        }
                                        className={`meeting-chat-row ${
                                            message.role ===
                                            "user"
                                                ? "meeting-chat-user-row"
                                                : "meeting-chat-assistant-row"
                                        }`}
                                    >
                                        {message.role ===
                                            "assistant" && (
                                            <div className="meeting-chat-avatar">
                                                ✦
                                            </div>
                                        )}

                                        <div
                                            className={`meeting-chat-bubble ${
                                                message.role ===
                                                "user"
                                                    ? "meeting-chat-user-bubble"
                                                    : "meeting-chat-assistant-bubble"
                                            }`}
                                        >
                                            {message.content
                                                .split(
                                                    "\n"
                                                )
                                                .map(
                                                    (
                                                        line,
                                                        lineIndex
                                                    ) => (
                                                        <span
                                                            key={
                                                                lineIndex
                                                            }
                                                        >
                                                            {
                                                                line
                                                            }

                                                            {lineIndex <
                                                                message.content.split(
                                                                    "\n"
                                                                ).length -
                                                                    1 && (
                                                                <br />
                                                            )}
                                                        </span>
                                                    )
                                                )}
                                        </div>
                                    </div>
                                )
                            )}

                            {meetingChatLoading && (
                                <div className="meeting-chat-row meeting-chat-assistant-row">
                                    <div className="meeting-chat-avatar">
                                        ✦
                                    </div>

                                    <div className="meeting-chat-bubble meeting-chat-assistant-bubble">
                                        Thinking...
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* ================================================== */}
                        {/* AI SUGGESTIONS */}
                        {/* ================================================== */}

                        <div className="meeting-chat-suggestions">
                            <button
                                type="button"
                                onClick={() =>
                                    sendMeetingChatMessage(
                                        "Can I meet Admin tomorrow at 7 PM for 30 minutes?"
                                    )
                                }
                                disabled={
                                    meetingChatLoading
                                }
                            >
                                Tomorrow at 7 PM
                            </button>

                            <button
                                type="button"
                                onClick={() =>
                                    sendMeetingChatMessage(
                                        "Is Admin available tomorrow at 5 PM?"
                                    )
                                }
                                disabled={
                                    meetingChatLoading
                                }
                            >
                                Check availability
                            </button>

                            <button
                                type="button"
                                onClick={() =>
                                    sendMeetingChatMessage(
                                        "I need a meeting tomorrow at 3 PM for 1 hour."
                                    )
                                }
                                disabled={
                                    meetingChatLoading
                                }
                            >
                                1 hour meeting
                            </button>

                            <button
                                type="button"
                                onClick={
                                    startNewMeetingChat
                                }
                                disabled={
                                    meetingChatLoading
                                }
                            >
                                + New Meeting Chat
                            </button>
                        </div>

                        {/* ================================================== */}
                        {/* MEETING CHAT INPUT */}
                        {/* ================================================== */}

                        <form
                            className="user-meeting-chat-input-area"
                            onSubmit={
                                handleMeetingChatSubmit
                            }
                        >
                            <input
                                type="text"
                                placeholder="Tell me when you want to meet Admin..."
                                value={
                                    meetingChatInput
                                }
                                onChange={(
                                    event
                                ) =>
                                    setMeetingChatInput(
                                        event.target
                                            .value
                                    )
                                }
                                disabled={
                                    meetingChatLoading
                                }
                            />

                            <button
                                type="submit"
                                disabled={
                                    meetingChatLoading ||
                                    !meetingChatInput.trim()
                                }
                            >
                                →
                            </button>
                        </form>
                    </section>

                    {/* ================================================== */}
                    {/* MY MEETINGS */}
                    {/* ================================================== */}

                    <section className="my-meetings-card">
                        <div className="user-card-header">
                            <div>
                                <span className="user-card-label">
                                    YOUR BOOKINGS
                                </span>

                                <h2>
                                    My Meetings
                                </h2>

                                <p>
                                    Track your meeting requests with Admin.
                                </p>
                            </div>

                            <button
                                className="refresh-meetings-button"
                                onClick={() =>
                                    fetchMyMeetings(
                                        token
                                    )
                                }
                                disabled={
                                    myMeetingsLoading
                                }
                            >
                                {myMeetingsLoading
                                    ? "Refreshing..."
                                    : "Refresh"}
                            </button>
                        </div>

                        {myMeetingsLoading && (
                            <div className="meetings-empty">
                                Loading your meetings...
                            </div>
                        )}

                        {!myMeetingsLoading &&
                            myMeetingsError && (
                                <div className="meeting-error">
                                    {
                                        myMeetingsError
                                    }
                                </div>
                            )}

                        {!myMeetingsLoading &&
                            !myMeetingsError &&
                            myMeetings.length ===
                                0 && (
                                <div className="meetings-empty">
                                    <div className="meetings-empty-icon">
                                        📅
                                    </div>

                                    <strong>
                                        No meeting requests
                                    </strong>

                                    <span>
                                        Your meeting requests will appear here.
                                    </span>
                                </div>
                            )}

                        {!myMeetingsLoading &&
                            myMeetings.length >
                                0 && (
                                <div className="meetings-list">
                                    {myMeetings.map(
                                        (
                                            meeting
                                        ) => {
                                            const start =
                                                new Date(
                                                    meeting.start_datetime ||
                                                        meeting.start
                                                );

                                            const end =
                                                new Date(
                                                    meeting.end_datetime ||
                                                        meeting.end
                                                );

                                            const status =
                                                meeting.status ||
                                                "pending";

                                            const duration =
                                                meeting.duration ||
                                                Math.round(
                                                    (end.getTime() -
                                                        start.getTime()) /
                                                        60000
                                                );

                                            return (
                                                <div
                                                    className="meeting-item"
                                                    key={
                                                        meeting.id
                                                    }
                                                >
                                                    <div className="meeting-item-icon">
                                                        {status ===
                                                        "approved"
                                                            ? "✓"
                                                            : status ===
                                                              "rejected"
                                                            ? "✕"
                                                            : "🕐"}
                                                    </div>

                                                    <div className="meeting-item-content">
                                                        <strong>
                                                            Meeting with Admin
                                                        </strong>

                                                        <div className="meeting-item-details">
                                                            <span>
                                                                {start.toLocaleDateString(
                                                                    "en-IN",
                                                                    {
                                                                        day: "numeric",
                                                                        month: "short",
                                                                        year: "numeric",
                                                                        timeZone:
                                                                            "Asia/Kolkata",
                                                                    }
                                                                )}
                                                            </span>

                                                            <span>
                                                                {start.toLocaleTimeString(
                                                                    "en-IN",
                                                                    {
                                                                        hour: "numeric",
                                                                        minute: "2-digit",
                                                                        hour12: true,
                                                                        timeZone:
                                                                            "Asia/Kolkata",
                                                                    }
                                                                )}

                                                                {" – "}

                                                                {end.toLocaleTimeString(
                                                                    "en-IN",
                                                                    {
                                                                        hour: "numeric",
                                                                        minute: "2-digit",
                                                                        hour12: true,
                                                                        timeZone:
                                                                            "Asia/Kolkata",
                                                                    }
                                                                )}
                                                            </span>

                                                            <span>
                                                                {
                                                                    duration
                                                                }{" "}
                                                                min
                                                            </span>
                                                        </div>

                                                        {meeting.admin_message && (
                                                            <div className="meeting-admin-message">
                                                                {
                                                                    meeting.admin_message
                                                                }
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div
                                                        className={`meeting-status ${status}`}
                                                    >
                                                        {status ===
                                                            "pending" && (
                                                            <>
                                                                🕐
                                                                Pending
                                                            </>
                                                        )}

                                                        {status ===
                                                            "approved" && (
                                                            <>
                                                                ✓
                                                                Approved
                                                            </>
                                                        )}

                                                        {status ===
                                                            "rejected" && (
                                                            <>
                                                                ✕
                                                                Rejected
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        }
                                    )}
                                </div>
                            )}
                    </section>
                </main>
            </div>
        );
    }

    // ============================================================
    // ADMIN DASHBOARD
    // ============================================================

    return (
        <div className="app-shell">
            {/* ================================================== */}
            {/* MEETING REMINDER POPUP */}
            {/* ================================================== */}

            {meetingReminder && (
                <div className="meeting-reminder-overlay">
                    <div className="meeting-reminder-popup">
                        <div className="meeting-reminder-header">
                            <div>
                                <span className="meeting-reminder-label">
                                    Meeting Reminder
                                </span>

                                <h3>
                                    {meetingReminder.summary ||
                                        "Upcoming Meeting"}
                                </h3>
                            </div>

                            <button
                                className="meeting-reminder-close"
                                onClick={() =>
                                    setMeetingReminder(
                                        null
                                    )
                                }
                            >
                                ×
                            </button>
                        </div>

                        <div className="meeting-reminder-body">
                            <div className="meeting-reminder-time">
                                {meetingReminder.start
                                    ?.dateTime
                                    ? new Date(
                                          meetingReminder.start.dateTime
                                      ).toLocaleTimeString(
                                          "en-IN",
                                          {
                                              hour: "numeric",
                                              minute: "2-digit",
                                              hour12: true,
                                              timeZone:
                                                  "Asia/Kolkata",
                                          }
                                      )
                                    : "All day"}
                            </div>

                            <p>
                                Your meeting starts in
                                <strong>
                                    {" "}
                                    30 minutes.
                                </strong>
                            </p>

                            <div className="meeting-reminder-date">
                                {meetingReminder.start
                                    ?.dateTime
                                    ? new Date(
                                          meetingReminder.start.dateTime
                                      ).toLocaleDateString(
                                          "en-IN",
                                          {
                                              weekday:
                                                  "long",
                                              day: "numeric",
                                              month: "long",
                                              year: "numeric",
                                              timeZone:
                                                  "Asia/Kolkata",
                                          }
                                      )
                                    : ""}
                            </div>

                            {meetingReminder.location && (
                                <div className="meeting-reminder-location">
                                    {
                                        meetingReminder.location
                                    }
                                </div>
                            )}
                        </div>

                        <button
                            className="meeting-reminder-dismiss"
                            onClick={() =>
                                setMeetingReminder(
                                    null
                                )
                            }
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            )}

            {/* ================================================== */}
            {/* SIDEBAR */}
            {/* ================================================== */}

            <aside className="sidebar">
                <div className="sidebar-logo">
                    ✦
                </div>

                <div className="sidebar-nav">
                    <button
                        className="sidebar-icon active"
                        title="Dashboard"
                    >
                        ▦
                    </button>
                </div>
            </aside>

            {/* ================================================== */}
            {/* LEFT PANEL */}
            {/* ================================================== */}

            <aside className="left-panel">
                <div className="panel-header">
                    <h2>
                        About You & Connected Apps
                    </h2>

                    <p>
                        Your personal assistant workspace
                    </p>
                </div>

                {/* ================================================== */}
                {/* MEMORY */}
                {/* ================================================== */}

                <div className="section-card">
                    <div className="section-title-row">
                        <div>
                            <h3>
                                What I Know About You
                            </h3>

                            <p>
                                Personal memories
                            </p>
                        </div>

                        <button
                            className="add-memory-button"
                            onClick={() =>
                                setShowMemoryForm(
                                    !showMemoryForm
                                )
                            }
                        >
                            +
                        </button>
                    </div>

                    {showMemoryForm && (
                        <form
                            className="memory-form"
                            onSubmit={
                                saveMemory
                            }
                        >
                            <div className="memory-form-title">
                                Add Memory
                            </div>

                            <input
                                type="text"
                                placeholder="Key"
                                value={
                                    memoryKey
                                }
                                onChange={(
                                    event
                                ) =>
                                    setMemoryKey(
                                        event.target
                                            .value
                                    )
                                }
                            />

                            <input
                                type="text"
                                placeholder="Value"
                                value={
                                    memoryValue
                                }
                                onChange={(
                                    event
                                ) =>
                                    setMemoryValue(
                                        event.target
                                            .value
                                    )
                                }
                            />

                            <div className="memory-form-actions">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowMemoryForm(
                                            false
                                        );

                                        setMemoryKey(
                                            ""
                                        );

                                        setMemoryValue(
                                            ""
                                        );
                                    }}
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    disabled={
                                        memorySaving
                                    }
                                >
                                    {memorySaving
                                        ? "Saving..."
                                        : "Save"}
                                </button>
                            </div>
                        </form>
                    )}

                    {memoryLoading ? (
                        <div className="memory-loading">
                            Loading memories...
                        </div>
                    ) : memories.length ===
                      0 ? (
                        <div className="memory-empty">
                            I don't know anything about you yet.
                        </div>
                    ) : (
                        <div className="memory-dropdown">
                            <select
                                value={
                                    selectedMemoryId
                                }
                                onChange={(
                                    event
                                ) =>
                                    setSelectedMemoryId(
                                        event.target
                                            .value
                                    )
                                }
                            >
                                <option value="">
                                    Select something I know about you
                                </option>

                                {memories.map(
                                    (
                                        memory
                                    ) => (
                                        <option
                                            key={
                                                memory.id
                                            }
                                            value={
                                                memory.id
                                            }
                                        >
                                            {
                                                memory.key
                                            }
                                        </option>
                                    )
                                )}
                            </select>

                            {selectedMemoryId && (
                                <div className="selected-memory">
                                    {memories
                                        .filter(
                                            (
                                                memory
                                            ) =>
                                                String(
                                                    memory.id
                                                ) ===
                                                String(
                                                    selectedMemoryId
                                                )
                                        )
                                        .map(
                                            (
                                                memory
                                            ) => (
                                                <div
                                                    className="selected-memory-content"
                                                    key={
                                                        memory.id
                                                    }
                                                >
                                                    <strong>
                                                        {
                                                            memory.key
                                                        }
                                                    </strong>

                                                    <span>
                                                        {
                                                            memory.value
                                                        }
                                                    </span>

                                                    <div className="selected-memory-actions">
                                                        <button
                                                            type="button"
                                                            className="memory-edit"
                                                            onClick={() =>
                                                                startEditMemory(
                                                                    memory
                                                                )
                                                            }
                                                        >
                                                            ✎
                                                        </button>

                                                        <button
                                                            type="button"
                                                            className="memory-delete"
                                                            onClick={() => {
                                                                deleteMemory(
                                                                    memory.id
                                                                );

                                                                setSelectedMemoryId(
                                                                    ""
                                                                );
                                                            }}
                                                        >
                                                            ×
                                                        </button>
                                                    </div>
                                                </div>
                                            )
                                        )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* ================================================== */}
                    {/* EDIT MEMORY */}
                    {/* ================================================== */}

                    {editingMemoryId && (
                        <form
                            className="memory-form memory-edit-form"
                            onSubmit={
                                updateMemory
                            }
                        >
                            <div className="memory-form-title">
                                Edit Memory
                            </div>

                            <input
                                type="text"
                                placeholder="Key"
                                value={
                                    editMemoryKey
                                }
                                onChange={(
                                    event
                                ) =>
                                    setEditMemoryKey(
                                        event.target
                                            .value
                                    )
                                }
                            />

                            <input
                                type="text"
                                placeholder="Value"
                                value={
                                    editMemoryValue
                                }
                                onChange={(
                                    event
                                ) =>
                                    setEditMemoryValue(
                                        event.target
                                            .value
                                    )
                                }
                            />

                            <div className="memory-form-actions">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setEditingMemoryId(
                                            null
                                        );

                                        setEditMemoryKey(
                                            ""
                                        );

                                        setEditMemoryValue(
                                            ""
                                        );
                                    }}
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    disabled={
                                        memoryUpdating
                                    }
                                >
                                    {memoryUpdating
                                        ? "Saving..."
                                        : "Save"}
                                </button>
                            </div>
                        </form>
                    )}
                </div>

                {/* ================================================== */}
                {/* CONNECTED APPS */}
                {/* ================================================== */}

                <div className="section-card">
                    <div className="section-title-row">
                        <div>
                            <h3>
                                Connected Apps
                            </h3>

                            <p>
                                Services connected to your assistant
                            </p>
                        </div>
                    </div>

                    <div className="connected-app">
                        <div className="app-icon">
                            <img
                                src="/gmail-logo.png"
                                alt="Gmail"
                            />
                        </div>

                        <div className="app-info">
                            <strong>
                                Gmail
                            </strong>

                            <span>
                                Connected
                            </span>
                        </div>

                        <div className="connection-status">
                            ●
                        </div>
                    </div>

                    <div className="connected-app">
                        <div className="app-icon">
                            <img
                                src="/google-calendar-logo.png"
                                alt="Google Calendar"
                            />
                        </div>

                        <div className="app-info">
                            <strong>
                                Google Calendar
                            </strong>

                            <span>
                                Connected
                            </span>
                        </div>

                        <div className="connection-status">
                            ●
                        </div>
                    </div>
                </div>

                {/* ================================================== */}
                {/* USER */}
                {/* ================================================== */}

                <div className="left-panel-footer">
                    <div className="user-footer">
                        <div className="user-avatar">
                            {user?.name
                                ? user.name
                                      .charAt(0)
                                      .toUpperCase()
                                : "U"}
                        </div>

                        <div className="user-footer-info">
                            <strong>
                                {user?.name}
                            </strong>

                            <span>
                                {user?.email}
                            </span>
                        </div>

                        <button
                            className="small-logout"
                            onClick={
                                handleLogout
                            }
                            title="Logout"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </aside>

            {/* ================================================== */}
            {/* CENTER CHAT */}
            {/* ================================================== */}

            <main className="chat-panel">
                <div className="chat-header">
                    <div>
                        <h2>
                            Chat & Conversation
                        </h2>

                        <p>
                            Talk with your personal AI assistant
                        </p>
                    </div>

                    <button
                        className="new-chat-button"
                        onClick={
                            startNewChat
                        }
                    >
                        + Chat
                    </button>
                </div>

                <div className="chat-messages">
                    {messages.map(
                        (
                            message,
                            index
                        ) => (
                            <div
                                key={
                                    index
                                }
                                className={`message-row ${
                                    message.role ===
                                    "user"
                                        ? "user-row"
                                        : "assistant-row"
                                }`}
                            >
                                {message.role ===
                                    "assistant" && (
                                    <div className="ai-avatar">
                                        ✦
                                    </div>
                                )}

                                <div
                                    className={`message-bubble ${
                                        message.role ===
                                        "user"
                                            ? "user-message"
                                            : "assistant-message"
                                    }`}
                                >
                                    {
                                        message.content
                                    }
                                </div>
                            </div>
                        )
                    )}

                    {chatLoading && (
                        <div className="message-row assistant-row">
                            <div className="ai-avatar">
                                ✦
                            </div>

                            <div className="message-bubble assistant-message">
                                Thinking...
                            </div>
                        </div>
                    )}
                </div>

                <div className="chat-bottom">
                    <div className="remembered-chip">
                        ✦

                        <span>
                            Your assistant remembers your preferences
                        </span>
                    </div>

                    <form
                        className="chat-input-area"
                        onSubmit={
                            handleSubmit
                        }
                    >
                        <input
                            type="text"
                            placeholder="Ask your assistant anything..."
                            value={
                                messageInput
                            }
                            onChange={(
                                event
                            ) =>
                                setMessageInput(
                                    event.target
                                        .value
                                )
                            }
                        />

                        <button
                            type="submit"
                            className="send-button"
                            disabled={
                                chatLoading ||
                                !messageInput.trim()
                            }
                        >
                            →
                        </button>
                    </form>
                </div>
            </main>

            {/* ================================================== */}
            {/* RIGHT PANEL */}
            {/* ================================================== */}

            <aside className="right-panel">
                <div className="right-panel-header">
                    <h2>
                        Today's Focus
                    </h2>

                    <p>
                        Your personal priorities, email & calendar
                    </p>
                </div>

                {/* ================================================== */}
                {/* MEETING REQUESTS */}
                {/* ================================================== */}

                <div className="dashboard-card meeting-requests-card">
                    <div className="card-header">
                        <div>
                            <h3>
                                Meeting Requests
                            </h3>

                            <p>
                                Requests waiting for your approval
                            </p>
                        </div>

                        <button
                            className="meeting-requests-refresh"
                            onClick={() =>
                                fetchMeetingRequests(
                                    token
                                )
                            }
                            disabled={
                                meetingRequestsLoading
                            }
                        >
                            {meetingRequestsLoading
                                ? "..."
                                : "↻"}
                        </button>
                    </div>

                    {meetingRequestsLoading ? (
                        <div className="meeting-requests-empty">
                            Loading meeting requests...
                        </div>
                    ) : meetingRequestsError ? (
                        <div className="calendar-error">
                            {
                                meetingRequestsError
                            }
                        </div>
                    ) : meetingRequests.length ===
                      0 ? (
                        <div className="meeting-requests-empty">
                            <div className="meeting-request-empty-icon">
                                ✓
                            </div>

                            <strong>
                                No meeting requests
                            </strong>

                            <span>
                                New requests from users will appear here.
                            </span>
                        </div>
                    ) : (
                        <div className="meeting-requests-list">
                            {meetingRequests.map(
                                (
                                    request
                                ) => {
                                    const start =
                                        new Date(
                                            request.start_datetime
                                        );

                                    const end =
                                        new Date(
                                            request.end_datetime
                                        );

                                    const isPending =
                                        request.status ===
                                        "pending";

                                    return (
                                        <div
                                            className="meeting-request-item"
                                            key={
                                                request.id
                                            }
                                        >
                                            <div className="meeting-request-top">
                                                <div className="meeting-request-user">
                                                    <div className="meeting-request-avatar">
                                                        {request.user_name
                                                            ?.charAt(
                                                                0
                                                            )
                                                            ?.toUpperCase() ||
                                                            "U"}
                                                    </div>

                                                    <div>
                                                        <strong>
                                                            {
                                                                request.user_name
                                                            }
                                                        </strong>

                                                        <span>
                                                            {
                                                                request.user_email
                                                            }
                                                        </span>
                                                    </div>
                                                </div>

                                                <span className="meeting-request-status pending">
                                                    Pending
                                                </span>
                                            </div>

                                            <div className="meeting-request-details">
                                                <div>
                                                    <span>
                                                        Date
                                                    </span>

                                                    <strong>
                                                        {start.toLocaleDateString(
                                                            "en-IN",
                                                            {
                                                                day: "numeric",
                                                                month: "short",
                                                                year: "numeric",
                                                                timeZone:
                                                                    "Asia/Kolkata",
                                                            }
                                                        )}
                                                    </strong>
                                                </div>

                                                <div>
                                                    <span>
                                                        Time
                                                    </span>

                                                    <strong>
                                                        {start.toLocaleTimeString(
                                                            "en-IN",
                                                            {
                                                                hour: "numeric",
                                                                minute: "2-digit",
                                                                hour12: true,
                                                                timeZone:
                                                                    "Asia/Kolkata",
                                                            }
                                                        )}

                                                        {" – "}

                                                        {end.toLocaleTimeString(
                                                            "en-IN",
                                                            {
                                                                hour: "numeric",
                                                                minute: "2-digit",
                                                                hour12: true,
                                                                timeZone:
                                                                    "Asia/Kolkata",
                                                            }
                                                        )}
                                                    </strong>
                                                </div>

                                                <div>
                                                    <span>
                                                        Duration
                                                    </span>

                                                    <strong>
                                                        {
                                                            request.duration
                                                        }{" "}
                                                        min
                                                    </strong>
                                                </div>
                                            </div>

                                            {request.admin_message && (
                                                <div className="meeting-request-message">
                                                    {
                                                        request.admin_message
                                                    }
                                                </div>
                                            )}

                                            {isPending && (
                                                <div className="meeting-request-actions">
                                                    <button
                                                        className="approve-meeting-button"
                                                        onClick={() =>
                                                            approveMeetingRequest(
                                                                request.id
                                                            )
                                                        }
                                                        disabled={
                                                            meetingActionLoading ===
                                                            request.id
                                                        }
                                                    >
                                                        {meetingActionLoading ===
                                                        request.id
                                                            ? "Processing..."
                                                            : "✓ Approve"}
                                                    </button>

                                                    <button
                                                        className="reject-meeting-button"
                                                        onClick={() =>
                                                            rejectMeetingRequest(
                                                                request.id
                                                            )
                                                        }
                                                        disabled={
                                                            meetingActionLoading ===
                                                            request.id
                                                        }
                                                    >
                                                        ✕ Reject
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                }
                            )}
                        </div>
                    )}

                    {meetingActionMessage && (
                        <div className="meeting-action-message">
                            {
                                meetingActionMessage
                            }
                        </div>
                    )}
                </div>

                {/* ================================================== */}
                {/* GMAIL */}
                {/* ================================================== */}

                <div className="dashboard-card gmail-card">
                    <div className="card-header">
                        <div>
                            <h3>
                                Gmail
                            </h3>

                            <p>
                                Email confirmation & drafts
                            </p>
                        </div>

                        <span className="status-dot">
                            ●
                        </span>
                    </div>

                    {pendingEmail ? (
                        <div className="gmail-confirmation">
                            <div className="gmail-confirmation-icon">
                                ✉
                            </div>

                            <div className="gmail-confirmation-title">
                                Email ready to send
                            </div>

                            <div className="gmail-confirmation-text">
                                Your email has been prepared. Please confirm before sending.
                            </div>

                            <div className="gmail-action-status">
                                Pending confirmation
                            </div>

                            <div className="gmail-action-buttons">
                                <button
                                    className="gmail-confirm-button"
                                    onClick={
                                        confirmEmailAction
                                    }
                                    disabled={
                                        emailActionLoading
                                    }
                                >
                                    {emailActionLoading
                                        ? "Sending..."
                                        : "✓ Confirm & Send"}
                                </button>

                                <button
                                    className="gmail-rewrite-button"
                                    onClick={
                                        rewriteEmailDraft
                                    }
                                    disabled={
                                        emailActionLoading
                                    }
                                >
                                    ↻ Rewrite Draft
                                </button>

                                <button
                                    className="gmail-cancel-button"
                                    onClick={
                                        cancelEmailAction
                                    }
                                    disabled={
                                        emailActionLoading
                                    }
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="gmail-ready">
                            <div className="gmail-ready-icon">
                                ✉
                            </div>

                            <strong>
                                No email awaiting confirmation
                            </strong>

                            <span>
                                Ask your assistant to draft or send an email.
                            </span>
                        </div>
                    )}

                    {emailActionMessage && (
                        <div className="gmail-action-message">
                            {
                                emailActionMessage
                            }
                        </div>
                    )}
                </div>

                {/* ================================================== */}
                {/* CALENDAR */}
                {/* ================================================== */}

                <div className="dashboard-card calendar-card">
                    <div className="card-header">
                        <div>
                            <h3>
                                Calendar Sneak Peek
                            </h3>

                            <p>
                                All upcoming events
                            </p>
                        </div>

                        <span className="status-dot">
                            ●
                        </span>
                    </div>

                    {calendarLoading ? (
                        <div className="calendar-empty">
                            Loading calendar...
                        </div>
                    ) : calendarError ? (
                        <div className="calendar-error">
                            {
                                calendarError
                            }
                        </div>
                    ) : calendarEvents.length ===
                      0 ? (
                        <div className="calendar-empty">
                            <strong>
                                No upcoming events
                            </strong>
                        </div>
                    ) : (
                        <div className="calendar-dropdown">
                            <select
                                value={
                                    selectedCalendarEvent?.id ||
                                    ""
                                }
                                onChange={(
                                    event
                                ) => {
                                    const selected =
                                        calendarEvents.find(
                                            (
                                                calendarEvent
                                            ) =>
                                                calendarEvent.id ===
                                                event
                                                    .target
                                                    .value
                                        );

                                    setSelectedCalendarEvent(
                                        selected ||
                                            null
                                    );
                                }}
                            >
                                <option value="">
                                    Select a calendar event
                                </option>

                                {calendarEvents.map(
                                    (
                                        event
                                    ) => {
                                        const startDateTime =
                                            event.start
                                                ?.dateTime ||
                                            event.start
                                                ?.date;

                                        if (
                                            !startDateTime
                                        ) {
                                            return null;
                                        }

                                        const eventDate =
                                            new Date(
                                                startDateTime
                                            );

                                        const dateText =
                                            eventDate.toLocaleDateString(
                                                "en-IN",
                                                {
                                                    day: "numeric",
                                                    month: "short",
                                                    timeZone:
                                                        "Asia/Kolkata",
                                                }
                                            );

                                        const timeText =
                                            event.start
                                                ?.dateTime
                                                ? eventDate.toLocaleTimeString(
                                                      "en-IN",
                                                      {
                                                          hour: "numeric",
                                                          minute: "2-digit",
                                                          hour12: true,
                                                          timeZone:
                                                              "Asia/Kolkata",
                                                      }
                                                  )
                                                : "All day";

                                        return (
                                            <option
                                                key={
                                                    event.id
                                                }
                                                value={
                                                    event.id
                                                }
                                            >
                                                {event.summary ||
                                                    "Untitled event"}{" "}
                                                —{" "}
                                                {
                                                    dateText
                                                }{" "}
                                                {
                                                    timeText
                                                }
                                            </option>
                                        );
                                    }
                                )}
                            </select>

                            {selectedCalendarEvent && (
                                <div className="calendar-selected-event">
                                    <div className="calendar-event">
                                        <div className="calendar-time">
                                            {selectedCalendarEvent
                                                .start
                                                ?.dateTime
                                                ? new Date(
                                                      selectedCalendarEvent
                                                          .start
                                                          .dateTime
                                                  ).toLocaleTimeString(
                                                      "en-IN",
                                                      {
                                                          hour: "numeric",
                                                          minute: "2-digit",
                                                          hour12: true,
                                                          timeZone:
                                                              "Asia/Kolkata",
                                                      }
                                                  )
                                                : "All day"}
                                        </div>

                                        <div className="calendar-event-info">
                                            <strong>
                                                {selectedCalendarEvent.summary ||
                                                    "Untitled event"}
                                            </strong>

                                            <span>
                                                {new Date(
                                                    selectedCalendarEvent
                                                        .start
                                                        ?.dateTime ||
                                                        selectedCalendarEvent
                                                            .start
                                                            ?.date
                                                ).toLocaleDateString(
                                                    "en-IN",
                                                    {
                                                        weekday:
                                                            "short",
                                                        day: "numeric",
                                                        month: "short",
                                                        year: "numeric",
                                                        timeZone:
                                                            "Asia/Kolkata",
                                                    }
                                                )}
                                            </span>
                                        </div>
                                    </div>

                                    {selectedCalendarEvent.location && (
                                        <div className="calendar-detail">
                                            <span>
                                                Location
                                            </span>

                                            <strong>
                                                {
                                                    selectedCalendarEvent.location
                                                }
                                            </strong>
                                        </div>
                                    )}

                                    {selectedCalendarEvent.description && (
                                        <div className="calendar-detail">
                                            <span>
                                                Description
                                            </span>

                                            <strong>
                                                {
                                                    selectedCalendarEvent.description
                                                }
                                            </strong>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </aside>
        </div>
    );
}

export default App;