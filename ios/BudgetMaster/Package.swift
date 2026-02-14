// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "BudgetMaster",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [
        .library(name: "BudgetMaster", targets: ["BudgetMaster"]),
    ],
    targets: [
        .target(
            name: "BudgetMaster",
            path: ".",
            exclude: ["Package.swift"],
            sources: ["Models", "Networking", "Services"]
        )
    ]
)
