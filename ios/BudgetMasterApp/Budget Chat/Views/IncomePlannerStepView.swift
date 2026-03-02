import SwiftUI

// MARK: - IncomePlannerStepView

/// A self-contained multi-screen income planner.
/// None of the user's financial inputs are persisted — only the final
/// recommended budget amount surfaces as the `onApply` callback value.
struct IncomePlannerStepView: View {

    let onApply: (Double) -> Void
    let onSkip: () -> Void

    @Environment(\.appAccent) private var appAccent

    // MARK: - Internal Screen State

    private enum Screen: Int, CaseIterable {
        case modeSelect
        case incomeInput
        case savingsRate
        case result
    }

    @State private var screen: Screen = .modeSelect
    @State private var input = BudgetCalcInput()
    @State private var result: BudgetCalcResult?

    // MARK: - Body

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                privacyNotice
                    .padding(.horizontal, 24)
                    .padding(.top, 16)

                switch screen {
                case .modeSelect:
                    modeSelectContent
                case .incomeInput:
                    incomeInputContent
                case .savingsRate:
                    savingsRateContent
                case .result:
                    resultContent
                }
            }
            .animation(.spring(response: 0.35, dampingFraction: 0.85), value: screen)
            .dismissKeyboardOnTap()
        }
        .scrollDismissesKeyboard(.interactively)
    }

    // MARK: - Privacy Notice

    private var privacyNotice: some View {
        HStack(spacing: 10) {
            Image(systemName: "lock.fill")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("None of this information is saved — it is used only to calculate your recommendation.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(uiColor: .secondarySystemBackground).opacity(0.8))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Screen 1: Mode Select

    private var modeSelectContent: some View {
        VStack(spacing: 16) {
            VStack(spacing: 6) {
                Text("How would you like to set your budget?")
                    .font(.title3.bold())
                    .multilineTextAlignment(.center)
                Text("Choose the method that works best for you.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 24)

            modeCard(
                icon: "arrow.down.to.line",
                title: "I know my take-home",
                subtitle: "Enter your net pay per paycheck",
                mode: .directDeposit
            )
            .padding(.horizontal, 24)

            modeCard(
                icon: "building.columns",
                title: "Calculate from salary",
                subtitle: "Enter gross pay, taxes will be estimated",
                mode: .salary
            )
            .padding(.horizontal, 24)

            manualEntryCard
                .padding(.horizontal, 24)
        }
    }

    private var manualEntryCard: some View {
        Button {
            onSkip()
        } label: {
            HStack(spacing: 16) {
                Image(systemName: "pencil")
                    .font(.title2)
                    .foregroundStyle(appAccent)
                    .frame(width: 48, height: 48)
                    .background(appAccent.opacity(0.12))
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 4) {
                    Text("Enter budget manually")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text("Set a specific monthly amount directly")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(20)
            .glassCard(cornerRadius: 16)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Enter budget manually")
        .accessibilityHint("Set a specific monthly amount directly")
    }

    private func modeCard(icon: String, title: String, subtitle: String, mode: IncomeMode) -> some View {
        Button {
            input.mode = mode
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                screen = .incomeInput
            }
        } label: {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(appAccent)
                    .frame(width: 48, height: 48)
                    .background(appAccent.opacity(0.12))
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(20)
            .glassCard(cornerRadius: 16)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityHint(subtitle)
    }

    // MARK: - Screen 2: Income Input

    @ViewBuilder
    private var incomeInputContent: some View {
        if input.mode == .directDeposit {
            directDepositInput
        } else {
            salaryInput
        }
    }

    private var directDepositInput: some View {
        VStack(spacing: 20) {
            VStack(spacing: 6) {
                Text("Your Take-Home Pay")
                    .font(.title3.bold())
                Text("Enter the amount that hits your account each pay period.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                currencyField(
                    label: "Take-home amount",
                    value: $input.takeHome
                )
                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 28)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                Picker("Pay frequency", selection: $input.frequency) {
                    ForEach(PayFrequency.allCases) { freq in
                        Text(freq.rawValue).tag(freq)
                    }
                }
                .pickerStyle(.segmented)
                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.horizontal, 24)

            advanceButton(label: "Continue", enabled: input.takeHome > 0)

            Button {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) { screen = .modeSelect }
            } label: {
                Text("Back")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 8)
        }
    }

    private var salaryInput: some View {
        VStack(spacing: 20) {
            VStack(spacing: 6) {
                Text("Your Salary Details")
                    .font(.title3.bold())
                Text("We will estimate taxes based on these figures.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                currencyField(label: "Gross annual salary", value: $input.grossAnnual)
                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 28)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                Picker("State", selection: $input.stateCode) {
                    ForEach(allUSStates) { state in
                        Text(state.name).tag(state.code)
                    }
                }
                .pickerStyle(.menu)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .glassCard(cornerRadius: 14)

                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                HStack {
                    Text("401k contribution")
                        .font(.subheadline)
                    Spacer()
                    Text("\(Int(input.retirement401kPct))%")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(appAccent)
                }
                Slider(value: $input.retirement401kPct, in: 0...30, step: 1)
                    .tint(appAccent)
                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 4) {
                currencyField(label: "Other pre-tax deductions per month (optional)", value: $input.monthlyHealthcare)
                Text("e.g., medical, dental, parking, FSA")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 28)
                Text("Not stored")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 28)
            }
            .padding(.horizontal, 24)

            advanceButton(label: "Continue", enabled: input.grossAnnual > 0)

            Button {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) { screen = .modeSelect }
            } label: {
                Text("Back")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 8)
        }
    }

    // MARK: - Screen 3: Savings Rate

    private var savingsRateContent: some View {
        VStack(spacing: 24) {
            VStack(spacing: 6) {
                Text("How much do you want to save?")
                    .font(.title3.bold())
                    .multilineTextAlignment(.center)
                Text("This portion of your take-home will be reserved before your spending budget is calculated.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 24)

            VStack(spacing: 16) {
                Text("\(Int(input.savingsRate))%")
                    .font(.system(size: 56, weight: .bold))
                    .foregroundStyle(appAccent)
                    .contentTransition(.numericText())
                    .animation(.spring(response: 0.25), value: input.savingsRate)

                Slider(value: $input.savingsRate, in: 5...50, step: 5)
                    .tint(appAccent)
                    .padding(.horizontal, 24)

                HStack {
                    Text("5%")
                    Spacer()
                    Text("50%")
                }
                .font(.caption)
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 28)
            }
            .padding(.horizontal, 24)

            advanceButton(label: "See My Budget", enabled: true)

            Button {
                withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) { screen = .incomeInput }
            } label: {
                Text("Back")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 8)
        }
    }

    // MARK: - Screen 4: Result

    private var resultContent: some View {
        let calc = BudgetCalculator.calculateBudget(input: input)

        return VStack(spacing: 24) {
            VStack(spacing: 6) {
                Text("Recommended Monthly Budget")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Text(calc.recommendedMonthlyBudget, format: .currency(code: "USD"))
                    .font(.system(size: 52, weight: .bold))
                    .foregroundStyle(appAccent)
            }
            .frame(maxWidth: .infinity)
            .padding(24)
            .glassCard()
            .padding(.horizontal, 24)

            if let breakdown = calc.breakdown {
                breakdownSection(breakdown)
                    .padding(.horizontal, 24)
            }

            // Privacy reminder
            HStack(spacing: 8) {
                Image(systemName: "info.circle")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("Only the final budget amount you choose to apply will be saved. Your income, deductions, and savings rate are discarded immediately.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(12)
            .background(Color(uiColor: .secondarySystemBackground).opacity(0.7))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .padding(.horizontal, 24)

            // Primary action
            Button {
                onApply(calc.recommendedMonthlyBudget)
            } label: {
                Text("Use This as My Budget")
                    .font(.body.weight(.semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(appAccent)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .padding(.horizontal, 24)
            .accessibilityLabel("Use this as my monthly budget")

            Button {
                onSkip()
            } label: {
                Text("Skip")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 8)
        }
    }

    private func breakdownSection(_ b: BudgetBreakdown) -> some View {
        VStack(spacing: 0) {
            breakdownRow(label: "Gross Annual", value: b.grossAnnual, isBold: false)
            Divider().padding(.leading, 16)
            breakdownRow(label: "401k Contribution", value: -b.retirement401k, isBold: false, isDeduction: true)
            Divider().padding(.leading, 16)
            breakdownRow(label: "Healthcare", value: -b.healthcare, isBold: false, isDeduction: true)
            Divider().padding(.leading, 16)
            breakdownRow(label: "Federal Tax", value: -b.federalTax, isBold: false, isDeduction: true)
            Divider().padding(.leading, 16)
            breakdownRow(label: "State Tax", value: -b.stateTax, isBold: false, isDeduction: true)
            Divider().padding(.leading, 16)
            breakdownRow(label: "FICA", value: -b.fica, isBold: false, isDeduction: true)
            Divider()
            breakdownRow(label: "Annual Take-Home", value: b.netAnnual, isBold: true)
            Divider().padding(.leading, 16)
            breakdownRow(label: "Savings (\(Int(input.savingsRate))%)", value: -b.savingsAmount, isBold: false, isDeduction: true)
        }
        .glassCard(cornerRadius: 16)
    }

    private func breakdownRow(label: String, value: Double, isBold: Bool, isDeduction: Bool = false) -> some View {
        HStack {
            Text(label)
                .font(isBold ? .subheadline.weight(.semibold) : .subheadline)
            Spacer()
            Text(abs(value), format: .currency(code: "USD"))
                .font(isBold ? .subheadline.weight(.semibold) : .subheadline)
                .foregroundStyle(isDeduction ? .red : (isBold ? appAccent : .primary))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Shared Helpers

    /// Currency text field that drives a Double binding.
    private func currencyField(label: String, value: Binding<Double>) -> some View {
        // Use a string proxy so the keyboard shows numeric input naturally
        let proxy = Binding<String>(
            get: { value.wrappedValue > 0 ? String(format: "%.0f", value.wrappedValue) : "" },
            set: { value.wrappedValue = Double($0) ?? 0 }
        )
        return HStack(spacing: 4) {
            Text("$")
                .font(.title3.weight(.semibold))
                .foregroundStyle(.secondary)
            TextField("0", text: proxy)
                .keyboardType(.numberPad)
                .font(.title3.weight(.semibold))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .glassCard(cornerRadius: 14)
        .accessibilityLabel(label)
    }

    private func advanceButton(label: String, enabled: Bool) -> some View {
        Button {
            let next = nextScreen(from: screen)
            withAnimation(.spring(response: 0.35, dampingFraction: 0.85)) {
                screen = next
            }
        } label: {
            HStack(spacing: 6) {
                Text(label)
                Image(systemName: "chevron.right")
            }
            .font(.body.weight(.semibold))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(enabled ? appAccent : Color(uiColor: .systemGray3))
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .disabled(!enabled)
        .padding(.horizontal, 24)
    }

    private func nextScreen(from current: Screen) -> Screen {
        switch current {
        case .modeSelect:   return .incomeInput
        case .incomeInput:  return .savingsRate
        case .savingsRate:  return .result
        case .result:       return .result
        }
    }
}
