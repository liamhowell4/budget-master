# Conversation History Left Sidebar - Implementation Plan

## Overview
Add a left sidebar to ChatPage showing conversation history, with full persistence via existing backend endpoints.

## Key Finding
**The backend already supports conversations!** All Firestore operations and API endpoints exist:
- `GET /conversations` - List conversations
- `GET /conversations/{id}` - Get conversation with messages
- `POST /conversations` - Create new conversation
- `DELETE /conversations/{id}` - Delete conversation

We only need frontend implementation.

---

## Implementation Steps

### 1. Add Types (`src/types/chat.ts`)
```typescript
export interface Conversation {
  id: string
  created_at: string
  last_activity: string
  messages: ChatMessage[]
  summary: string | null
}

export interface ConversationListItem {
  id: string
  created_at: string
  last_activity: string
  summary: string | null
  message_count: number
}
```

### 2. Add Service Functions (`src/services/conversationService.ts`)
New file with:
- `listConversations(token, limit?)` - GET /conversations
- `getConversation(token, id)` - GET /conversations/{id}
- `createConversation(token)` - POST /conversations
- `deleteConversation(token, id)` - DELETE /conversations/{id}

### 3. Create Hook (`src/hooks/useConversations.ts`)
Follow `useExpenses.ts` pattern:
- Session-level cache with Map
- `useConversations()` returns `{ conversations, loading, refetch }`
- `invalidateConversationsCache()` export for cache busting

### 4. Update useChat Hook (`src/hooks/useChat.ts`)
- Add `conversationId` state
- Add `loadConversation(id)` to fetch and restore messages
- Add `startNewConversation()` to create new conversation
- Call backend to persist messages (or rely on backend's existing behavior)
- Expose `conversationId` for sidebar highlighting

### 5. Create Left Sidebar Component (`src/components/chat/ConversationSidebar.tsx`)
Layout:
- "New Chat" button at top
- List of conversations (most recent first)
- Each item shows: summary/preview, relative time, message count
- Click to load, hover for delete button
- Responsive: inline on xl+, overlay on mobile (mirror right sidebar)

### 6. Update ChatPage (`src/pages/ChatPage.tsx`)
- Add left sidebar state management
- Integrate ConversationSidebar
- Wire up conversation selection/creation
- Balanced 3-column layout on xl+: left sidebar | chat | right sidebar

---

## File Changes Summary

| File | Action |
|------|--------|
| `src/types/chat.ts` | Add Conversation types |
| `src/services/conversationService.ts` | **New** - API calls |
| `src/hooks/useConversations.ts` | **New** - Data hook |
| `src/hooks/useChat.ts` | Add conversation support |
| `src/components/chat/ConversationSidebar.tsx` | **New** - UI component |
| `src/components/chat/index.ts` | Export new component |
| `src/pages/ChatPage.tsx` | Integrate left sidebar |

---

## Layout on Large Screens (xl+)

```
┌─────────────────────────────────────────────────────────────┐
│                        Header                                │
├──────────────┬────────────────────────┬─────────────────────┤
│ Conversation │                        │   Budget Sidebar    │
│   History    │      Chat Area         │   (existing)        │
│   (new)      │                        │                     │
│   w-64       │      flex-1            │      w-80           │
└──────────────┴────────────────────────┴─────────────────────┘
```

---

## Verification
1. Start dev server: `npm run dev`
2. Create a new conversation via "New Chat"
3. Send messages, verify they persist on refresh
4. Switch between conversations
5. Delete a conversation
6. Test responsive behavior (resize window)
7. Verify right sidebar still works correctly
