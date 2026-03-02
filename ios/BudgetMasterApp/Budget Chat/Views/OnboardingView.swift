import SwiftUI
import BudgetMaster

// MARK: - OnboardingView

struct OnboardingView: View {
    let onComplete: () -> Void

    @EnvironmentObject private var authManager: AuthenticationManager
    @Environment(\.appAccent) private var appAccent
    @Environment(\.appBackgroundTint) private var backgroundTint
    @State private var currentStep = 0
    @State private var totalBudget: Double = 0
    @State private var budgetText = ""
    @State private var defaultCategories: [DefaultCategory] = []
    @State private var selectedCategoryIds: Set<String> = []
    @State private var categoryCaps: [String: Double] = [:]
    @State private var categoryCapTexts: [String: String] = [:]
    @State private var customCategories: [CustomCategoryInput] = []
    @State private var excludedCategoryIds: Set<String> = []
    @State private var isLoadingDefaults = true
    @State private var isSubmitting = false
    @State private var errorMessage: String?
    @State private var showAddCustomSheet = false

    // Step indices:
    // 0 = welcome, 1 = income planner, 2 = budget, 3 = categories,
    // 4 = allocation, 5 = exclusions, 6 = review
    private let stepCount = 7

    var body: some View {
        ZStack {
            backgroundTint
                .ignoresSafeArea()

            VStack(spacing: 0) {
                stepIndicator
                    .padding(.top, 16)
                    .padding(.bottom, 8)

                TabView(selection: $currentStep) {
                    welcomeStep.tag(0)
                    incomePlannerStep.tag(1)
                    budgetStep.tag(2)
                    categoriesStep.tag(3)
                    allocationStep.tag(4)
                    exclusionsStep.tag(5)
                    reviewStep.tag(6)
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(.spring(response: 0.4, dampingFraction: 0.85), value: currentStep)

                navigationButtons
                    .padding(.horizontal, 24)
                    .padding(.bottom, 16)
            }

            VStack {
                HStack {
                    Spacer()
                    Button("Sign Out") {
                        authManager.signOut()
                    }
                    .font(.body.bold())
                    .foregroundStyle(.red)
                    .padding(.trailing, 20)
                    .padding(.top, 16)
                }
                Spacer()
            }
        }
        .task {
            await loadDefaults()
        }
    }

    // MARK: - Step Indicator

    private var stepIndicator: some View {
        HStack(spacing: 8) {
            ForEach(0..<stepCount, id: \.self) { step in
                Capsule()
                    .fill(stepColor(for: step))
                    .frame(width: step == currentStep ? 24 : 8, height: 8)
                    .animation(.spring(response: 0.3, dampingFraction: 0.7), value: currentStep)
            }
        }
    }

    private func stepColor(for step: Int) -> Color {
        if step == currentStep {
            return appAccent
        } else if step < currentStep {
            return appAccent.opacity(0.4)
        } else {
            return Color(uiColor: .systemGray4)
        }
    }

    // MARK: - Navigation Buttons

    /// Steps that manage their own navigation via internal buttons (no outer Next button shown).
    private var stepManagesOwnNavigation: Bool {
        currentStep == 1 || currentStep == 5
    }

    private var navigationButtons: some View {
        HStack {
            if currentStep > 0 {
                Button {
                    withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                        currentStep -= 1
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "chevron.left")
                        Text("Back")
                    }
                    .font(.body.weight(.medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 12)
                    .glassCapsule()
                }
            }

            Spacer()

            if stepManagesOwnNavigation {
                // No outer Next button — the step's own UI handles advancement.
                EmptyView()
            } else if currentStep < stepCount - 1 {
                Button {
                    withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                        currentStep += 1
                    }
                } label: {
                    HStack(spacing: 4) {
                        Text("Next")
                        Image(systemName: "chevron.right")
                    }
                    .font(.body.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(canAdvance ? appAccent : Color(uiColor: .systemGray3))
                    .clipShape(Capsule())
                }
                .disabled(!canAdvance)
            } else {
                Button {
                    Task { await completeOnboarding() }
                } label: {
                    if isSubmitting {
                        ProgressView()
                            .progressViewStyle(.circular)
                            .tint(.white)
                            .padding(.horizontal, 24)
                            .padding(.vertical, 12)
                            .background(appAccent)
                            .clipShape(Capsule())
                    } else {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark")
                            Text("Complete Setup")
                        }
                        .font(.body.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                        .background(appAccent)
                        .clipShape(Capsule())
                    }
                }
                .disabled(isSubmitting)
            }
        }
    }

    private var canAdvance: Bool {
        switch currentStep {
        case 0: return true           // welcome
        case 1: return true           // income planner (handled by its own buttons)
        case 2: return totalBudget > 0 // budget
        case 3: return !selectedCategoryIds.isEmpty // categories
        case 4: return true           // allocation
        case 5: return true           // exclusions (handled by its own buttons)
        case 6: return true           // review
        default: return true
        }
    }

    // MARK: - Step 1: Welcome

    private var welcomeStep: some View {
        ScrollView {
            VStack(spacing: 32) {
                Spacer().frame(height: 40)

                Image(systemName: "dollarsign.circle.fill")
                    .font(.system(size: 80))
                    .foregroundStyle(appAccent)

                VStack(spacing: 8) {
                    Text("Welcome to")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    Text("Budget Master")
                        .font(.largeTitle.bold())
                }

                VStack(alignment: .leading, spacing: 20) {
                    featureBullet(
                        icon: "message.fill",
                        title: "Chat naturally to log expenses",
                        subtitle: "Just type what you spent"
                    )
                    featureBullet(
                        icon: "chart.pie.fill",
                        title: "Track spending by category",
                        subtitle: "Visual insights at a glance"
                    )
                    featureBullet(
                        icon: "bell.badge.fill",
                        title: "Budget limit alerts",
                        subtitle: "Know when you're approaching limits"
                    )
                }
                .padding(24)
                .glassCard()
                .padding(.horizontal, 24)

                Spacer()
            }
        }
    }

    private func featureBullet(icon: String, title: String, subtitle: String) -> some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(appAccent)
                .frame(width: 40, height: 40)
                .background(appAccent.opacity(0.12))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Step 1b: Income Planner (optional)

    private var incomePlannerStep: some View {
        IncomePlannerStepView(
            onApply: { recommendedAmount in
                // Apply the calculated budget to the budget field and advance
                totalBudget = recommendedAmount
                budgetText = "\(Int(recommendedAmount))"
                withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                    currentStep = 2
                }
            },
            onSkip: {
                withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                    currentStep = 2
                }
            }
        )
    }

    // MARK: - Step 2: Total Budget

    private var budgetStep: some View {
        ScrollView {
            VStack(spacing: 28) {
                Spacer().frame(height: 24)

                VStack(spacing: 8) {
                    Text("Set Your Monthly Budget")
                        .font(.title2.bold())
                    Text("How much do you want to spend each month?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                // Large currency input
                VStack(spacing: 16) {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text("$")
                            .font(.system(size: 48, weight: .bold))
                            .foregroundStyle(appAccent)

                        TextField("0", text: $budgetText)
                            .font(.system(size: 48, weight: .bold))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.leading)
                            .onChange(of: budgetText) { _, newValue in
                                totalBudget = Double(newValue) ?? 0
                            }
                    }
                    .padding(24)
                    .glassCard()
                    .padding(.horizontal, 24)

                    // Quick-select chips
                    VStack(spacing: 8) {
                        Text("Quick select")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        HStack(spacing: 12) {
                            ForEach([1500, 2000, 3000, 5000], id: \.self) { amount in
                                Button {
                                    budgetText = "\(amount)"
                                    totalBudget = Double(amount)
                                } label: {
                                    Text("$\(amount)")
                                        .font(.subheadline.weight(.medium))
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 10)
                                        .foregroundStyle(totalBudget == Double(amount) ? .white : .primary)
                                        .background(
                                            totalBudget == Double(amount)
                                                ? AnyShapeStyle(appAccent)
                                                : AnyShapeStyle(Color(uiColor: .tertiarySystemFill)),
                                            in: Capsule()
                                        )
                                }
                            }
                        }
                    }
                }

                Spacer()
            }
        }
    }

    // MARK: - Step 3: Categories

    private var categoriesStep: some View {
        ScrollView {
            VStack(spacing: 20) {
                VStack(spacing: 8) {
                    Text("Choose Your Categories")
                        .font(.title2.bold())
                    Text("Select the spending categories you want to track")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, 24)

                if isLoadingDefaults {
                    ProgressView("Loading categories...")
                        .padding(.top, 40)
                } else {
                    let columns = [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ]

                    LazyVGrid(columns: columns, spacing: 12) {
                        ForEach(defaultCategories) { category in
                            categoryCard(category)
                        }
                    }
                    .padding(.horizontal, 24)

                    // Custom categories already added
                    ForEach(customCategories.indices, id: \.self) { index in
                        customCategoryRow(customCategories[index], at: index)
                    }
                    .padding(.horizontal, 24)

                    Button {
                        showAddCustomSheet = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "plus.circle.fill")
                            Text("Add Custom Category")
                        }
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(appAccent)
                        .padding(.vertical, 14)
                        .frame(maxWidth: .infinity)
                        .background(appAccent.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .padding(.horizontal, 24)
                }

                Spacer().frame(height: 24)
            }
        }
        .sheet(isPresented: $showAddCustomSheet) {
            AddCustomCategorySheet { custom in
                customCategories.append(custom)
            }
        }
    }

    private func categoryCard(_ category: DefaultCategory) -> some View {
        let isOther = category.categoryId.uppercased() == "OTHER"
        let isSelected = isOther || selectedCategoryIds.contains(category.categoryId)

        return Button {
            if !isOther {
                if selectedCategoryIds.contains(category.categoryId) {
                    selectedCategoryIds.remove(category.categoryId)
                    // Intentionally keep categoryCaps and categoryCapTexts values
                    // so the user's input is preserved if they re-select this category.
                    // The submission logic already filters by selectedCategoryIds.
                } else {
                    selectedCategoryIds.insert(category.categoryId)
                }
            }
        } label: {
            VStack(spacing: 8) {
                ZStack(alignment: .topTrailing) {
                    VStack(spacing: 8) {
                        Image(systemName: AppTheme.sfSymbol(for: category.icon))
                            .font(.title2)
                            .foregroundStyle(Color(hex: category.color) ?? .gray)

                        Text(category.displayName)
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.primary)
                            .lineLimit(1)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)

                    if isSelected {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.caption)
                            .foregroundStyle(appAccent)
                            .padding(6)
                    }
                }
            }
            .glassCard(cornerRadius: 14)
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isSelected ? appAccent : .clear, lineWidth: 2)
            )
            .opacity(isOther ? 0.7 : 1)
        }
        .disabled(isOther)
    }

    private func customCategoryRow(_ category: CustomCategoryInput, at index: Int) -> some View {
        HStack(spacing: 12) {
            Image(systemName: category.icon)
                .font(.title3)
                .foregroundStyle(Color(hex: category.color) ?? .gray)
                .frame(width: 36, height: 36)
                .background((Color(hex: category.color) ?? .gray).opacity(0.12))
                .clipShape(Circle())

            Text(category.displayName)
                .font(.subheadline.weight(.medium))

            Spacer()

            Button {
                customCategories.remove(at: index)
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .glassCard(cornerRadius: 12)
    }

    // MARK: - Step 4: Budget Allocation

    private var allocationStep: some View {
        ScrollView {
            VStack(spacing: 20) {
                VStack(spacing: 8) {
                    Text("Allocate Your Budget")
                        .font(.title2.bold())
                    Text("Set spending limits for each category")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 24)

                // Summary bar
                allocationSummary
                    .padding(.horizontal, 24)

                // Category cap inputs
                let selectedDefaults = defaultCategories.filter {
                    selectedCategoryIds.contains($0.categoryId)
                        && $0.categoryId.uppercased() != "OTHER"
                }

                ForEach(selectedDefaults) { category in
                    categoryCapRow(category)
                }
                .padding(.horizontal, 24)

                // Custom categories allocation
                ForEach(customCategories, id: \.displayName) { custom in
                    customCategoryCapRow(custom)
                }
                .padding(.horizontal, 24)

                // OTHER auto-fill
                otherCategoryRow
                    .padding(.horizontal, 24)

                Spacer().frame(height: 24)
            }
        }
    }

    private var allocationSummary: some View {
        let allocated = allocatedTotal
        let remaining = totalBudget - allocated
        let isOver = remaining < 0

        return VStack(spacing: 8) {
            HStack {
                Text("Total Budget")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(formatCurrency(totalBudget))
                    .font(.subheadline.weight(.semibold))
            }
            HStack {
                Text("Allocated")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(formatCurrency(allocated))
                    .font(.subheadline.weight(.semibold))
            }
            Divider()
            HStack {
                Text(isOver ? "Over Budget" : "Remaining")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(isOver ? .red : .secondary)
                Spacer()
                Text(formatCurrency(abs(remaining)))
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(isOver ? .red : appAccent)
            }

            if isOver {
                HStack(spacing: 4) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.caption)
                    Text("Category caps exceed your total budget")
                        .font(.caption)
                }
                .foregroundStyle(.red)
                .padding(.top, 4)
            }
        }
        .padding(16)
        .glassCard(cornerRadius: 14)
    }

    private func categoryCapRow(_ category: DefaultCategory) -> some View {
        let capValue = categoryCaps[category.categoryId] ?? 0
        let percentage = totalBudget > 0 ? (capValue / totalBudget) * 100 : 0

        return VStack(spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: AppTheme.sfSymbol(for: category.icon))
                    .font(.body)
                    .foregroundStyle(Color(hex: category.color) ?? .gray)
                    .frame(width: 28, height: 28)

                Text(category.displayName)
                    .font(.subheadline.weight(.medium))

                Spacer()

                HStack(spacing: 2) {
                    Text("$")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    TextField("0", text: capBinding(for: category.categoryId))
                        .font(.subheadline.weight(.semibold))
                        .keyboardType(.decimalPad)
                        .frame(width: 70)
                        .multilineTextAlignment(.trailing)
                }

                Text("\(Int(percentage))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(width: 36, alignment: .trailing)
            }

            Slider(
                value: capSliderBinding(for: category.categoryId),
                in: 0...max(totalBudget, 1)
            )
            .tint(Color(hex: category.color) ?? .gray)
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }

    private func customCategoryCapRow(_ custom: CustomCategoryInput) -> some View {
        let capValue = categoryCaps["custom_\(custom.displayName)"] ?? custom.monthlyCap
        let percentage = totalBudget > 0 ? (capValue / totalBudget) * 100 : 0

        return VStack(spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: custom.icon)
                    .font(.body)
                    .foregroundStyle(Color(hex: custom.color) ?? .gray)
                    .frame(width: 28, height: 28)

                Text(custom.displayName)
                    .font(.subheadline.weight(.medium))

                Spacer()

                HStack(spacing: 2) {
                    Text("$")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    TextField("0", text: capBinding(for: "custom_\(custom.displayName)"))
                        .font(.subheadline.weight(.semibold))
                        .keyboardType(.decimalPad)
                        .frame(width: 70)
                        .multilineTextAlignment(.trailing)
                }

                Text("\(Int(percentage))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(width: 36, alignment: .trailing)
            }

            Slider(
                value: capSliderBinding(for: "custom_\(custom.displayName)"),
                in: 0...max(totalBudget, 1)
            )
            .tint(Color(hex: custom.color) ?? .gray)
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
    }

    private var otherCategoryRow: some View {
        let otherAmount = otherAutoFill

        return HStack(spacing: 10) {
            Image(systemName: "ellipsis.circle.fill")
                .font(.body)
                .foregroundStyle(.gray)
                .frame(width: 28, height: 28)

            Text("Other")
                .font(.subheadline.weight(.medium))

            Spacer()

            Text(formatCurrency(max(otherAmount, 0)))
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)

            Text("auto")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(.secondary.opacity(0.15))
                .clipShape(Capsule())
        }
        .padding(14)
        .glassCard(cornerRadius: 14)
        .opacity(0.7)
    }

    // MARK: - Step 5b: Exclusions

    private var exclusionsStep: some View {
        ExclusionsStepView(
            selectedCategories: defaultCategories.filter {
                selectedCategoryIds.contains($0.categoryId)
            },
            excludedCategoryIds: $excludedCategoryIds,
            onContinue: {
                withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                    currentStep = 6
                }
            },
            onSkipExclusions: {
                excludedCategoryIds = []
                withAnimation(.spring(response: 0.4, dampingFraction: 0.85)) {
                    currentStep = 6
                }
            }
        )
        .onAppear {
            // Pre-populate RENT and UTILITIES if they're selected
            let rentId = defaultCategories.first(where: { $0.categoryId.uppercased() == "RENT" })?.categoryId
            let utilitiesId = defaultCategories.first(where: { $0.categoryId.uppercased() == "UTILITIES" })?.categoryId

            if let id = rentId, selectedCategoryIds.contains(id) {
                excludedCategoryIds.insert(id)
            }
            if let id = utilitiesId, selectedCategoryIds.contains(id) {
                excludedCategoryIds.insert(id)
            }
        }
    }

    // MARK: - Step 6: Review (was Step 5)

    private var reviewStep: some View {
        ScrollView {
            VStack(spacing: 20) {
                VStack(spacing: 8) {
                    Text("Review Your Setup")
                        .font(.title2.bold())
                    Text("Everything look good?")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 24)

                // Total budget card
                VStack(spacing: 4) {
                    Text("Monthly Budget")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(formatCurrency(totalBudget))
                        .font(.system(size: 36, weight: .bold))
                        .foregroundStyle(appAccent)
                }
                .frame(maxWidth: .infinity)
                .padding(20)
                .glassCard()
                .padding(.horizontal, 24)

                // Selected categories as pills
                VStack(alignment: .leading, spacing: 12) {
                    Text("Categories")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)

                    let selectedDefaults = defaultCategories.filter {
                        selectedCategoryIds.contains($0.categoryId)
                    }

                    FlowLayout(spacing: 8) {
                        ForEach(selectedDefaults) { cat in
                            HStack(spacing: 4) {
                                Image(systemName: AppTheme.sfSymbol(for: cat.icon))
                                    .font(.caption)
                                Text(cat.displayName)
                                    .font(.caption.weight(.medium))
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .foregroundStyle(Color(hex: cat.color) ?? .gray)
                            .glassCapsule()
                        }

                        // Always show OTHER
                        HStack(spacing: 4) {
                            Image(systemName: "ellipsis.circle.fill")
                                .font(.caption)
                            Text("Other")
                                .font(.caption.weight(.medium))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .foregroundStyle(.gray)
                        .glassCapsule()

                        // Custom categories
                        ForEach(customCategories, id: \.displayName) { cat in
                            HStack(spacing: 4) {
                                Image(systemName: cat.icon)
                                    .font(.caption)
                                Text(cat.displayName)
                                    .font(.caption.weight(.medium))
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .foregroundStyle(Color(hex: cat.color) ?? .gray)
                            .glassCapsule()
                        }
                    }
                }
                .padding(.horizontal, 24)

                // Budget allocations table
                VStack(spacing: 0) {
                    let selectedDefaults = defaultCategories.filter {
                        selectedCategoryIds.contains($0.categoryId)
                            && $0.categoryId.uppercased() != "OTHER"
                    }

                    ForEach(selectedDefaults) { cat in
                        reviewRow(
                            name: cat.displayName,
                            icon: AppTheme.sfSymbol(for: cat.icon),
                            color: Color(hex: cat.color) ?? .gray,
                            amount: categoryCaps[cat.categoryId] ?? 0
                        )
                    }

                    ForEach(customCategories, id: \.displayName) { cat in
                        reviewRow(
                            name: cat.displayName,
                            icon: cat.icon,
                            color: Color(hex: cat.color) ?? .gray,
                            amount: categoryCaps["custom_\(cat.displayName)"] ?? cat.monthlyCap
                        )
                    }

                    reviewRow(
                        name: "Other",
                        icon: "ellipsis.circle.fill",
                        color: .gray,
                        amount: max(otherAutoFill, 0)
                    )
                }
                .padding(4)
                .glassCard()
                .padding(.horizontal, 24)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }

                Spacer().frame(height: 24)
            }
        }
    }

    private func reviewRow(name: String, icon: String, color: Color, amount: Double) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundStyle(color)
                .frame(width: 24, height: 24)

            Text(name)
                .font(.subheadline)

            Spacer()

            Text(formatCurrency(amount))
                .font(.subheadline.weight(.medium))

            if totalBudget > 0 {
                Text("\(Int((amount / totalBudget) * 100))%")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .frame(width: 32, alignment: .trailing)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
    }

    // MARK: - Data Helpers

    private var allocatedTotal: Double {
        var total: Double = 0
        for catId in selectedCategoryIds where catId.uppercased() != "OTHER" {
            total += categoryCaps[catId] ?? 0
        }
        for custom in customCategories {
            total += categoryCaps["custom_\(custom.displayName)"] ?? custom.monthlyCap
        }
        return total
    }

    private var otherAutoFill: Double {
        totalBudget - allocatedTotal
    }

    private func capBinding(for key: String) -> Binding<String> {
        Binding(
            get: { categoryCapTexts[key] ?? "" },
            set: { newValue in
                categoryCapTexts[key] = newValue
                categoryCaps[key] = Double(newValue) ?? 0
            }
        )
    }

    private func capSliderBinding(for key: String) -> Binding<Double> {
        Binding(
            get: { categoryCaps[key] ?? 0 },
            set: { newValue in
                let rounded = (newValue / 10).rounded() * 10
                categoryCaps[key] = rounded
                categoryCapTexts[key] = "\(Int(rounded))"
            }
        )
    }

    private func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$\(Int(value))"
    }

    // MARK: - Network

    private func loadDefaults() async {
        isLoadingDefaults = true
        do {
            let response = try await CategoryService.getDefaults()
            defaultCategories = response.defaults
            // Auto-select OTHER
            if let other = defaultCategories.first(where: { $0.categoryId.uppercased() == "OTHER" }) {
                selectedCategoryIds.insert(other.categoryId)
            }
        } catch {
            errorMessage = "Failed to load categories: \(error.localizedDescription)"
        }
        isLoadingDefaults = false
    }

    private func completeOnboarding() async {
        isSubmitting = true
        errorMessage = nil

        // Build caps dictionary for the API
        var caps: [String: Double] = [:]
        for catId in selectedCategoryIds where catId.uppercased() != "OTHER" {
            caps[catId] = categoryCaps[catId] ?? 0
        }

        // Update custom category caps from the allocation step
        let customInputs: [CustomCategoryInput] = customCategories.map { custom in
            let cap = categoryCaps["custom_\(custom.displayName)"] ?? custom.monthlyCap
            return CustomCategoryInput(
                displayName: custom.displayName,
                icon: custom.icon,
                color: custom.color,
                monthlyCap: cap
            )
        }

        let request = OnboardingCompleteRequest(
            totalBudget: totalBudget,
            selectedCategoryIds: Array(selectedCategoryIds),
            categoryCaps: caps,
            customCategories: customInputs.isEmpty ? nil : customInputs,
            excludedCategoryIds: excludedCategoryIds.isEmpty ? nil : Array(excludedCategoryIds)
        )

        do {
            let _ = try await CategoryService.completeOnboarding(request)
            await MainActor.run {
                onComplete()
            }
        } catch {
            errorMessage = "Setup failed: \(error.localizedDescription)"
        }

        isSubmitting = false
    }
}

// MARK: - FlowLayout

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = arrange(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = arrange(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y),
                proposal: .unspecified
            )
        }
    }

    private func arrange(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var currentX: CGFloat = 0
        var currentY: CGFloat = 0
        var lineHeight: CGFloat = 0
        var maxX: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX + size.width > maxWidth, currentX > 0 {
                currentX = 0
                currentY += lineHeight + spacing
                lineHeight = 0
            }
            positions.append(CGPoint(x: currentX, y: currentY))
            lineHeight = max(lineHeight, size.height)
            currentX += size.width + spacing
            maxX = max(maxX, currentX - spacing)
        }

        return (CGSize(width: maxX, height: currentY + lineHeight), positions)
    }
}

// MARK: - Add Custom Category Sheet

struct AddCustomCategorySheet: View {
    let onAdd: (CustomCategoryInput) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var selectedIcon = "creditcard.fill"
    @State private var selectedColor = "#6366f1"
    @State private var capText = ""

    private let availableIcons = [
        "fork.knife", "cup.and.saucer.fill", "cart.fill", "car.fill",
        "fuelpump.fill", "house.fill", "heart.fill", "airplane",
        "laptopcomputer", "building.2.fill", "bolt.fill", "creditcard.fill",
        "headphones", "bag.fill", "dumbbell.fill", "book.fill",
        "wifi", "gift.fill", "gamecontroller.fill", "camera.fill",
        "paintbrush.fill", "wrench.fill", "leaf.fill", "star.fill"
    ]

    private let availableColors = [
        "#ef4444", "#f97316", "#eab308", "#22c55e",
        "#14b8a6", "#06b6d4", "#3b82f6", "#6366f1",
        "#8b5cf6", "#a855f7", "#ec4899", "#f43f5e",
        "#a16038", "#64748b"
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Preview
                    VStack(spacing: 8) {
                        Image(systemName: selectedIcon)
                            .font(.largeTitle)
                            .foregroundStyle(Color(hex: selectedColor) ?? .gray)
                        Text(name.isEmpty ? "Category Name" : name)
                            .font(.headline)
                            .foregroundStyle(name.isEmpty ? .secondary : .primary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(24)
                    .glassCard()
                    .padding(.horizontal, 24)

                    // Name
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Name")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)
                        TextField("Category name", text: $name)
                            .padding(14)
                            .background(.secondary.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Monthly Cap
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Monthly Cap")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Text("$")
                                .foregroundStyle(.secondary)
                            TextField("0", text: $capText)
                                .keyboardType(.decimalPad)
                        }
                        .padding(14)
                        .background(.secondary.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Icon picker
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Icon")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)

                        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 6), spacing: 8) {
                            ForEach(availableIcons, id: \.self) { icon in
                                Button {
                                    selectedIcon = icon
                                } label: {
                                    Image(systemName: icon)
                                        .font(.title3)
                                        .frame(width: 44, height: 44)
                                        .foregroundStyle(
                                            selectedIcon == icon
                                                ? Color.white
                                                : (Color(hex: selectedColor) ?? .gray)
                                        )
                                        .background(
                                            selectedIcon == icon
                                                ? (Color(hex: selectedColor) ?? .gray)
                                                : Color.secondary.opacity(0.1)
                                        )
                                        .clipShape(RoundedRectangle(cornerRadius: 10))
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 24)

                    // Color picker
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Color")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)

                        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 7), spacing: 8) {
                            ForEach(availableColors, id: \.self) { color in
                                Button {
                                    selectedColor = color
                                } label: {
                                    Circle()
                                        .fill(Color(hex: color) ?? .gray)
                                        .frame(width: 36, height: 36)
                                        .overlay(
                                            Circle()
                                                .stroke(Color.white, lineWidth: selectedColor == color ? 3 : 0)
                                        )
                                        .overlay(
                                            Circle()
                                                .stroke(Color(hex: color) ?? .gray, lineWidth: selectedColor == color ? 1 : 0)
                                                .padding(3)
                                        )
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 24)

                    Spacer().frame(height: 24)
                }
            }
            .navigationTitle("Add Category")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        let cap = Double(capText) ?? 0
                        let custom = CustomCategoryInput(
                            displayName: name,
                            icon: selectedIcon,
                            color: selectedColor,
                            monthlyCap: cap
                        )
                        onAdd(custom)
                        dismiss()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
