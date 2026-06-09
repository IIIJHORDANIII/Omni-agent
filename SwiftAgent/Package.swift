// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Omniscient",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "Omniscient", targets: ["Omniscient"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "Omniscient",
            dependencies: [],
            path: "Sources/Omniscient",
            linkerSettings: [
                .linkedFramework("IOKit"),
                .linkedFramework("CoreAudio"),
                .linkedFramework("ApplicationServices"),
                .linkedFramework("AppKit")
            ]
        ),
        .testTarget(
            name: "OmniscientTests",
            dependencies: ["Omniscient"],
            path: "Tests/OmniscientTests"
        )
    ]
)
