# React Native iOS Conversion Plan

This document outlines the assessment and plan for converting the Budget Master web frontend (React + Vite) to a React Native iOS app.

## Overview

The current `frontend/` is a React web app with ~6,000 lines of TypeScript across 56 files. The app already has responsive design that works well on mobile browsers, which simplifies the conversion significantly.

**Recommended Stack:**
- **Expo** - Managed workflow for easier iOS builds and native module access
- **NativeWind** - Tailwind-like styling for React Native (reuse existing class names)
- **expo-router** - File-based routing similar to web patterns
- **expo-av** - Audio recording for voice memos

## Estimated Timeline

**12-18 developer-days** (~2-3 weeks)

This assumes:
- Using Expo + NativeWind (reduces complexity significantly)
- Implementing the existing mobile-responsive layout directly (no redesign needed)
- Developer has React experience but may be new to React Native

## What Ports Easily (~70% of codebase)

These can be reused with minimal or no changes:

| Area | Files | Notes |
|------|-------|-------|
| **TypeScript types** | `frontend/src/types/` | Fully compatible |
| **API services** | `frontend/src/services/api.ts` | Axios works in RN |
| **Auth context** | `frontend/src/contexts/AuthContext.tsx` | Firebase SDK has RN support |
| **Theme context** | `frontend/src/contexts/ThemeContext.tsx` | Minor changes for Appearance API |
| **Custom hooks** | `frontend/src/hooks/` | useState/useContext identical |
| **Business logic** | useChat, useExpenses, useBudget, etc. | All reusable |

## What Needs Changes (~30% of codebase)

### 1. Styling (Effort: Low with NativeWind)

Most Tailwind classes work directly with NativeWind. Exceptions:
- Arbitrary values like `h-[calc(100dvh-56px)]` need simplification
- Responsive breakpoints (`lg:hidden`) not needed - just build mobile view directly
- Custom CSS animations need Reanimated equivalents

### 2. Routing (Effort: Low-Medium)

| Web | React Native |
|-----|--------------|
| `react-router-dom` | `expo-router` |
| `<BrowserRouter>` | File-based routing in `app/` directory |
| `useNavigate()` | `useRouter()` from expo-router |
| URL paths | Stack/tab navigation |

The protected route pattern (`ProtectedLayout`) translates to expo-router's layout routes.

### 3. Web API Replacements (Effort: Low)

| Web API | React Native Equivalent |
|---------|------------------------|
| `localStorage` | `@react-native-async-storage/async-storage` |
| `window.matchMedia('prefers-color-scheme')` | `Appearance` from react-native |
| `createPortal()` for modals | `<Modal>` from react-native |
| `document.addEventListener` | Gesture handlers or built-in components |
| `crypto.randomUUID()` | `uuid` package or `expo-crypto` |

### 4. Audio Recording (Effort: Medium)

Current web implementation in `useVoiceRecording.ts`:
```typescript
// Web - won't work in RN
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
const mediaRecorder = new MediaRecorder(stream, { mimeType })
```

React Native replacement with expo-av:
```typescript
// React Native
import { Audio } from 'expo-av'
const recording = new Audio.Recording()
await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY)
await recording.startAsync()
```

## Hard Parts & Risks

### 1. Audio Permissions (Risk: Medium-High)

iOS requires explicit permission descriptions and graceful handling of:
- Initial permission request
- User denying permission
- User revoking permission later (in Settings)
- Audio session interruptions (phone calls, other apps)

**Mitigation:** Test permission flows thoroughly on real iOS device.

### 2. SSE Chat Streaming (Risk: Medium)

The chat uses Server-Sent Events (`streamChat` function). React Native's fetch may not handle SSE identically to browsers.

**Mitigation:**
- Test early in development
- Have `react-native-sse` as backup if native fetch doesn't work
- Consider fallback to polling if SSE proves unreliable

### 3. Custom Animations (Risk: Low-Medium)

The Apple Intelligence glow effects (`apple-glow-spin-and-fade`, `apple-glow-settle`) are pure CSS. Options:
- Rebuild with `react-native-reanimated` (more effort, full parity)
- Simplify for v1 (less effort, ship faster)

## Implementation Phases

### Phase 1: Project Setup (1-2 days)
- [ ] Create Expo project with TypeScript template
- [ ] Install NativeWind and configure
- [ ] Install expo-router and set up navigation structure
- [ ] Install and configure Firebase for React Native
- [ ] Set up expo-av for audio

### Phase 2: Core Infrastructure (2-3 days)
- [ ] Port AuthContext (swap localStorage → AsyncStorage)
- [ ] Port ThemeContext (swap matchMedia → Appearance API)
- [ ] Port API service layer (test that Axios works)
- [ ] Test SSE streaming - identify issues early

### Phase 3: Screens & Components (5-7 days)
- [ ] Port LoginPage
- [ ] Port ChatPage (main screen)
- [ ] Port DashboardPage
- [ ] Port ExpensesPage
- [ ] Port shared UI components (Modal, Card, Button, etc.)
- [ ] Port chat components (ChatMessage, ChatInput, ToolCallDisplay)

### Phase 4: Audio Recording (2-3 days)
- [ ] Implement useVoiceRecording with expo-av
- [ ] Add iOS permission handling
- [ ] Test audio format compatibility with Whisper endpoint
- [ ] Handle edge cases (interruptions, permission denial)

### Phase 5: Polish & Testing (2-3 days)
- [ ] Test on real iOS device
- [ ] Fix platform-specific bugs
- [ ] Add loading states and error handling
- [ ] Performance optimization if needed
- [ ] Prepare for TestFlight / App Store

## File Structure (Proposed)

```
mobile/
├── app/                    # expo-router pages
│   ├── _layout.tsx        # Root layout (auth check)
│   ├── index.tsx          # Redirect to /chat
│   ├── login.tsx          # Login screen
│   ├── (app)/             # Authenticated routes
│   │   ├── _layout.tsx    # Tab navigator
│   │   ├── chat.tsx       # Chat screen
│   │   ├── dashboard.tsx  # Dashboard screen
│   │   └── expenses.tsx   # Expenses screen
├── components/            # Ported from frontend/src/components
├── contexts/              # Ported from frontend/src/contexts
├── hooks/                 # Ported from frontend/src/hooks
├── services/              # Ported from frontend/src/services
├── types/                 # Copied from frontend/src/types
├── app.json              # Expo config
├── tailwind.config.js    # NativeWind config
└── package.json
```

## Dependencies

### Required
```json
{
  "expo": "~50.x",
  "expo-router": "~3.x",
  "expo-av": "~13.x",
  "nativewind": "^4.x",
  "tailwindcss": "^3.x",
  "@react-native-async-storage/async-storage": "^1.x",
  "axios": "^1.x",
  "firebase": "^10.x"
}
```

### Potentially Needed
```json
{
  "react-native-sse": "^1.x",
  "react-native-reanimated": "~3.x",
  "expo-crypto": "~12.x"
}
```

## Open Questions

1. **App Store account** - Do we have an Apple Developer account ($99/year)?
2. **Bundle identifier** - What should the app ID be? (e.g., `com.budgetmaster.app`)
3. **Minimum iOS version** - iOS 15+ recommended for best Expo compatibility
4. **Push notifications** - Needed for budget alerts? (adds complexity)
5. **Offline support** - Should expenses work offline? (adds complexity)

## References

- [Expo Documentation](https://docs.expo.dev/)
- [NativeWind Documentation](https://www.nativewind.dev/)
- [expo-router Documentation](https://docs.expo.dev/router/introduction/)
- [expo-av Audio Recording](https://docs.expo.dev/versions/latest/sdk/av/)
