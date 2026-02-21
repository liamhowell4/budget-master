import SwiftUI
import BudgetMaster

struct CategoriesTab: View {
    @StateObject private var viewModel = CategoriesViewModel()
    @Environment(\.appAccent) private var appAccent
    @State private var showAddSheet = false
    @State private var editingCategory: ExpenseCategory?
    @State private var deletingCategory: ExpenseCategory?
    @State private var reassignTarget: String = "OTHER"

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Total budget card
                totalBudgetCard

                // Categories list
                categoriesList

                // Add category button
                addCategoryButton
            }
            .padding()
        }
        .task {
            await viewModel.loadData()
        }
        .sheet(isPresented: $showAddSheet) {
            AddCategorySheet { request in
                Task {
                    await viewModel.createCategory(request)
                }
            }
        }
        .sheet(item: $editingCategory) { category in
            EditCategorySheet(category: category) { id, update in
                Task {
                    await viewModel.updateCategory(id: id, update: update)
                    editingCategory = nil
                }
            }
        }
        .alert("Delete Category", isPresented: showDeleteBinding) {
            if viewModel.categories.count > 1 {
                Picker("Reassign expenses to", selection: $reassignTarget) {
                    ForEach(reassignOptions, id: \.categoryId) { cat in
                        Text(cat.displayName).tag(cat.categoryId)
                    }
                }
            }
            Button("Delete", role: .destructive) {
                if let cat = deletingCategory {
                    Task {
                        await viewModel.deleteCategory(
                            id: cat.categoryId,
                            reassignTo: reassignTarget
                        )
                        deletingCategory = nil
                    }
                }
            }
            Button("Cancel", role: .cancel) {
                deletingCategory = nil
            }
        } message: {
            if let cat = deletingCategory {
                Text("Expenses in \"\(cat.displayName)\" will be reassigned to another category.")
            }
        }
        .overlay {
            if viewModel.isLoading && viewModel.categories.isEmpty {
                ProgressView()
            } else if let error = viewModel.errorMessage, viewModel.categories.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text(error)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                    Button("Retry") {
                        Task { await viewModel.loadData() }
                    }
                    .font(.subheadline.weight(.medium))
                }
                .padding()
            }
        }
    }

    private var showDeleteBinding: Binding<Bool> {
        Binding(
            get: { deletingCategory != nil },
            set: { if !$0 { deletingCategory = nil } }
        )
    }

    private var reassignOptions: [ExpenseCategory] {
        viewModel.categories.filter { $0.categoryId != deletingCategory?.categoryId }
    }

    // MARK: - Total Budget Card

    private var totalBudgetCard: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Total Monthly Budget")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    if viewModel.isEditingBudget {
                        HStack(spacing: 4) {
                            Text("$")
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundStyle(appAccent)
                            TextField("0", text: $viewModel.totalBudgetText)
                                .font(.title2)
                                .fontWeight(.bold)
                                .keyboardType(.decimalPad)
                                .frame(width: 120)
                        }
                    } else {
                        Text(viewModel.totalBudget, format: .currency(code: "USD"))
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundStyle(appAccent)
                    }
                }

                Spacer()

                if viewModel.isEditingBudget {
                    HStack(spacing: 8) {
                        Button {
                            viewModel.cancelBudgetEdit()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title3)
                                .foregroundStyle(.secondary)
                        }

                        Button {
                            Task { await viewModel.saveTotalBudget() }
                        } label: {
                            if viewModel.isSavingBudget {
                                ProgressView()
                                    .progressViewStyle(.circular)
                            } else {
                                Image(systemName: "checkmark.circle.fill")
                                    .font(.title3)
                                    .foregroundStyle(appAccent)
                            }
                        }
                        .disabled(viewModel.isSavingBudget)
                    }
                } else {
                    Button {
                        viewModel.startBudgetEdit()
                    } label: {
                        Image(systemName: "pencil.circle.fill")
                            .font(.title3)
                            .foregroundStyle(appAccent)
                    }
                }
            }

            if !viewModel.categories.isEmpty {
                let allocated = viewModel.categories.reduce(0.0) { $0 + $1.monthlyCap }
                let remaining = viewModel.totalBudget - allocated

                HStack {
                    Text("Allocated: \(allocated.formatted(.currency(code: "USD")))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("Remaining: \(remaining.formatted(.currency(code: "USD")))")
                        .font(.caption)
                        .foregroundStyle(remaining < 0 ? .red : .secondary)
                }
            }
        }
        .padding()
        .glassCard()
    }

    // MARK: - Categories List

    private var categoriesList: some View {
        VStack(spacing: 0) {
            ForEach(viewModel.categories) { category in
                categoryRow(category)

                if category.id != viewModel.categories.last?.id {
                    Divider()
                        .padding(.leading, 56)
                }
            }
        }
        .glassCard()
    }

    private func categoryRow(_ category: ExpenseCategory) -> some View {
        HStack(spacing: 12) {
            // Icon
            Image(systemName: AppTheme.sfSymbol(for: category.icon))
                .font(.body)
                .foregroundStyle(Color(hex: category.color) ?? .gray)
                .frame(width: 36, height: 36)
                .background((Color(hex: category.color) ?? .gray).opacity(0.12))
                .clipShape(RoundedRectangle(cornerRadius: 8))

            // Name and budget
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(category.displayName)
                        .font(.subheadline)
                        .fontWeight(.medium)

                    if category.excludeFromTotal {
                        Text("excluded")
                            .font(.caption2)
                            .foregroundStyle(.orange)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(.orange.opacity(0.12))
                            .clipShape(Capsule())
                    }
                }

                Text(category.monthlyCap.formatted(.currency(code: "USD")))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // Actions
            if !category.isSystem {
                Menu {
                    Button {
                        editingCategory = category
                    } label: {
                        Label("Edit", systemImage: "pencil")
                    }

                    Button(role: .destructive) {
                        reassignTarget = "OTHER"
                        deletingCategory = category
                    } label: {
                        Label("Delete", systemImage: "trash")
                    }
                } label: {
                    Image(systemName: "ellipsis")
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .frame(width: 32, height: 32)
                }
            } else {
                Button {
                    editingCategory = category
                } label: {
                    Image(systemName: "pencil")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(width: 32, height: 32)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    // MARK: - Add Category Button

    private var addCategoryButton: some View {
        Button {
            showAddSheet = true
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "plus.circle.fill")
                Text("Add Category")
            }
            .font(.subheadline.weight(.medium))
            .foregroundStyle(appAccent)
            .padding(.vertical, 14)
            .frame(maxWidth: .infinity)
            .background(appAccent.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
    }
}

// MARK: - View Model

@MainActor
class CategoriesViewModel: ObservableObject {
    @Published var categories: [ExpenseCategory] = []
    @Published var totalBudget: Double = 0
    @Published var isLoading = false
    @Published var errorMessage: String?

    @Published var isEditingBudget = false
    @Published var totalBudgetText = ""
    @Published var isSavingBudget = false

    func loadData() async {
        isLoading = true
        do {
            let response = try await CategoryService.getCategories()
            categories = response.categories.sorted { $0.sortOrder < $1.sortOrder }
            totalBudget = response.totalMonthlyBudget
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func createCategory(_ request: CategoryCreateRequest) async {
        do {
            let _ = try await CategoryService.createCategory(request)
            await loadData()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func updateCategory(id: String, update: CategoryUpdateRequest) async {
        do {
            let _ = try await CategoryService.updateCategory(id: id, update: update)
            await loadData()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deleteCategory(id: String, reassignTo: String) async {
        do {
            let _ = try await CategoryService.deleteCategory(id: id, reassignTo: reassignTo)
            await loadData()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func startBudgetEdit() {
        totalBudgetText = String(Int(totalBudget))
        isEditingBudget = true
    }

    func cancelBudgetEdit() {
        isEditingBudget = false
        totalBudgetText = ""
    }

    func saveTotalBudget() async {
        guard let newBudget = Double(totalBudgetText), newBudget > 0 else { return }
        isSavingBudget = true
        do {
            let _ = try await BudgetService.updateTotalBudget(newBudget)
            totalBudget = newBudget
            isEditingBudget = false
        } catch {
            errorMessage = error.localizedDescription
        }
        isSavingBudget = false
    }
}

// MARK: - Add Category Sheet

struct AddCategorySheet: View {
    let onAdd: (CategoryCreateRequest) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var selectedIcon = "creditcard.fill"
    @State private var selectedColor = "#6366f1"
    @State private var capText = ""

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
                            .background(Color(uiColor: .secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Monthly Cap
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Monthly Budget")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Text("$")
                                .foregroundStyle(.secondary)
                            TextField("0", text: $capText)
                                .keyboardType(.decimalPad)
                        }
                        .padding(14)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Icon picker
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Icon")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)

                        IconPicker(
                            selectedIcon: $selectedIcon,
                            accentColor: Color(hex: selectedColor) ?? .gray
                        )
                    }
                    .padding(.horizontal, 24)

                    // Color picker
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Color")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)

                        ColorPalettePicker(selectedColor: $selectedColor)
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
                        let request = CategoryCreateRequest(
                            displayName: name,
                            icon: selectedIcon,
                            color: selectedColor,
                            monthlyCap: cap
                        )
                        onAdd(request)
                        dismiss()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

// MARK: - Edit Category Sheet

struct EditCategorySheet: View {
    let category: ExpenseCategory
    let onSave: (String, CategoryUpdateRequest) -> Void

    @Environment(\.dismiss) private var dismiss
    @Environment(\.appAccent) private var appAccent
    @State private var name: String
    @State private var selectedIcon: String
    @State private var selectedColor: String
    @State private var capText: String
    @State private var excludeFromTotal: Bool

    init(category: ExpenseCategory, onSave: @escaping (String, CategoryUpdateRequest) -> Void) {
        self.category = category
        self.onSave = onSave
        _name = State(initialValue: category.displayName)
        _selectedIcon = State(initialValue: category.icon)
        _selectedColor = State(initialValue: category.color)
        _capText = State(initialValue: String(Int(category.monthlyCap)))
        _excludeFromTotal = State(initialValue: category.excludeFromTotal)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Preview
                    VStack(spacing: 8) {
                        Image(systemName: AppTheme.sfSymbol(for: selectedIcon))
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
                            .background(Color(uiColor: .secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Monthly Cap
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Monthly Budget")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.secondary)
                        HStack(spacing: 4) {
                            Text("$")
                                .foregroundStyle(.secondary)
                            TextField("0", text: $capText)
                                .keyboardType(.decimalPad)
                        }
                        .padding(14)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                    .padding(.horizontal, 24)

                    // Exclude from total toggle
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Exclude from Total")
                                .font(.subheadline)
                                .fontWeight(.medium)
                            Text("Don't count this category in overall budget")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Toggle("", isOn: $excludeFromTotal)
                            .labelsHidden()
                            .tint(appAccent)
                    }
                    .padding(.horizontal, 24)

                    // Icon picker (only for custom categories)
                    if !category.isSystem {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Icon")
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(.secondary)

                            IconPicker(
                                selectedIcon: $selectedIcon,
                                accentColor: Color(hex: selectedColor) ?? .gray
                            )
                        }
                        .padding(.horizontal, 24)

                        // Color picker
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Color")
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(.secondary)

                            ColorPalettePicker(selectedColor: $selectedColor)
                        }
                        .padding(.horizontal, 24)
                    }

                    Spacer().frame(height: 24)
                }
            }
            .navigationTitle("Edit Category")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        let cap = Double(capText) ?? category.monthlyCap
                        let update = CategoryUpdateRequest(
                            displayName: name != category.displayName ? name : nil,
                            icon: selectedIcon != category.icon ? selectedIcon : nil,
                            color: selectedColor != category.color ? selectedColor : nil,
                            monthlyCap: cap != category.monthlyCap ? cap : nil,
                            excludeFromTotal: excludeFromTotal != category.excludeFromTotal ? excludeFromTotal : nil
                        )
                        onSave(category.categoryId, update)
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
