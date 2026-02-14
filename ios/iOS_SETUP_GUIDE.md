# Budget Master iOS App - Setup Guide

## Overview

This guide will help you set up the Budget Master iOS app, which connects to your FastAPI backend on Cloud Run using Firebase Authentication.

## Project Structure

```
ios/
├── BudgetMaster/              # Swift Package (Models, Networking, Services)
└── BudgetMasterApp/           # iOS App Project
    ├── BudgetMasterApp.swift
    ├── ContentView.swift
    ├── Info.plist
    ├── GoogleService-Info.plist
    ├── Authentication/
    │   ├── AuthenticationManager.swift
    │   └── FirebaseTokenProvider.swift
    └── Views/
        ├── LoginView.swift
        ├── DashboardView.swift
        ├── ExpensesView.swift
        └── ChatView.swift
```

## Prerequisites

- macOS with Xcode 15.0 or later
- iOS 16.0+ deployment target
- Firebase project: `budget-master-lh`
- Backend deployed to Cloud Run

## Step 1: Create Xcode Project

1. **Open Xcode** and create a new iOS App project:
   - Product Name: `BudgetMasterApp`
   - Bundle Identifier: `com.yourcompany.budgetmaster`
   - Interface: SwiftUI
   - Language: Swift
   - Minimum iOS Version: 16.0

2. **Add all the Swift files** from `iosBudgetMasterApp/` to your Xcode project:
   - `BudgetMasterApp.swift`
   - `ContentView.swift`
   - `Authentication/AuthenticationManager.swift`
   - `Authentication/FirebaseTokenProvider.swift`
   - `Views/LoginView.swift`
   - `Views/DashboardView.swift`
   - `Views/ExpensesView.swift`
   - `Views/ChatView.swift`

3. **Add configuration files**:
   - `Info.plist` (already configured)
   - `GoogleService-Info.plist` (needs real data from Firebase)

## Step 2: Add BudgetMaster Swift Package

1. In Xcode, go to **File → Add Package Dependencies...**

2. Click **Add Local...** and select the `ios/BudgetMaster` folder

3. Add the package to your app target

The BudgetMaster package includes:
- **Models**: `Expense`, `User`, `Budget`, etc.
- **Networking**: `APIClient`, `TokenProvider` protocol
- **Services**: API service wrappers

## Step 3: Configure Firebase

### Register iOS App in Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project: `budget-master-lh`
3. Click **Add App** → **iOS**
4. Register with bundle ID: `com.yourcompany.budgetmaster`
5. **Download GoogleService-Info.plist**
6. Replace the template file in your Xcode project with the real one
7. Make sure it's added to your app target

### Add Firebase SDK via Swift Package Manager

1. In Xcode, go to **File → Add Package Dependencies...**
2. Enter URL: `https://github.com/firebase/firebase-ios-sdk.git`
3. Select version: `10.20.0` or later
4. Add these products to your app target:
   - **FirebaseAuth**
   - **FirebaseCore**

## Step 4: Configure Backend URL

In `ChatView.swift`, update the `AppConfiguration` enum:

```swift
enum AppConfiguration {
    static let baseURL = URL(string: "https://your-backend-url.run.app")!
    
    // Replace with your actual Cloud Run URL
    // Example: https://budget-master-backend-abc123-uc.a.run.app
}
```

## Step 5: Integrate BudgetMaster Package Models

The app currently has placeholder models. You'll need to update the views to use the actual models from the BudgetMaster package:

### Update Expense Model Usage

In `DashboardView.swift` and `ExpensesView.swift`, replace the placeholder `Expense` struct with imports from BudgetMaster:

```swift
import BudgetMaster

// Use BudgetMaster.Expense instead of local struct
```

### Update Service Integration

In `ChatView.swift`, replace the mock `BudgetService` and `ChatService` with the real implementations from BudgetMaster:

```swift
import BudgetMaster

// Initialize services with FirebaseTokenProvider
let tokenProvider = FirebaseTokenProvider()
let budgetService = BudgetMasterAPI.BudgetService(
    tokenProvider: tokenProvider,
    baseURL: AppConfiguration.baseURL
)
```

## Step 6: Build and Test

### Run Setup Check Script

From the `iosBudgetMasterApp/` directory:

```bash
chmod +x setup-check.sh
./setup-check.sh
```

This will verify:
- ✓ Xcode installation
- ✓ Project structure
- ✓ Firebase configuration
- ✓ All required Swift files
- ✓ BudgetMaster package

### Build in Xcode

1. Select a simulator or device
2. Press **Cmd + B** to build
3. Fix any compilation errors
4. Press **Cmd + R** to run

## Architecture Overview

### Authentication Flow

1. User signs in via `LoginView` using Firebase Auth
2. `AuthenticationManager` manages auth state
3. `FirebaseTokenProvider` implements `TokenProvider` protocol from BudgetMaster package
4. Token is automatically injected into API requests

### Networking Layer

The BudgetMaster Swift Package provides:

```swift
protocol TokenProvider {
    func getToken() async throws -> String?
    func refreshToken() async throws -> String?
}

class APIClient {
    let tokenProvider: TokenProvider
    let baseURL: URL
    
    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T
}
```

Your `FirebaseTokenProvider` bridges Firebase Auth with this protocol.

### Views

#### LoginView
- Email/password authentication
- Sign up / Sign in toggle
- Firebase Auth integration

#### DashboardView
- Budget summary card (total spent, limit, percentage)
- Category breakdown with visual charts
- Recent expenses list
- Pull-to-refresh

#### ExpensesView
- List/grid of all expenses
- Filtering (category, date range, amount)
- Swipe actions (edit, delete)
- Add new expense sheet
- Pagination support

#### ChatView
- Streaming SSE conversation with AI assistant
- Real-time message updates
- Sample questions sheet
- Clear history option

## API Endpoints Used

Based on `docs/openapi.json`:

### Authentication
- **POST** `/api/auth/signup` - Create new user
- **POST** `/api/auth/signin` - Sign in user

### Budget
- **GET** `/api/budget/summary` - Get budget overview
- **GET** `/api/expenses` - List expenses with filters
- **POST** `/api/expenses` - Create expense
- **PUT** `/api/expenses/{id}` - Update expense
- **DELETE** `/api/expenses/{id}` - Delete expense

### Chat
- **GET** `/api/chat/stream` - SSE streaming chat endpoint

## Firebase Setup Requirements

### Enable Authentication

In Firebase Console:
1. Go to **Authentication** → **Sign-in method**
2. Enable **Email/Password**

### Security Rules

Ensure your Firestore rules allow authenticated users:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Testing

### Manual Testing Checklist

- [ ] Login with email/password
- [ ] Sign up new user
- [ ] View dashboard with budget summary
- [ ] See category breakdown
- [ ] View expenses list
- [ ] Add new expense
- [ ] Edit existing expense
- [ ] Delete expense
- [ ] Filter expenses
- [ ] Chat with AI assistant
- [ ] Logout

### Unit Testing

Create tests for:
- `AuthenticationManager` auth flows
- `FirebaseTokenProvider` token refresh
- View models business logic

Example with Swift Testing:

```swift
import Testing
@testable import BudgetMasterApp

@Suite("Authentication Tests")
struct AuthenticationTests {
    
    @Test("Sign in with valid credentials")
    func signInSuccess() async throws {
        let manager = AuthenticationManager()
        // Test implementation
    }
}
```

## Troubleshooting

### Firebase Configuration Issues

**Problem**: "FirebaseApp.configure() fails"
- **Solution**: Ensure `GoogleService-Info.plist` is in the app target and contains real data

**Problem**: "No user signed in"
- **Solution**: Check Firebase Console that Email/Password auth is enabled

### Networking Issues

**Problem**: "Failed to connect to backend"
- **Solution**: Verify `AppConfiguration.baseURL` is correct Cloud Run URL

**Problem**: "Unauthorized (401)"
- **Solution**: Check Firebase token is being sent in Authorization header

### Build Errors

**Problem**: "Cannot find 'BudgetMaster' in scope"
- **Solution**: Add BudgetMaster package as local dependency in Xcode

**Problem**: "Missing GoogleService-Info.plist"
- **Solution**: Download from Firebase Console and add to Xcode project

## Next Steps

1. **Add real models**: Replace placeholder models with BudgetMaster package types
2. **Implement persistence**: Add local caching with SwiftData or Core Data
3. **Add charts**: Use Swift Charts for better data visualization
4. **Implement notifications**: Add push notifications for budget alerts
5. **Add widgets**: Create Home Screen widgets for quick budget overview
6. **Offline support**: Handle offline scenarios gracefully

## Resources

- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui)
- [Firebase iOS SDK](https://firebase.google.com/docs/ios/setup)
- [Swift Concurrency](https://docs.swift.org/swift-book/LanguageGuide/Concurrency.html)
- Backend API: `docs/openapi.json`
- Networking Architecture: `docs/ios-networking-layer.md`

## Support

For issues or questions:
1. Check this guide
2. Review `docs/ios-networking-layer.md`
3. Check backend API spec in `docs/openapi.json`
4. Run `./setup-check.sh` to verify setup

---

**Ready to build!** Open `BudgetMasterApp.xcodeproj` in Xcode and start coding! 🚀
