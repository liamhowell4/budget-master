import Foundation

// MARK: - PayFrequency

public enum PayFrequency: String, CaseIterable, Identifiable {
    case weekly = "Weekly"
    case biweekly = "Biweekly"
    case semimonthly = "Semi-monthly"
    case monthly = "Monthly"

    public var id: String { rawValue }

    public var periodsPerYear: Double {
        switch self {
        case .weekly:      return 52
        case .biweekly:    return 26
        case .semimonthly: return 24
        case .monthly:     return 12
        }
    }
}

// MARK: - IncomeMode

public enum IncomeMode: String, CaseIterable {
    case directDeposit = "I know my take-home"
    case salary = "Calculate from salary"
}

// MARK: - BudgetCalcInput

public struct BudgetCalcInput {
    public var mode: IncomeMode = .directDeposit
    // Direct deposit fields
    public var takeHome: Double = 0
    public var frequency: PayFrequency = .biweekly
    // Salary fields
    public var grossAnnual: Double = 0
    public var stateCode: String = "CA"
    public var retirement401kPct: Double = 0    // 0–100
    public var monthlyHealthcare: Double = 0
    // Shared
    public var savingsRate: Double = 20         // 0–100

    public init() {}
}

// MARK: - BudgetCalcResult

public struct BudgetCalcResult {
    public let recommendedMonthlyBudget: Double
    public let breakdown: BudgetBreakdown?
}

// MARK: - BudgetBreakdown

public struct BudgetBreakdown {
    public let grossAnnual: Double
    public let retirement401k: Double
    public let healthcare: Double
    public let federalTax: Double
    public let stateTax: Double
    public let fica: Double
    public let netAnnual: Double
    public let savingsAmount: Double
}

// MARK: - BudgetCalculator

public struct BudgetCalculator {

    // MARK: State Tax Rates (2025 Tax Foundation data, effective rate estimates)

    /// Flat or estimated effective marginal rates for all 50 states + DC.
    /// No-income-tax states are 0.0.
    private static let stateTaxRates: [String: Double] = [
        // No-income-tax states
        "AK": 0.000,
        "FL": 0.000,
        "NV": 0.000,
        "NH": 0.000,
        "SD": 0.000,
        "TN": 0.000,
        "TX": 0.000,
        "WA": 0.000,
        "WY": 0.000,
        // Flat-tax states
        "IL": 0.0495,
        "PA": 0.0307,
        "IN": 0.0300,
        "KY": 0.0400,
        "CO": 0.0440,
        "MI": 0.0425,
        "UT": 0.0465,
        "NC": 0.0475,
        // Progressive states — estimated effective rates at moderate income
        "CA": 0.0930,
        "NY": 0.0685,
        "OR": 0.0990,
        "MN": 0.0785,
        "HI": 0.0820,
        "NJ": 0.0637,
        "VT": 0.0660,
        "DC": 0.0850,
        "ME": 0.0715,
        "SC": 0.0700,
        "CT": 0.0699,
        "WI": 0.0765,
        "ID": 0.0580,
        "MT": 0.0590,
        "NE": 0.0664,
        "ND": 0.0290,
        "RI": 0.0599,
        "MA": 0.0500,
        "OH": 0.0399,
        "GA": 0.0550,
        "VA": 0.0575,
        "MD": 0.0575,
        "AL": 0.0500,
        "MS": 0.0500,
        "LA": 0.0425,
        "AR": 0.0490,
        "MO": 0.0495,
        "KS": 0.0570,
        "OK": 0.0475,
        "AZ": 0.0250,
        "NM": 0.0490,
        "WV": 0.0650,
        "DE": 0.0660,
        "IA": 0.0600,
    ]

    // MARK: Federal Tax Brackets (2025, single filer, marginal)

    // Brackets are (upper bound, rate). The last bracket has no upper bound
    // (represented by .infinity).
    private static let federalBrackets: [(Double, Double)] = [
        (11600,    0.10),
        (47150,    0.12),
        (100525,   0.22),
        (191950,   0.24),
        (243725,   0.32),
        (609350,   0.35),
        (.infinity, 0.37),
    ]

    // MARK: Constants

    /// 2025 Social Security wage base
    private static let ssWageBase: Double = 176_100
    /// 2025 standard deduction for single filers
    private static let standardDeduction: Double = 14_600

    // MARK: Public API

    public static func calculateBudget(input: BudgetCalcInput) -> BudgetCalcResult {
        switch input.mode {
        case .directDeposit:
            return calculateDirectDeposit(input: input)
        case .salary:
            return calculateFromSalary(input: input)
        }
    }

    // MARK: - Direct Deposit Path

    private static func calculateDirectDeposit(input: BudgetCalcInput) -> BudgetCalcResult {
        let annualTakeHome = input.takeHome * input.frequency.periodsPerYear
        let monthlyNet = annualTakeHome / 12.0
        let monthlyBudget = monthlyNet * (1.0 - input.savingsRate / 100.0)
        return BudgetCalcResult(recommendedMonthlyBudget: monthlyBudget, breakdown: nil)
    }

    // MARK: - Salary Path

    private static func calculateFromSalary(input: BudgetCalcInput) -> BudgetCalcResult {
        let gross = input.grossAnnual

        // Pre-tax deductions
        let retirement401k = gross * (input.retirement401kPct / 100.0)
        let healthcareAnnual = input.monthlyHealthcare * 12.0

        // Taxable income for federal purposes
        let taxableIncome = max(0, gross - retirement401k - healthcareAnnual - standardDeduction)

        // Federal tax via marginal brackets
        let federalTax = marginalTax(on: taxableIncome, brackets: federalBrackets)

        // State tax (flat effective rate on gross income, approximation)
        let stateRate = stateTaxRates[input.stateCode.uppercased()] ?? 0.05
        let stateTax = gross * stateRate

        // FICA: Social Security (6.2% up to wage base) + Medicare (1.45% uncapped)
        let fica = min(gross, ssWageBase) * 0.062 + gross * 0.0145

        // Net annual take-home
        let netAnnual = gross - retirement401k - healthcareAnnual - federalTax - stateTax - fica

        // Monthly spendable after savings
        let monthlyNet = netAnnual / 12.0
        let savingsAmount = monthlyNet * (input.savingsRate / 100.0)
        let monthlyBudget = monthlyNet * (1.0 - input.savingsRate / 100.0)

        let breakdown = BudgetBreakdown(
            grossAnnual: gross,
            retirement401k: retirement401k,
            healthcare: healthcareAnnual,
            federalTax: federalTax,
            stateTax: stateTax,
            fica: fica,
            netAnnual: max(0, netAnnual),
            savingsAmount: savingsAmount
        )

        return BudgetCalcResult(
            recommendedMonthlyBudget: max(0, monthlyBudget),
            breakdown: breakdown
        )
    }

    // MARK: - Tax Helpers

    private static func marginalTax(on income: Double, brackets: [(Double, Double)]) -> Double {
        var tax: Double = 0
        var previousBound: Double = 0

        for (upperBound, rate) in brackets {
            if income <= previousBound { break }
            let taxableInBracket = min(income, upperBound) - previousBound
            tax += taxableInBracket * rate
            previousBound = upperBound
        }

        return tax
    }
}

// MARK: - US States List (for picker)

public struct USState: Identifiable {
    public let code: String
    public let name: String
    public var id: String { code }
}

public let allUSStates: [USState] = [
    USState(code: "AL", name: "Alabama"),
    USState(code: "AK", name: "Alaska"),
    USState(code: "AZ", name: "Arizona"),
    USState(code: "AR", name: "Arkansas"),
    USState(code: "CA", name: "California"),
    USState(code: "CO", name: "Colorado"),
    USState(code: "CT", name: "Connecticut"),
    USState(code: "DC", name: "Washington D.C."),
    USState(code: "DE", name: "Delaware"),
    USState(code: "FL", name: "Florida"),
    USState(code: "GA", name: "Georgia"),
    USState(code: "HI", name: "Hawaii"),
    USState(code: "ID", name: "Idaho"),
    USState(code: "IL", name: "Illinois"),
    USState(code: "IN", name: "Indiana"),
    USState(code: "IA", name: "Iowa"),
    USState(code: "KS", name: "Kansas"),
    USState(code: "KY", name: "Kentucky"),
    USState(code: "LA", name: "Louisiana"),
    USState(code: "ME", name: "Maine"),
    USState(code: "MD", name: "Maryland"),
    USState(code: "MA", name: "Massachusetts"),
    USState(code: "MI", name: "Michigan"),
    USState(code: "MN", name: "Minnesota"),
    USState(code: "MS", name: "Mississippi"),
    USState(code: "MO", name: "Missouri"),
    USState(code: "MT", name: "Montana"),
    USState(code: "NE", name: "Nebraska"),
    USState(code: "NV", name: "Nevada"),
    USState(code: "NH", name: "New Hampshire"),
    USState(code: "NJ", name: "New Jersey"),
    USState(code: "NM", name: "New Mexico"),
    USState(code: "NY", name: "New York"),
    USState(code: "NC", name: "North Carolina"),
    USState(code: "ND", name: "North Dakota"),
    USState(code: "OH", name: "Ohio"),
    USState(code: "OK", name: "Oklahoma"),
    USState(code: "OR", name: "Oregon"),
    USState(code: "PA", name: "Pennsylvania"),
    USState(code: "RI", name: "Rhode Island"),
    USState(code: "SC", name: "South Carolina"),
    USState(code: "SD", name: "South Dakota"),
    USState(code: "TN", name: "Tennessee"),
    USState(code: "TX", name: "Texas"),
    USState(code: "UT", name: "Utah"),
    USState(code: "VT", name: "Vermont"),
    USState(code: "VA", name: "Virginia"),
    USState(code: "WA", name: "Washington"),
    USState(code: "WV", name: "West Virginia"),
    USState(code: "WI", name: "Wisconsin"),
    USState(code: "WY", name: "Wyoming"),
]
